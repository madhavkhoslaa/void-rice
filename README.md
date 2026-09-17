# void-rice

**Status: BETA.** This is a work-in-progress Void Linux rice. The configuration
builds have been checked on the authoring machine; end-to-end installation in a
Void VM and testing on the target Intel laptop are still pending.

A complete installable configuration for **Void Linux + runit + X11**, inspired
by Ryoku's coordinated palette, spacing and restrained presentation. dwm changes
layout instantly. There are no animations or fades.

The target is the specified Intel H-series laptop. The same installer supports
an Ethernet-only Void VM for testing; missing radios/backlight show as unavailable.

## Install

On an existing Void installation with Internet access, run as the desktop user:

```sh
git clone https://github.com/madhavkhoslaa/void-rice.git
cd void-rice
./install.sh
```

The installer uses `sudo`, `doas`, or `su` for root operations. It updates XBPS,
updates the Void system, installs packages, builds the pinned software, copies
configs, creates the runit links, and provisions permissions. It generates an
original default wallpaper, so no image download or manual config assembly is
needed. Existing Wi-Fi network blocks are retained; otherwise it prompts for
WPA2-Personal credentials. Its final service activation can briefly reconnect
the network; downloads and builds finish first.

**Log out fully and log in again on a local TTY**, then run:

```sh
startx
```

That new login picks up the device, Bluetooth and supplicant-control groups.
The installer replaces `~/.xinitrc` with this session's entry point. It backs up
existing managed files under `~/.local/share/rice/backups/TIMESTAMP/` and
`/var/backups/rice/TIMESTAMP/`; custom XDG directories are respected.

Optional installation parameters:

```sh
RICE_WIFI_INTERFACE=wlp0s20f3 RICE_COUNTRY=US RICE_JOBS=2 \
  RICE_WALLPAPER="$HOME/Pictures/my wallpaper.jpg" ./install.sh
```

Use your actual interface/country. Interface selection is automatic with one
adapter, interactive with several, and `none` with no wireless adapter.
The two-job default applies to the rice builds to limit contention/heat.
The installer is guarded against running on Arch or as the root desktop user.

## Included files

```text
rice-config/
├── install.sh
├── README.md
├── LICENSE
├── dwm/
│   ├── config.h.template
│   ├── patches.h
│   ├── config.mk
│   └── bar-current.h
├── slstatus/config.h
├── picom/
│   ├── picom.conf
│   └── effects.conf
├── rofi/
│   ├── config.rasi
│   └── rice.rasi.template
├── dunst/dunstrc.template
├── wireplumber/90-rice-no-logind.conf
├── x11/
│   ├── xinitrc
│   ├── session
│   └── Xresources.template
├── scripts/
│   ├── README-network.md
│   ├── rice-lib.sh
│   ├── rice-theme
│   ├── rice-rebuild
│   ├── rice-wallpaper-menu
│   ├── rice-default-wallpaper
│   ├── rice-wifi-status
│   ├── rice-bluetooth-status
│   ├── rice-brightness-status
│   ├── rice-audio-status
│   ├── rice-controls
│   ├── rice-wifi-add
│   ├── rice-picom
│   ├── rice-build
│   └── rice-system-setup
├── sv/
│   ├── dhcpcd/{run,log/run}
│   ├── wpa_supplicant/{run,check,conf.template,log/run}
│   └── bluetoothd/{run,log/run}
└── xbps-src/picom-ibhagwan/template
```

Every listed file is provided in full. Templates are intentional inputs consumed
by the installer/theme renderer; there are no config stubs to fill in. The only
machine-specific inputs are interface/country and network credentials.

## Bar: six fields

Your later brightness/audio additions expand the original four-field request:

```text
[Void] │ ━ ● · · · · · · ·  2 [windows] 1/3       [clock] 14:30 Thu 17       [wifi] MySSID -54dBm   [BT] on   [sun] 65%   [audio] 40%
```

The supplied image is the visual reference: **28px, edge-to-edge, nearly black
wallpaper-tinted background; active-tag pills and inactive dots on the left;
a truly centered clock; compact icon-led indicators on the right**. Labels in
square brackets above represent Nerd Font icons in the actual bar. The Void
logo replaces the reference's distribution logo. Bar corners stay square;
the optional compositor effects apply to application windows.

1. **Current tags/window number** — dwm's `bar-current.h` draws this on X events;
   no polling or EWMH approximation. Multiple viewed tags appear as `1+3`.
   Window numbering follows the visible client list on that monitor, including
   floating clients. An empty view is `0/0`. Occupied tags have brighter dots.
