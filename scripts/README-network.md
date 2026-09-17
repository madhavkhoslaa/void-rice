# Networking, Bluetooth, brightness and audio

## Ownership and runit services

`wpa_supplicant` owns wireless association; **dhcpcd owns IP configuration on
both wired and wireless interfaces**. The installer writes the complete service
scripts supplied in `sv/`, then enables these links:

```sh
sudo ln -s /etc/sv/dbus /var/service/dbus
sudo ln -s /etc/sv/wpa_supplicant /var/service/wpa_supplicant
sudo ln -s /etc/sv/dhcpcd /var/service/dhcpcd
sudo ln -s /etc/sv/bluetoothd /var/service/bluetoothd
```

These are the equivalent first-install commands; `install.sh` handles existing
links, backup files, foreground processes, logging, startup ordering and new
supervisors. It accepts `sudo`, `doas`, or `su` for its privileged phase.

The effective commands in the run scripts are:

```sh
/usr/bin/dhcpcd -B -M -C wpa_supplicant
/usr/bin/wpa_supplicant -D nl80211 -i "$WPA_INTERFACE" -c /etc/wpa_supplicant/wpa_supplicant.conf
/usr/libexec/bluetooth/bluetoothd -n
```

`-B` keeps dhcpcd in the foreground; `-M` selects its manager mode. Its
`wpa_supplicant` hook is disabled with `-C`: this prevents a second supplicant
competing with runit. The supplicant itself has **no `-B` flag**.

The detected Wi-Fi name is saved in both:

- `/etc/sv/wpa_supplicant/conf` — `WPA_INTERFACE` and `CONF_FILE`.
- `~/.config/rice/wifi-interface` — the bar's interface name.

On an Ethernet-only VM, `WPA_INTERFACE=none`. The service runs
`wpa_supplicant -g /run/wpa_supplicant/global` without attaching a nonexistent
adapter, and the Wi-Fi icon is followed by `absent`. To add a passed-through adapter,
rerun the installer with `RICE_WIFI_INTERFACE=your-interface`.

## Wi-Fi credentials and permissions

Existing `/etc/wpa_supplicant/wpa_supplicant.conf` network blocks are preserved,
including WPA3 and enterprise configurations. The installer sets:

```ini
ctrl_interface=DIR=/run/wpa_supplicant GROUP=ricewifi
update_config=0
```

The file remains root-owned, mode `0600`. The control directory is root:ricewifi,
mode `0770`. Your user joins `ricewifi`, so **log out completely and log back in**
before testing the bar. This group grants supplicant control, including network
changes, not just read-only status. There is no privileged command in a bar poll.

To add a WPA2-Personal network interactively:

```sh
rice-wifi-add
```

This uses `wpa_passphrase` with the passphrase on stdin, removes its plaintext
`#psk` comment, backs up the existing config, appends the PSK block, and issues
`wpa_cli reconfigure`. An existing configuration avoids the install-time prompt.
For WPA3-only or enterprise networks, use the network block appropriate to that
network in the same file; the installer preserves it.

Set your regulatory domain during installation if needed:

```sh
RICE_COUNTRY=GB ./install.sh
```

Use your actual two-letter country code. An unset variable preserves an existing
`country=` line and otherwise uses the kernel/regulatory defaults.

## Exact Wi-Fi bar queries

Inside the installed X session:

```sh
iface=$(cat "${XDG_CONFIG_HOME:-$HOME/.config}/rice/wifi-interface")
wpa_cli -p /run/wpa_supplicant -i "$iface" status
wpa_cli -p /run/wpa_supplicant -i "$iface" signal_poll
ip -o addr show dev "$iface" scope global
```

`rice-wifi-status` parses `wpa_state=COMPLETED` and `ssid=` from `status`, and
**`RSSI=` from `signal_poll`**. RSSI is shown in dBm, not a made-up percentage.
An unsupported signal poll shows `?dBm`. The script does not trigger scans.
It caches the result for 10 seconds and bounds each control request at 2 seconds.
SSID escape sequences remain literal, with a 20-byte display limit; control
characters and `|`/`;` separators cannot corrupt the other fields or the clock.

`ip` checks the live address state after association. No global address means
`IP?`; it can also indicate a static/SLAAC configuration issue.
The bar distinguishes link/IP availability, not external Internet reachability.

