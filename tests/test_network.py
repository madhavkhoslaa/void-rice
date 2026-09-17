"""Offline tests: no daemons, package installation or host network changes."""
import configparser
import importlib.machinery
import importlib.util
from pathlib import Path
import stat
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load(name, filename):
    loader = importlib.machinery.SourceFileLoader(name, str(ROOT / "scripts" / filename))
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


migration = load("migration", "rice-network-migrate")
status = load("network_status", "rice-wifi-status")


class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.wpa = self.base / "wpa"
        self.nm = self.base / "connections"
        self.state = self.base / "state"
        self.wpa.mkdir()
        self.nm.mkdir()

    def write_wpa(self, text, name="wpa_supplicant.conf"):
        (self.wpa / name).write_text(text)

    def migrate(self):
        return migration.migrate(self.wpa, self.nm, self.state)

    def test_import_psk_hidden_network_and_repeat(self):
        original = ('ctrl_interface=/run/wpa_supplicant\nnetwork={\n'
                    ' ssid="Cafe:#; North" # comment\n psk=' + 'a' * 64 + '\n'
                    ' scan_ssid=1\n priority=7\n proto=RSN\n ieee80211w=1\n}\n')
        self.write_wpa(original)
        self.assertEqual(self.migrate()["imported"], 1)
        path, = self.nm.glob("*.nmconnection")
        config = configparser.ConfigParser(interpolation=None)
        config.read(path)
        self.assertEqual(config["wifi-security"]["psk"], "a" * 64)
        self.assertEqual(config["wifi-security"]["pmf"], "2")
        self.assertEqual(config["wifi"]["hidden"], "true")
        self.assertEqual(config["connection"]["autoconnect-priority"], "7")
        self.assertEqual(migration.known_ssids(self.nm), {b"Cafe:#; North"})
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        self.assertEqual((self.wpa / "wpa_supplicant.conf").read_text(), original)
        # User edits in NM survive a rerun; deleted profiles are not resurrected.
        path.write_text(path.read_text().replace("priority=7", "priority=9"))
        self.assertTrue(self.migrate()["already_migrated"])
        self.assertIn("priority=9", path.read_text())
        path.unlink()
        self.migrate()
        self.assertEqual(list(self.nm.iterdir()), [])

    def test_existing_networkmanager_profile_wins(self):
        existing = self.nm / "user-profile.nmconnection"
        contents = "[connection]\nid=Mine\n[wifi]\nssid=Cafe\\sNorth\n[wifi-security]\npsk=my-own-secret\n"
        existing.write_text(contents)
        self.write_wpa('network={\nssid="Cafe North"\npsk="legacy-secret"\n}\n')
        counts = self.migrate()
        self.assertEqual((counts["imported"], counts["kept"]), (0, 1))
        self.assertEqual(existing.read_text(), contents)

    def test_duplicate_open_profiles_and_hex_ssid(self):
        self.write_wpa('network={\nssid="Guest"\nkey_mgmt=NONE\n}\n')
        self.write_wpa('network={\nssid=4775657374\nkey_mgmt=NONE\n}\n', "wpa_supplicant-wlan0.conf")
        counts = self.migrate()
        self.assertEqual((counts["imported"], counts["kept"]), (1, 1))
        text = next(self.nm.iterdir()).read_text()
        self.assertNotIn("wifi-security", text)
        self.assertIn("method=auto", text)

    def test_quoted_password_escaping(self):
        ssid, _, text = migration.profile({"ssid": '"Office"', "psk": '" a\\b #; password "'})
        self.assertEqual(ssid, b"Office")
        self.assertIn(r"psk=\sa\\b\s#;\spassword\s", text)

    def test_custom_security_is_retained_not_guessed(self):
        self.write_wpa('network={\nssid="University"\nkey_mgmt=WPA-EAP\nidentity="me"\n}\n'
                       'network={\nssid="WPA3"\nkey_mgmt=SAE\nsae_password="secret"\n}\n'
                       'network={\nssid="Broken"\npsk="short"\n}\n')
        counts = self.migrate()
        self.assertEqual((counts["imported"], counts["skipped"]), (0, 3))
        self.assertEqual(list(self.nm.iterdir()), [])
        self.assertNotIn("secret", (self.state / "networkmanager-migration.json").read_text())

    def test_fresh_install_without_wifi_configuration(self):
        counts = self.migrate()
        self.assertEqual(counts["imported"], 0)
        self.assertTrue(self.migrate()["already_migrated"])

    @unittest.skipUnless(shutil.which("nmcli"), "nmcli offline validator is not installed")
    def test_real_networkmanager_offline_parser(self):
        # --offline only reads stdin/writes stdout; it never contacts the daemon.
        for block in [{"ssid": '"Cafe:#; North"', "psk": "a" * 64},
                      {"ssid": '"Guest"', "key_mgmt": "NONE"},
                      {"ssid": '"Office"', "psk": '" a\\b #; password "'},
                      *({"ssid": value.hex(), "key_mgmt": "NONE"} for value in
                        [b"A;B", b"A\\;B", b"A\\B", b"1;2;3;", b" Leading ", b"A\\\\;B"])]:
            ssid, _, text = migration.profile(block)
            result = subprocess.run(["nmcli", "--offline", "connection", "modify",
                                     "connection.autoconnect", "yes"], input=text,
                                    text=True, capture_output=True, check=True)
            (self.nm / "normalized.nmconnection").write_text(result.stdout)
            self.assertIn(ssid, migration.known_ssids(self.nm))


class NetworkStatusTests(unittest.TestCase):
    def test_wifi_escaped_ssid_and_no_rescan(self):
        calls = []
        def query(*args):
            calls.append(args)
            return "wlan0:wifi:connected" if args[-1] == "status" else r"*:Cafe\:lab\\x;y|z:87"
        value = status.network_status(query)
        self.assertEqual(value, "\uf1eb Cafe:lab\\x/y/z 87%")
        self.assertEqual(calls[1][-2:], ("--rescan", "no"))
        self.assertNotIn(";", value)

    def test_ethernet_only_vm(self):
        self.assertEqual(status.network_status(lambda *args: "enp1s0:ethernet:connected\nlo:loopback:connected"),
                         "\uf0e8 enp1s0")

    def test_connected_ethernet_when_wifi_disconnected(self):
        self.assertEqual(status.network_status(lambda *args: "wlan0:wifi:disconnected\neth0:ethernet:connected"),
                         "\uf0e8 eth0")

    def test_radio_off_and_connection_states(self):
        for state, radio, expected in [("unavailable", "disabled", "off"),
                                       ("connecting (prepare)", "enabled", "connecting"),
                                       ("disconnected", "enabled", "disconnected"),
                                       ("unmanaged", "enabled", "unmanaged")]:
            with self.subTest(state=state):
                def query(*args):
                    return f"wlan0:wifi:{state}" if args[-1] == "status" else radio
                self.assertEqual(status.network_status(query), "\uf1eb " + expected)

    def test_missing_daemon_and_missing_hardware(self):
        def fail(*args):
            raise subprocess.TimeoutExpired("nmcli", 3)
        self.assertEqual(status.network_status(fail), "\uf0e8 NM unavailable")
        self.assertEqual(status.network_status(lambda *args: "lo:loopback:connected"), "\uf0e8 absent")

    def test_invalid_signal_is_not_reported_as_real_strength(self):
        def query(*args):
            return "wlan0:wifi:connected" if args[-1] == "status" else "*:Test:101"
        self.assertEqual(status.network_status(query), "\uf1eb Test ?%")


if __name__ == "__main__":
    unittest.main()
