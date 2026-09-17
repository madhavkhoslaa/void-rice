#!/usr/bin/env bash
# Install from an existing Void Linux local console, as the desktop user.
set -euo pipefail
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
if [[ ${1:-} == --help ]]; then
    cat <<'EOF'
Usage: ./install.sh
Environment: RICE_WIFI_INTERFACE=wlp0s20f3 RICE_COUNTRY=US RICE_JOBS=2
             RICE_WALLPAPER=/absolute/path/to/image.png
Requires an existing Void/runit installation, working Internet, and root access
via sudo, doas, or su. New wireless installs prompt for WPA2 credentials.
An Ethernet-only VM is supported; Wi-Fi will display 'absent'.
EOF
    exit 0
fi
[[ $# == 0 ]] || { echo 'Use ./install.sh --help' >&2; exit 2; }
(( EUID != 0 )) || { echo 'Run ./install.sh as your desktop user, not root.' >&2; exit 1; }
command -v xbps-install >/dev/null || { echo 'This installer requires Void Linux/XBPS.' >&2; exit 1; }
[[ -d /etc/sv && -d /var/service ]] || { echo 'A running Void/runit system is required.' >&2; exit 1; }
[[ $(uname -m) == x86_64 ]] || { echo 'This profile targets the specified x86_64 Intel laptop.' >&2; exit 1; }
USER_NAME=$(id -un)
JOBS=${RICE_JOBS:-2}
[[ $JOBS =~ ^[1-9][0-9]*$ ]] || { echo 'RICE_JOBS must be positive.' >&2; exit 2; }
COUNTRY=${RICE_COUNTRY:-}
[[ -z $COUNTRY || $COUNTRY =~ ^[A-Z]{2}$ ]] || { echo 'RICE_COUNTRY must be an uppercase ISO country code.' >&2; exit 2; }
export XDG_CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-$HOME/.cache}"
export XDG_DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
export PATH="$HOME/.local/bin:$PATH"
export RICE_JOBS=$JOBS
CONFIG="$XDG_CONFIG_HOME/rice"
SOURCE="$HOME/.local/src/rice"
STAMP=$(date +%Y%m%d-%H%M%S)-$$
BACKUP="$XDG_DATA_HOME/rice/backups/$STAMP"

if command -v sudo >/dev/null && sudo -v; then
    ROOT_METHOD=sudo
elif command -v doas >/dev/null; then
    ROOT_METHOD=doas
else
    ROOT_METHOD=su
fi
as_root() {
    if [[ $ROOT_METHOD == su ]]; then
        local command
        printf -v command '%q ' "$@"
        su -s /bin/bash -c "$command"
    else
        "$ROOT_METHOD" "$@"
    fi
}
backup() {
    local path=$1 relative
    if [[ -e $path || -L $path ]]; then
        relative=${path#/}
        mkdir -p "$BACKUP/$(dirname "$relative")"
        cp -a -- "$path" "$BACKUP/$relative"
    fi
}
copy_file() {
    backup "$2"
    install -D -m "${3:-0644}" "$1" "$2"
}
checkout() {
    local url=$1 revision=$2 directory=$3
    if [[ ! -d $directory/.git ]]; then
        [[ ! -e $directory ]] || { echo "Not a managed checkout: $directory" >&2; exit 1; }
        git init -q "$directory"
        git -C "$directory" remote add origin "$url"
        # Some small Git servers do not serve a raw SHA once it stops being an
        # advertised tip. Fall back to fetching branch history, then check out
        # the same pinned revision rather than silently using a newer source.
        git -C "$directory" fetch -q --depth 1 origin "$revision" ||
            git -C "$directory" fetch -q origin
        git -C "$directory" checkout -q --detach "$revision"
    fi
    [[ $(git -C "$directory" rev-parse HEAD) == "$revision" ]] || {
        echo "Source revision differs from the pinned build: $directory" >&2; exit 1;
    }
}

echo 'Updating XBPS, then the installed Void system...'
as_root xbps-install -Suy xbps
as_root xbps-install -uy
echo 'Installing build tools, X11, drivers, applications, and runit services...'
as_root xbps-install -y base-devel git curl ca-certificates pkg-config python3 python3-Pillow \
    libX11-devel libXft-devel libXinerama-devel libXext-devel fontconfig-devel
as_root xbps-install -y xorg-minimal mesa-dri linux-firmware-intel linux-firmware-network \
    intel-media-driver sof-firmware dejavu-fonts-ttf nerd-fonts-symbols-ttf xterm xprop xrdb xsetroot xset
as_root xbps-install -y runit dbus dhcpcd wpa_supplicant bluez iproute2 util-linux \
    procps-ng shadow bash
as_root xbps-install -y pipewire wireplumber libspa-bluetooth alsa-pipewire pulseaudio-utils
as_root xbps-install -y pywal ImageMagick feh rofi dunst libnotify brightnessctl

iface=${RICE_WIFI_INTERFACE:-}
if [[ -z $iface ]]; then
    interfaces=()
    for path in /sys/class/net/*/wireless; do
        [[ -d $path ]] && interfaces+=("$(basename "$(dirname "$path")")")
    done
    if (( ${#interfaces[@]} == 0 )); then
        iface=none
        echo 'No wireless adapter found; configuring Ethernet-only/VM operation.'
    elif (( ${#interfaces[@]} == 1 )); then
        iface=${interfaces[0]}
    else
        printf 'Wireless interfaces: %s\n' "${interfaces[*]:-none detected}"
        read -r -p 'Wi-Fi interface name: ' iface
    fi
fi
[[ $iface == none || ( $iface =~ ^[a-zA-Z0-9_.:-]+$ && -d /sys/class/net/$iface/wireless ) ]] || {
    echo 'Select an existing wireless interface with RICE_WIFI_INTERFACE.' >&2; exit 1;
}

echo 'Building the pinned ibhagwan fork as a local XBPS package...'
mkdir -p "$SOURCE"
checkout https://github.com/void-linux/void-packages.git \
    93ba84918bb407a66c1013f7f3625f5915477ddf "$SOURCE/void-packages"
package_template="$SOURCE/void-packages/srcpkgs/picom-ibhagwan/template"
copy_file "$ROOT/xbps-src/picom-ibhagwan/template" "$package_template"
(
    cd "$SOURCE/void-packages"
    ./xbps-src binary-bootstrap
    ./xbps-src -j "$JOBS" pkg picom-ibhagwan
)
as_root xbps-install -y -R "$SOURCE/void-packages/hostdir/binpkgs" picom-ibhagwan

echo 'Installing the templates and building dwm/slstatus...'
checkout https://github.com/bakkeby/dwm-flexipatch.git \
    4c963b33681b277a0ff4d3bf39a27b2feab68950 "$SOURCE/dwm"
checkout https://git.suckless.org/slstatus \
    675c83912ea1aca9834448aaa87a040bc9990c52 "$SOURCE/slstatus"
mkdir -p "$CONFIG" "$HOME/.local/bin" "$XDG_DATA_HOME/rice" "$HOME/Pictures/Wallpapers"
for folder in dwm slstatus picom rofi dunst x11 wireplumber; do
    backup "$CONFIG/$folder"
    mkdir -p "$CONFIG/$folder"
    cp -a "$ROOT/$folder/." "$CONFIG/$folder/"
done
for script in "$ROOT"/scripts/rice-*; do
    copy_file "$script" "$HOME/.local/bin/$(basename "$script")" 0755
done
printf '%s\n' "$iface" >"$CONFIG/wifi-interface"
copy_file "$ROOT/rofi/config.rasi" "$XDG_CONFIG_HOME/rofi/config.rasi"
for path in "$XDG_CONFIG_HOME/rofi/rice.rasi" "$XDG_CONFIG_HOME/dunst/dunstrc" \
            "$HOME/.local/bin/rice-dwm" "$HOME/.local/bin/rice-slstatus"; do backup "$path"; done
copy_file "$ROOT/slstatus/config.h" "$SOURCE/slstatus/config.h"
make -C "$SOURCE/slstatus" clean
make -C "$SOURCE/slstatus" -j "$JOBS" COM='components/datetime components/run_command'
install -m 0755 "$SOURCE/slstatus/slstatus" "$HOME/.local/bin/.rice-slstatus.new"
mv -f "$HOME/.local/bin/.rice-slstatus.new" "$HOME/.local/bin/rice-slstatus"

wallpaper=${RICE_WALLPAPER:-$HOME/Pictures/Wallpapers/rice-default.png}
if [[ -z ${RICE_WALLPAPER:-} && ! -f $wallpaper ]]; then rice-default-wallpaper "$wallpaper"; fi
rice-theme --no-reload "$wallpaper"

# The standard Void example filenames override same-named system drop-ins.
mkdir -p "$XDG_CONFIG_HOME/pipewire/pipewire.conf.d"
for spec in 'wireplumber/10-wireplumber.conf' 'pipewire/20-pipewire-pulse.conf'; do
    destination="$XDG_CONFIG_HOME/pipewire/pipewire.conf.d/${spec##*/}"
    backup "$destination"
    ln -sfn "/usr/share/examples/$spec" "$destination"
done
copy_file "$ROOT/wireplumber/90-rice-no-logind.conf" \
    "$XDG_CONFIG_HOME/wireplumber/wireplumber.conf.d/90-rice-no-logind.conf"
copy_file "$ROOT/x11/xinitrc" "$HOME/.xinitrc" 0755
chmod 0755 "$CONFIG/x11/session"

echo 'Configuring device permissions and enabling runit services...'
as_root bash "$ROOT/scripts/rice-system-setup" "$ROOT" "$USER_NAME" "$iface" "$COUNTRY" "$STAMP"
if [[ $iface != none ]] && ! as_root grep -Eq '^[[:space:]]*network[[:space:]]*=' /etc/wpa_supplicant/wpa_supplicant.conf; then
    as_root "$HOME/.local/bin/rice-wifi-add"
fi
cat <<EOF

Installed. Home backups: $BACKUP
System backups: /var/backups/rice/$STAMP
Log out completely, then log in on a local TTY (new device/control groups).
Run: startx
Super+Return: terminal | Super+p: launcher | Super+F9: compositor off/on
Super+F10: effects toggle | Super+Shift+w: wallpaper picker
Bluetooth pairing: bluetoothctl (see scripts/README-network.md).
EOF
