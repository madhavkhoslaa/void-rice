# NetworkManager, Bluetooth, brightness and audio

## Networking: one manager for Ethernet and Wi-Fi

The rice uses **NetworkManager** with Void's packaged runit service. Its package
includes `nmcli`, `nmtui`, `nmtui-connect` and `nm-online`; it also pulls in
`wpa_supplicant` as its Wi-Fi backend. The standalone supplicant/dhcpcd services
are disabled so they cannot compete with NetworkManager.

The installer enables these packaged services:

```text
/var/service/dbus           -> /etc/sv/dbus
/var/service/NetworkManager -> /etc/sv/NetworkManager
/var/service/bluetoothd     -> /etc/sv/bluetoothd
```

It adds your user to `network` and `bluetooth`. Void's packages supply the
corresponding access rules. **Log out completely and log back in** to get the
new group membership. The installer reloads D-Bus configuration without
restarting the system bus. No custom network service run scripts are installed.

### Everyday connection management

- **Super+Shift+n** opens `nmtui` in a terminal.
- `nmtui` lets you activate, edit and save Ethernet/Wi-Fi connections.
- `rice-wifi-add` remains available as a compatibility command for
  `nmtui-connect`.

The command-line equivalents are:

```sh
nmcli device status
nmcli connection show
nmcli radio wifi on
nmcli device wifi list
nmcli --ask device wifi connect 'Your SSID'
# Activate an already saved profile, by its name or UUID:
nmcli connection up uuid YOUR-CONNECTION-UUID
```

`--ask` requests the password interactively instead of putting it in a process
argument. Saved profiles normally live in
`/etc/NetworkManager/system-connections/`. Ethernet uses NetworkManager's
automatic configuration on a fresh install. Existing NetworkManager profiles,
including static IP/DNS choices, are preserved.

### Upgrading from the first beta and rerunning the installer

Run the same `./install.sh` after updating your checkout. It:

1. Finishes installing packages/building the rice before handing over networking.
2. Recognizes the **exact** old beta service wrappers by hash and reinstalls their
   owning packages to restore the packaged run scripts.
3. Imports compatible saved WPA2-Personal/open networks into root-only (`0600`)
   NetworkManager keyfiles. Existing NM profiles for the same SSID take priority.
4. Stops and unlinks standalone `dhcpcd`/`wpa_supplicant` services, including
   per-interface variants, before enabling NetworkManager.
5. Reloads connection files and checks that the NetworkManager D-Bus API is ready.

If a new NetworkManager handover fails, the installer attempts to stop that new
service and restore the previous network-service links before exiting. It does
not force-stop a NetworkManager service that was already enabled before the run.

The original `/etc/wpa_supplicant/*.conf` files are retained. Custom/WPA3/EAP
blocks are reported and left intact rather than approximated; configure those
through NetworkManager. The former `RICE_WIFI_INTERFACE`/`RICE_COUNTRY` installer
settings are no longer used—NetworkManager discovers the interfaces itself.

A migration marker in `/var/lib/void-rice/networkmanager-migration.json` prevents
later runs from importing the same legacy settings again or resurrecting profiles
you intentionally deleted. Existing NM passwords and BlueZ pairings are retained.
Rerunning uses **`sv up`, not `sv restart`**, for NetworkManager and Bluetooth.

On a new setup with no active connection, an interactive installation opens
`nmtui-connect`. On an Ethernet-only VM, no wireless interface or credentials are
required. The initial handover from the legacy services can reconnect the link.

### Exact bar queries

The network field uses `rice-wifi-status` (the filename is kept for compatibility):

```sh
nmcli --wait 2 -t --escape yes -f DEVICE,TYPE,STATE device status
nmcli --wait 2 -t --escape yes -f IN-USE,SSID,SIGNAL device wifi list ifname wlan0 --rescan no
nmcli --wait 2 -g WIFI general
```

The interface name is discovered from the first command; `wlan0` above is just
an example. **`--rescan no`** reads the cached AP information without requesting
a scan. Signal is NetworkManager's **0–100% strength**, not dBm.

