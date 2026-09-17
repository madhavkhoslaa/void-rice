# Use Void's packaged runit services

`install.sh` installs `NetworkManager`, `bluez` and `blueman`, and enables:

```text
/var/service/dbus           -> /etc/sv/dbus
/var/service/NetworkManager -> /etc/sv/NetworkManager
/var/service/bluetoothd     -> /etc/sv/bluetoothd
```

The run scripts come from XBPS packages. This bundle does not replace them.
Standalone `dhcpcd`/`wpa_supplicant` services (including per-interface variants)
are stopped and unlinked before NetworkManager is enabled. The supplicant
package stays installed as NetworkManager's normal Wi-Fi backend.

For upgrades from the original beta, `legacy-services.sha256` identifies only
the exact run scripts that beta overwrote. Their owning packages are reinstalled
to restore the packaged versions before the network handover. Existing legacy
logs and the original `/etc/wpa_supplicant/*.conf` files remain available.

Rerunning uses `sv up`, not `sv restart`, for NetworkManager and Bluetooth.
Saved NetworkManager profiles and BlueZ pairings are retained.