Useful DHCP commands (administration, **not periodic bar polling**):

```sh
sudo sv status /var/service/dhcpcd /var/service/wpa_supplicant
sudo dhcpcd -n "$iface"       # ask the running daemon to rebind/reconfigure
sudo dhcpcd -U "$iface"       # dump the saved DHCP lease, if one exists
sudo tail -n 40 /var/log/rice/dhcpcd/current
sudo tail -n 40 /var/log/rice/wpa_supplicant/current
```

A lease dump can be stale, so the bar does not equate its existence with being
connected. Wireless state/control sockets are in `/run/wpa_supplicant/`.

Manual association diagnostics:

```sh
wpa_cli -p /run/wpa_supplicant -i "$iface" ping
wpa_cli -p /run/wpa_supplicant -i "$iface" list_networks
wpa_cli -p /run/wpa_supplicant -i "$iface" scan
wpa_cli -p /run/wpa_supplicant -i "$iface" scan_results
sudo rfkill list
sudo rfkill unblock wifi
```

`rfkill` is supplied by Void's `util-linux` package. Hardware airplane switches
still need to be switched on physically.

## Bluetooth: BlueZ, D-Bus, runit

Void's **package is `bluez`, service is `bluetoothd`**, and the daemon is
`/usr/libexec/bluetooth/bluetoothd`. The run script waits for Void's packaged
`dbus` service. Your user joins the `bluetooth` group.

After the new login, pair through one interactive `bluetoothctl` session, so the
agent stays alive during pairing:

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

Substitute the device address printed by `scan on`. For a blocked adapter, run
`sudo rfkill unblock bluetooth`. Power is controllable with
`bluetoothctl power off` / `bluetoothctl power on`.

The bar polls these exact commands every 30 seconds, with a 3-second timeout:

```sh
bluetoothctl show
bluetoothctl devices Connected
```

It reads `Powered: yes/no` and counts `Device ...` lines from the second command.
Following the Bluetooth icon, the results are `n/a`, `off`, `on`, or a connected
device count. Polling
never enables discovery. This targets the default controller; use
`bluetoothctl select CONTROLLER-MAC` when managing multiple controllers manually.

```sh
sudo sv status /var/service/dbus /var/service/bluetoothd
sudo tail -n 40 /var/log/rice/bluetoothd/current
```

## Brightness and PipeWire audio

- Brightness reads `/sys/class/backlight/intel_backlight/{brightness,max_brightness}`,
  falling back to the first available backlight. It reports requested brightness
  as a percentage of `max_brightness`. An ordinary VM has no physical backlight,
  so `n/a` following the sun icon is expected there.
- Brightness keys use `brightnessctl -d DEVICE -n 1 set +5%` and
  `brightnessctl -d DEVICE -n 1 set 5%-`. The installer reloads its udev rules and
  triggers the backlight subsystem; your user joins `video`.
- Audio reads `wpctl get-volume @DEFAULT_AUDIO_SINK@`, including `[MUTED]`.
  The bar shows, for example, an audio icon followed by `45% muted`. An absent
  sink is reported as `n/a`.
- Audio keys run `wpctl set-volume -l 1.0 @DEFAULT_AUDIO_SINK@ 5%+`,
  `wpctl set-volume @DEFAULT_AUDIO_SINK@ 5%-`, and
  `wpctl set-mute @DEFAULT_AUDIO_SINK@ toggle`.
- `rice-controls` signals the session's **slstatus with SIGUSR1**, using its own
  validated PID file, to refresh after a key press. External changes appear at
  the next 10-second poll. There is no extra high-frequency polling process.

PipeWire uses Void's standard `10-wireplumber.conf` and
`20-pipewire-pulse.conf` user drop-ins. Thus the `pipewire &` autostart line in
`x11/session` also starts WirePlumber and the PulseAudio-compatible server.
`alsa-pipewire` handles ALSA clients; `libspa-bluetooth` handles Bluetooth audio.
WirePlumber's seat-monitoring override supports this setup without a login
manager; device access is via the `audio` and `video` groups.

```sh
wpctl status
pactl info
# Select an output, using its numeric ID from wpctl status:
wpctl set-default 42
```

Audio is per-user and uses the session D-Bus/runtime directory, not a system
runit audio daemon.