The field shows an active Wi-Fi SSID/strength, or falls back to an Ethernet icon
and connected interface. If both are connected, Wi-Fi is displayed. Other states
include off, connecting, disconnected, unmanaged, absent and NM unavailable.
It reports link state, not a guarantee of Internet/captive-portal reachability.

Results are cached for 10 seconds, including when audio/brightness keys refresh
slstatus. Each `nmcli` invocation has a 3-second outer timeout. Terse-output
escaping is parsed explicitly; SSID labels are capped at 20 characters and bar
separators/control characters are sanitized.

Diagnostics:

```sh
sudo sv status /var/service/dbus /var/service/NetworkManager
nmcli general status
nmcli device status
nmcli general permissions
sudo NetworkManager --print-config
rfkill list
sudo rfkill unblock wifi
```

## Bluetooth: BlueZ service + Blueman interface

**BlueZ (`bluez`) supplies the `bluetoothd` service and `bluetoothctl`.** Void's
packaged service starts `/usr/libexec/bluetooth/bluetoothd` after D-Bus is ready.
**Blueman (`blueman`) supplies graphical pairing and device management.**

- **Super+Shift+b** opens `blueman-manager`; it also appears in rofi.
- `blueman-applet` runs once in the X session to provide the pairing agent.
  It is outside dwm's restart lifecycle. The six-field bar remains unchanged;
  applet tray icons appear only if you enable the existing systray option.
- Existing pairings in `/var/lib/bluetooth/` and radio power preferences are kept.

CLI pairing also works. Use one interactive session so the agent remains active:

```text
bluetoothctl
power on
agent on
default-agent
scan on
pair AA:BB:CC:DD:EE:FF
trust AA:BB:CC:DD:EE:FF
connect AA:BB:CC:DD:EE:FF
scan off
quit
```

Use your device's address. For a soft-blocked radio, run
`sudo rfkill unblock bluetooth`; a hardware block requires the laptop switch or
firmware setting. A VM needs an actual/passed-through adapter for pairing.

The Bluetooth bar field polls these commands every 30 seconds (3-second timeout):

```sh
bluetoothctl show
bluetoothctl devices Connected
```

Following the Bluetooth icon it shows `n/a`, `off`, `on`, or the number of
connected devices. Status polling never enables discovery.

```sh
sudo sv status /var/service/bluetoothd
bluetoothctl show
```

## Brightness and PipeWire audio

- Brightness reads `/sys/class/backlight/intel_backlight/{brightness,max_brightness}`,
  falling back to the first backlight. A VM without a backlight shows `n/a`.
- Brightness keys use `brightnessctl -d DEVICE -n 1 set +5%` / `5%-`.
  The installer reloads the udev rules and adds your user to `video`.
- Audio uses `wpctl get-volume @DEFAULT_AUDIO_SINK@`, including `[MUTED]`.
- Audio keys use `wpctl set-volume -l 1.0 @DEFAULT_AUDIO_SINK@ 5%+`,
  `wpctl set-volume @DEFAULT_AUDIO_SINK@ 5%-`, and
  `wpctl set-mute @DEFAULT_AUDIO_SINK@ toggle`.
- Controls signal slstatus with SIGUSR1 for immediate refresh; external changes
  appear on its 10-second tick.

PipeWire's standard Void `10-wireplumber.conf` and `20-pipewire-pulse.conf`
drop-ins start WirePlumber and the PulseAudio-compatible server from the session's
single `pipewire` process. `alsa-pipewire` handles ALSA clients and
`libspa-bluetooth` handles Bluetooth audio. Device access uses `audio`/`video`
groups; the WirePlumber override supports operation without a login manager.

```sh
wpctl status
pactl info
# Select an output ID shown by wpctl status:
wpctl set-default 42
```

Session logs (including `blueman.log`) are in `~/.cache/rice/log/`. Old beta
network-service logs remain under `/var/log/rice/` on upgraded installations;
fresh installs use the packaged services' normal logging behavior.