2. **Wi-Fi SSID/status and RSSI** — wpa_supplicant, 10-second cache.
3. **Bluetooth power/connection status** — BlueZ, 30-second cache.
4. **Brightness** — the kernel backlight sysfs values.
5. **Audio volume/mute** — PipeWire/WirePlumber's `wpctl`.
6. **Date/time** — slstatus's native date formatter, 10-second refresh.

slstatus supplies the last five fields. Its semicolon-separated clock is drawn
in the center by flexipatch's extra-status module **on the same bar**, while the
other indicators are right-aligned. The systray
patch is compiled in but `showsystray = 0` keeps the six-field default exact.
Set it to `1` in the dwm template and run `rice-rebuild` to display XEmbed icons.
That adds application-provided icons to the bar, as expected for a tray.

Detailed commands, socket permissions, pairing, device control and status file
semantics are in **[scripts/README-network.md](scripts/README-network.md)**.

## dwm patches and interactions

The installer uses **dwm-flexipatch**, pinned at
`4c963b33681b277a0ff4d3bf39a27b2feab68950` (dwm 6.8 base). `patches.h` selects
its integrated patches; this avoids applying several incompatible stock-dwm
diff contexts in an arbitrary order.

| Patch / flag | Selection and interaction |
|---|---|
| [vanitygaps](https://dwm.suckless.org/patches/vanitygaps/) / `VANITYGAPS_PATCH` | On. 8px inner, 10px outer gaps; runtime adjust/reset/toggle. Use this instead of stacking another gaps implementation. |
| [barpadding](https://dwm.suckless.org/patches/barpadding/) / `BAR_PADDING_PATCH` | Available, set to 0px for the reference's edge-to-edge bar. Its padding stays fixed when window gaps change. `BAR_PADDING_VANITYGAPS_PATCH` is left off; do not enable both variants. |
| [bar height](https://dwm.suckless.org/patches/bar_height/) / `BAR_HEIGHT_PATCH` | On, 28px. |
| `BAR_EXTRASTATUS_PATCH` | On. Splits the centered clock from the right-hand status at a semicolon; both modules are on bar 0. |
| [systray](https://dwm.suckless.org/patches/systray/) / `BAR_SYSTRAY_PATCH` | Compiled in, visibility off by default. Stock systray and barpadding patches can overlap in bar geometry/drawing; flexipatch integrates those changes. Tray belongs to monitor 0. |
| [native rounded corners](https://github.com/bakkeby/dwm-flexipatch/blob/4c963b33681b277a0ff4d3bf39a27b2feab68950/patch/roundedcorners.c) / `ROUNDED_CORNERS_PATCH` | **Off**. Native XShape clipping requires border width 0 for clean results. This template automatically uses 0px if enabled; `config.mk` already links Xext. It requires a rebuild and is independent of the picom toggle. |
| [restartsig](https://dwm.suckless.org/patches/restartsig/) / `RESTARTSIG_PATCH` | On. HUP cleanly execs the new binary; TERM quits. `SELFRESTART_PATCH` is not needed. |
| `SEAMLESS_RESTART_PATCH`, `SAVEFLOATS_PATCH` | On. Preserve supported monitor/client state and floating geometry through WM restarts. This is WM-restart persistence, not reboot/session restoration. |
| [nodmenu](https://dwm.suckless.org/patches/nodmenu/) / `NODMENU_PATCH` | On. Rofi replaces hardcoded dmenu commands. |

The default uses **2px colored borders and square windows**. Opt-in picom rounding
gives the rounded look without rebuilding dwm. Do not combine native XShape
rounding with picom rounding: the two clip paths can disagree, especially at
borders. If choosing native rounding, keep picom's `corner-radius` and
`round-borders` at 0 in every profile. Native rounding also remains visible when
the compositor is stopped.

`bar-current.h` is the small local information module, included through
`config.h`; it does not fork programs or run a timer. The source's ordinary
tags, window-title and layout-symbol bar modules are disabled.

## Wallpaper → palette → build → restart

Installed editable templates live in `~/.config/rice/`. Built source checkouts
live in `~/.local/src/rice/`. Executables live in `~/.local/bin/`.

```sh
rice-theme "$HOME/Pictures/Wallpapers/something.jpg"
# Or: Super+Shift+w, to pick from ~/Pictures/Wallpapers recursively.
```

The theme command:

1. Copies the wallpaper to a staging directory and invokes
   `wal -i IMAGE -n -s -t -e -q` with an isolated pywal cache.
2. Validates the generated `#RRGGBB` palette and substitutes it into full
   `config.h`, rofi, dunst and XTerm templates.
3. Compiles dwm in a temporary source copy. A build error leaves the installed
   executable, active themes and wallpaper intact.
4. Writes literal colors into both `~/.config/rice/dwm/config.h` and
   `~/.local/src/rice/dwm/config.h`, then atomically replaces the **executable**
   `~/.local/bin/rice-dwm` (avoiding an in-place write to a running binary).
5. Publishes `~/.cache/wal/colors.json`, sets the wallpaper with feh, merges
   Xresources, reloads dunst, and HUPs only this session's validated dwm PID.

No root access is needed for wallpaper changes. Dwm's restart patch re-execs the
installed binary; clients survive and supported state is restored. Rofi reads
the new theme on its next launch. New XTerms read the updated Xresources.
An already-open rofi or XTerm does not automatically redraw its palette.

After editing the installed dwm template or patch selections:

```sh
rice-rebuild
```

This reuses the saved palette. `rice-theme --no-reload IMAGE` prepares a theme
without changing a running X session. Edits to generated `config.h` are replaced
on the next rebuild; edit `config.h.template` instead.

## Compositing and compile jobs

| Mode | Behavior |
|---|---|
| `rice-picom low` | Session default: XRender, damage-based repainting, opaque, vsync off, no blur, no rounding, no shadows, no fading. |
| `rice-picom effects` | Toggle low ↔ effects. Effects use GLX, vsync, 10px corners, mild dual-Kawase blur **only for translucent rofi/dunst**. Ordinary application/terminal windows stay opaque. |
| `rice-picom off` | Stop this session's compositor completely. Dwm, gaps, colors, status, rofi and notifications continue to work. |
| `rice-picom toggle` | Off ↔ low. |
| `rice-picom status` | Print `off`, `low`, or `effects`. |

Effects always reset to **low** on a new X session. No idle animation loop or
wallpaper timer exists. Fullscreen unredirection is enabled in both compositor
profiles. XRender is a conservative baseline, not a promise of lower power on
every driver; stopping picom removes its work altogether.

For a compile that shares the Intel CPU/iGPU thermal budget:

```sh
rice-build -- make -j8
```

This stops picom for the command and restores the previous mode on normal exit
or a handled interrupt, retaining the compile command's exit status. Choose the
parallelism suitable for your project and cooling. It does not alter CPU boost,
power limits or scheduler policy.

Picom logs: `~/.cache/rice/log/picom.log`. The wrapper uses a per-display PID and
lock; it controls only its own compositor instance.

## Keybindings

| Keys | Action |
|---|---|
| Super+Return / Super+p | XTerm / rofi |
| Super+1…9 | View a tag |
| Super+Shift+1…9 | Move selected client to a tag |
| Super+Ctrl+1…9 | Toggle tags in the current view |
| Super+Ctrl+Shift+1…9 | Toggle a client's membership on a tag |
| Super+j/k / Super+h/l | Focus next/previous / master ratio |
| Super+i/d | Increase/decrease master count |
| Super+Shift+Return | Promote client to master |
| Super+t/f/m | Tile / floating / monocle |
| Super+Shift+Space | Toggle a client's floating state |
| Super+g / Super+- / Super+= / Super+Shift+g | Toggle / reduce / enlarge / reset gaps |
| Super+b / Super+Tab | Toggle bar / previous view |
| Super+, / Super+. | Focus previous/next monitor |
| Super+Shift+, / Super+Shift+. | Send client to previous/next monitor |
| Super+left/middle/right mouse on a client | Move / float toggle / resize |
| Brightness up/down | Backlight ±5% |
| Volume up/down / mute | Default PipeWire output ±5% / mute |
| Super+F9 / Super+F10 | Compositor off/on / effects toggle |
| Super+Shift+w | Wallpaper picker |
| Super+Shift+r / Super+Shift+q | Restart WM / exit X session |
| Super+Shift+c | Close selected client |

## Exact Void packages and build sources

These are the package commands executed by `install.sh`, in order (shown with
`sudo`; the installer can instead use `doas` or `su`):

```sh
sudo xbps-install -Suy xbps
sudo xbps-install -uy
sudo xbps-install -y base-devel git curl ca-certificates pkg-config python3 python3-Pillow \
  libX11-devel libXft-devel libXinerama-devel libXext-devel fontconfig-devel
sudo xbps-install -y xorg-minimal mesa-dri linux-firmware-intel linux-firmware-network \
  intel-media-driver sof-firmware dejavu-fonts-ttf nerd-fonts-symbols-ttf xterm xprop xrdb xsetroot xset
sudo xbps-install -y runit dbus dhcpcd wpa_supplicant bluez iproute2 util-linux \
  procps-ng shadow bash
sudo xbps-install -y pipewire wireplumber libspa-bluetooth alsa-pipewire pulseaudio-utils
sudo xbps-install -y pywal ImageMagick feh rofi dunst libnotify brightnessctl
```

The modern Intel Xorg path uses the built-in modesetting driver and Mesa.
Intel GPU firmware, network firmware and SOF audio firmware are included;
`intel-media-driver` supplies modern Intel VA-API support. `xorg-minimal` supplies
Xorg, xinit/startx, xauth and libinput input support. `wireplumber` supplies
`wpctl`; `bluez` supplies `bluetoothctl`; `util-linux` supplies `flock`, `rfkill`
and the tools used for runtime checks.
`nerd-fonts-symbols-ttf` supplies the compact bar icons without installing the
entire Nerd Fonts collection; DejaVu Sans Mono supplies the text.

**Custom xbps-src build required: `picom-ibhagwan`.** Void's repository package
named `picom` is the upstream fork, not ibhagwan's. The included template builds
ibhagwan commit `c4107bb6cc17773fdc6c48bb2e475ef957513c7a` and verifies the tarball
SHA-256. The installer performs this custom build automatically; there is no
manual template creation step.

Its build dependencies are `libX11-devel`, `libXext-devel`, `libxcb-devel`,
`libconfig-devel`, `libev-devel`, **`pcre-devel` (PCRE1)**, `pixman-devel`, `uthash`,
`xcb-util-image-devel`, `xcb-util-renderutil-devel`, and `libglvnd-devel`.
The `meson` build style installs Meson/Ninja and `pkg-config` into the xbps-src
build environment. D-Bus compositor control and documentation are disabled.
The package installs `/usr/bin/picom-ibhagwan`, avoiding collision with an
existing upstream picom binary.

Equivalent build/install commands, after the installer has copied the template:

```sh
cd "$HOME/.local/src/rice/void-packages"
./xbps-src binary-bootstrap
./xbps-src -j 2 pkg picom-ibhagwan
sudo xbps-install -y -R "$PWD/hostdir/binpkgs" picom-ibhagwan
```

The void-packages checkout is pinned at
`93ba84918bb407a66c1013f7f3625f5915477ddf`. Package names/templates were checked
against that revision; binary packages come from the configured rolling Void
repositories. The first custom build needs space for an xbps-src masterdir.

dwm and slstatus are intentional **user-local source builds**, not repository
packages. slstatus is pinned at `675c83912ea1aca9834448aaa87a040bc9990c52`.
Only its datetime and run-command components are compiled. Re-running the
installer backs up and reapplies this bundle; everyday template edits should
use `rice-rebuild` rather than reinstalling the bundle.

## VM verification

On the Arch authoring machine, the generated dwm and slstatus configurations
were compiled with existing tools and shell scripts were syntax/lint checked.
The Void installer and hardware services must be exercised in your Void VM;
the full xbps-src/picom build and Intel hardware behavior are not claimed as
tested here.

After installing and starting X in the VM:

```sh
sudo sv status /var/service/dbus /var/service/dhcpcd \
  /var/service/wpa_supplicant /var/service/bluetoothd
wpctl status
pactl info
rice-picom status
rice-theme "$HOME/Pictures/Wallpapers/rice-default.png"
```

Open two XTerms, switch tags, and change the wallpaper: the clients should stay
open through the WM restart. Check rofi and send a themed notification with
`notify-send 'Rice ready' 'Shared pywal palette'`. Test F9/F10. A VM with no GLX
acceleration may reject the effects profile; low/off remain usable. Brightness
and physical Wi-Fi/Bluetooth require hardware or passthrough to test.

Session logs live in `~/.cache/rice/log/`. Network/Bluetooth logs live in
`/var/log/rice/{dhcpcd,wpa_supplicant,bluetoothd}/current`.

## References

- [Void wpa_supplicant handbook](https://docs.voidlinux.org/config/network/wpa_supplicant.html)
- [Void runit services](https://docs.voidlinux.org/config/services/index.html)
- [Void Bluetooth handbook](https://docs.voidlinux.org/config/bluetooth.html)
- [Void PipeWire handbook](https://docs.voidlinux.org/config/media/pipewire.html)
- [Void Intel graphics](https://docs.voidlinux.org/config/graphical-session/graphics-drivers/intel.html)
- [dwm-flexipatch](https://github.com/bakkeby/dwm-flexipatch)
- [slstatus](https://tools.suckless.org/slstatus/)
- [ibhagwan/picom](https://github.com/ibhagwan/picom)
