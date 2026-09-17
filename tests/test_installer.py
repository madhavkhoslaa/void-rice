"""Exercise real shell helpers in temporary directories with a fake runit CLI."""
import os
import hashlib
from pathlib import Path
import shlex
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class Sandbox(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.bins = self.base / "bin"
        self.bins.mkdir()
        self.env = {**os.environ, "PATH": str(self.bins) + ":" + os.environ["PATH"],
                    "HOME": str(self.base), "GIT_CONFIG_GLOBAL": "/dev/null"}

    def bash(self, code, check=True):
        return subprocess.run(["bash", "-c", "set -euo pipefail\n" + code], env=self.env,
                              text=True, capture_output=True, check=check)


class ServiceTests(Sandbox):
    def setUp(self):
        super().setUp()
        self.units = self.base / "etc/sv"
        self.services = self.base / "service"
        self.services.mkdir()
        self.log = self.base / "sv.log"
        self.env["TEST_LOG"] = str(self.log)
        mock = self.bins / "sv"
        mock.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >>"$TEST_LOG"\nexit 0\n')
        mock.chmod(0o755)
        for name in ("dbus", "dhcpcd", "wpa_supplicant", "wpa_supplicant-wlan0", "NetworkManager", "bluetoothd"):
            unit = self.units / name
            unit.mkdir(parents=True)
            (unit / "run").write_text("#!/bin/sh\nexit 0\n")
            (unit / "run").chmod(0o755)
        for name in ("dbus", "dhcpcd", "wpa_supplicant", "wpa_supplicant-wlan0", "bluetoothd"):
            (self.services / name).symlink_to(self.units / name)
        self.setup = (f"source {shlex.quote(str(ROOT / 'scripts/rice-system-setup'))}\n"
                      f"SV_DIR={shlex.quote(str(self.units))}\n"
                      f"SERVICE_DIR={shlex.quote(str(self.services))}\n"
                      f"backup={shlex.quote(str(self.base / 'backup'))}\n")

    def test_migration_order_and_idempotent_second_run(self):
        self.bash(self.setup + "activate_network_services")
        first = self.log.read_text().splitlines()
        enable_nm = next(i for i, line in enumerate(first) if line.endswith("up " + str(self.services / "NetworkManager")))
        stops = [i for i, line in enumerate(first) if " down " in line]
        self.assertEqual(len(stops), 3)
        self.assertTrue(all(i < enable_nm for i in stops))
        self.assertFalse((self.services / "dhcpcd").exists())
        self.assertFalse((self.services / "wpa_supplicant").exists())
        self.assertTrue((self.units / "dhcpcd/down").exists())
        self.assertEqual((self.services / "NetworkManager").resolve(), self.units / "NetworkManager")
        self.log.write_text("")
        self.bash(self.setup + "activate_network_services")
        second = self.log.read_text()
        self.assertNotIn(" down ", second)
        self.assertNotIn("restart", second)
        self.assertNotIn("exit", second)
        self.assertEqual(len(list(self.services.iterdir())), 3)

    def test_missing_nm_service_fails_before_stopping_existing_network(self):
        (self.units / "NetworkManager/run").unlink()
        result = self.bash(self.setup + "activate_network_services", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue((self.services / "dhcpcd").is_symlink())
        self.assertFalse(self.log.exists())

    def test_unexpected_existing_service_is_not_overwritten(self):
        custom = self.base / "custom-NetworkManager"
        custom.mkdir()
        (self.services / "NetworkManager").symlink_to(custom)
        result = self.bash(self.setup + "activate_network_services", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((self.services / "NetworkManager").resolve(), custom)
        self.assertTrue((self.services / "dhcpcd").is_symlink())

    def test_only_exact_legacy_wrapper_is_restored_once(self):
        repository = self.base / "bundle"
        (repository / "sv").mkdir(parents=True)
        run = self.units / "bluetoothd/run"
        digest = hashlib.sha256(run.read_bytes()).hexdigest()
        (repository / "sv/legacy-services.sha256").write_text(f"bluez {digest} {run}\n")
        self.env["TEST_RESTORE"] = str(run)
        query = self.bins / "xbps-query"
        query.write_text("#!/bin/sh\necho bluez-5.86_2\n")
        query.chmod(0o755)
        install = self.bins / "xbps-install"
        install.write_text('#!/bin/sh\nprintf "restore %s\\n" "$*" >>"$TEST_LOG"\n'
                           'printf "#!/bin/sh\\n# packaged version\\n" >"$TEST_RESTORE"\n')
        install.chmod(0o755)
        code = self.setup + f"root={shlex.quote(str(repository))}\nrestore_packaged_services"
        self.bash(code)
        self.assertIn("packaged version", run.read_text())
        self.bash(code)
        self.assertEqual(self.log.read_text().count("restore"), 1)
        # A user customization no longer matching the beta hash stays intact.
        run.write_text("#!/bin/sh\n# user customization\n")
        self.bash(code)
        self.assertIn("user customization", run.read_text())
        self.assertEqual(self.log.read_text().count("restore"), 1)

    def test_failed_new_manager_restores_previous_services(self):
        mock = self.bins / "sv"
        mock.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >>"$TEST_LOG"\n'
                        'case "$*" in *" up "*NetworkManager) exit 1 ;; esac\nexit 0\n')
        sleep = self.bins / "sleep"
        sleep.write_text("#!/bin/sh\nexit 0\n")
        sleep.chmod(0o755)
        result = self.bash(self.setup + "HANDOVER_PENDING=1\ntrap rollback_network ERR\n"
                           "activate_network_services", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.services / "NetworkManager").exists())
        for name in ("dhcpcd", "wpa_supplicant", "wpa_supplicant-wlan0"):
            self.assertEqual((self.services / name).resolve(), self.units / name)
            self.assertFalse((self.units / name / "down").exists())
        self.assertIn("restoring the previous", result.stderr)


class InstallHelperTests(Sandbox):
    def setUp(self):
        super().setUp()
        self.setup = f"source {shlex.quote(str(ROOT / 'scripts/rice-install-lib.sh'))}\n"

    def test_interrupted_checkout_can_resume_and_rerun(self):
        remote = self.base / "remote"
        dest = self.base / "checkout"
        subprocess.run(["git", "init", "-q", "-b", "master", str(remote)], env=self.env, check=True)
        (remote / "source.txt").write_text("source\n")
        subprocess.run(["git", "-C", str(remote), "add", "source.txt"], env=self.env, check=True)
        subprocess.run(["git", "-C", str(remote), "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                        "-c", "commit.gpgsign=false", "commit", "-qm", "fixture"], env=self.env, check=True)
        revision = subprocess.check_output(["git", "-C", str(remote), "rev-parse", "HEAD"], text=True).strip()
        subprocess.run(["git", "init", "-q", str(dest)], env=self.env, check=True)
        command = f"checkout {shlex.quote(remote.as_uri())} {revision} {shlex.quote(str(dest))}"
        self.bash(self.setup + command)
        self.assertEqual((dest / "source.txt").read_text(), "source\n")
        (dest / "source.txt").write_text("local edit\n")
        self.bash(self.setup + command)
        self.assertEqual((dest / "source.txt").read_text(), "local edit\n")

    def test_repeat_copy_keeps_single_original_backup(self):
        source = self.base / "new"
        dest = self.base / "config"
        backup = self.base / "backup"
        source.write_text("new config\n")
        dest.write_text("old config\n")
        code = self.setup + f"BACKUP={shlex.quote(str(backup))}\n"
        code += f"copy_file {shlex.quote(str(source))} {shlex.quote(str(dest))}\n"
        self.bash(code)
        before = dest.stat().st_mtime_ns
        self.bash(code)
        self.assertEqual(dest.stat().st_mtime_ns, before)
        files = [p for p in backup.rglob("*") if p.is_file()]
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0].read_text(), "old config\n")


if __name__ == "__main__":
    unittest.main()
