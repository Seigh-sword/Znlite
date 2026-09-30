# Znlite Aurora

**A customizable, lightweight Debian-based desktop—not a laptop-specific or
text-only distribution.** Aurora 0.3 targets 64-bit Intel/AMD PCs and virtual
machines. Its default experience is a Sway Wayland tiling desktop; the console is
an alternative and a recovery path. You can replace the desktop, change its
configuration, install software with APT, and rebuild the kernel from public policy
files. There is no proprietary customization layer or locked-down preset.

“Lightweight” means deliberate defaults and demand-loaded components. It does not
mean literally zero background services, guaranteed speed gains, or support for
every device ever made. Broad drivers/firmware and a usable graphical session make
the image larger than the earlier console-only builds. ARM requires separate images
and is not a target of this release.

## Default experience

- **Sway + Waybar + Fuzzel:** tiling, workspaces, launcher and an editable status bar.
- **Foot, Mako, Thunar, PipeWire/WirePlumber:** terminal, notifications, file manager
  and audio; NetworkManager and a policy agent handle desktop permissions/networking.
- Scalable DejaVu fonts and the cyan-on-midnight Aurora palette; XWayland for legacy
  X applications. No games, office suite, browser bundle or full desktop metapackage
  is forced into the base image. Add the applications you want through APT.
- Intel, AMD, Nouveau and common VM graphics support, modern Wi-Fi modules,
  firmware, AMD/Intel microcode, and optional virtualization/network-filesystem support.
- Compressed RAM swap, dynamic preemption and on-demand drivers—not overclocking,
  hidden security downgrades, or “magic” performance sysctls.
- A bounded, opt-out **Debian mirror measurement** in the background after boot.
- Your original cyan mascot with real, offline system information: `znfetch` or
  `neofetch`. The latter invokes our tool, not upstream neofetch's entire CLI.

This is experimental preview software. Back up important files before installing.
GPU acceleration, proprietary NVIDIA drivers, Secure Boot, suspend/hibernate and
individual Wi-Fi devices need platform-specific testing. Open-driver support is
not a guarantee of proprietary-driver compatibility or gaming performance.

## Login and first steps

The default image uses a **text login greeter that launches the graphical Sway
session after authentication**. It is not a graphical login screen, nor a shell-only
OS. The Debian live-user account is provisioned by live-config. Do not expose a live
session with default credentials to an untrusted network; set your own credentials
when installing. Desktop settings changed in a nonpersistent live session disappear
at reboot.

| Shortcut | Action |
| --- | --- |
| Super+Return | Terminal |
| Super+D | Application launcher |
| Super+E | File manager |
| Super+1…5 | Workspace |
| Super+Shift+1…5 | Move window to workspace |
| Super+F | Fullscreen |
| Super+Shift+Space | Floating/tiling |
| Super+R | Resize mode; Escape to leave |
| Super+Shift+C | Reload configuration |
| Super+Ctrl+L | Lock screen |
| Super+Shift+E | Confirm logout |
| Print | Select screenshot region → clipboard |
| Ctrl+Alt+F2 | Independent raster rescue login |

## Make it yours

```sh
znlite customize init                # Editable copies; existing files are kept
znlite customize preset minimal      # Less decoration
znlite customize preset aurora       # Restore Aurora spacing/borders
znlite doctor                        # Read-only system report
znfetch --full
znlite welcome --animate             # Optional terminal mascot reveal
```

`~/.config/sway/config` overrides the distribution Sway configuration. Foot, Waybar,
Fuzzel, Mako and GTK files live under their usual `~/.config` directories. Shared
fallback defaults are in `/etc/xdg/znlite`; users are not forced to copy them first.
`~/.config/znlite/sway.local.conf` is included last for personal tweaks; presets only
manage `~/.config/znlite/preset.conf` and refuse to overwrite manually edited content.
These paths also respect a custom `XDG_CONFIG_HOME`.
Reload with Super+Shift+C. Some application settings need that application restarted.

There are no stock blur or animation patches in Sway. You can change colors, fonts,
opacity, gaps, layouts, bindings, outputs, bar modules and applications, or choose
another compositor yourself. Presets are small and inspectable, not an opaque
configuration generator. `NO_COLOR`, `ZNLITE_WELCOME=0`, `ZNLITE_THEME=0` and
`ZNLITE_NO_ANIMATION=1` control terminal customization independently of the desktop.

```sh
znlite session status
sudo znlite session console          # Console-only next boot; current session stays
sudo znlite session graphical        # Restore the graphical next-boot default
sudo znlite fonts raster             # Console-only mode's tty1 font renderer
sudo znlite fonts vector             # Kmscon/FreeType in console-only mode
```

Both firmware boot menus have a rescue entry using
`systemd.unit=multi-user.target znlite.console=raster`; it does not launch Sway or
the greeter. Serial and tty2 logins remain available. Console font commands do not
change Wayland application fonts. To replace Sway, install/configure your chosen
desktop and change `/etc/greetd/config.toml` or install your preferred display manager.

## Automatic mirror selection

A timer starts a low-priority, best-effort measurement about 30 seconds after boot;
it **does not hold up login or wait for network-online**. Up to eight configured
HTTPS mirrors are supported. Each must serve Debian-signed, correctly named,
unexpired metadata for Trixie, updates and backports. A small package-index sample
adds a throughput measurement. The fastest successful sample wins—not necessarily
the globally fastest mirror or the fastest for all future downloads. Network
conditions vary. The initial list includes Debian's CDN and several public mirrors;
add appropriate local mirrors yourself in `/etc/znlite/mirrors.json`.

```sh
znlite mirror status
sudo znlite mirror select            # Re-measure now, if auto-selection is enabled
sudo znlite mirror auto off
sudo znlite mirror auto on
journalctl -u znlite-mirrors.service
```

The selector only changes `/etc/apt/sources.list.d/znlite.sources` while its stored
ownership hash matches. **Editing that file or adding another repository freezes
selection**, even if automatic mode is on. This conservative rule protects custom
repositories. There is no command that silently adopts or overwrites a user's APT
setup. Security updates stay on `security.debian.org`; Debian key verification and
APT's package/index hash checks stay enabled. The sample itself is not installed or
trusted as a package. This is not an APT update or upgrade service.

Offline boots, failed signatures, stale metadata or busy APT locks keep the existing
source selection. Each request is bounded, and the service has a 90-second limit.
APT's lock is only held during the final atomic write, not during network probes.
Results are stored in `/var/lib/znlite-mirrors/last-run.json`. An offline boot is not
retried continuously; run the command after connecting or wait until the next boot.

## Updates and performance

```sh
sudo znlite update --check            # Refresh lists and simulate a full upgrade
sudo znlite update                    # Review and confirm package changes
```

The command retains APT's locking, signature checks and confirmation. It does not
reboot, change Debian releases or autoremove. Live updates require `--allow-live`.
**Custom kernel, image-overlay tools and branding still do not have a signed Znlite
update repository.** They require a new image or deliberately installed replacement
packages; do not assume `znlite update` patches the custom kernel.

Zram uses LZ4 with logical swap capped at half RAM or 2 GiB. This uses CPU and memory,
not extra physical RAM. Add `systemd.zram=0` at boot to compare without it. Security
mitigations and memory hardening remain enabled. Measure your workloads and thermals
before making claims about speed or battery life. See [desktop/kernel policy notes](docs/desktop-profile.md).

## Build and verification

The build remains based on Debian 13 Trixie, with Kmscon/libtsm4 from signed Trixie
backports. Linux 6.12.111 source is hash-pinned in `kernel/source.lock`; the general
PC/VM configuration uses release `6.12.111-znlite3`. All four kernel fragments are
checked against the kernel's resolved configuration. The upstream C source is not
modified or copied into this repository.

Use the build dependencies in `.github/workflows/release.yml` on a Debian/Ubuntu
host with the compatible Debian live-build version, then:

```sh
./scripts/check.sh
python3 -m unittest discover -s tests -v
JOBS=2 ./scripts/build.sh
```

Outputs under ignored `build/output/` include the ISO, custom kernel **and matching
headers** packages, `kernel.config`, `kernel-audit.json`, and `SHA256SUMS`. The exact
upstream source archive is also uploaded. Headers let you deliberately build
additional modules; DKMS and proprietary drivers need separate validation.

GitHub Actions builds the image, validates the Sway configuration with a headless
backend in the chroot, and runs a BIOS/serial-login QEMU smoke test. Unit tests cover
kernel policy, mirror failure/ownership/signature handling, update safeguards and
non-destructive customization. **A serial-login success is not a graphical desktop,
GPU, audio, VPN, mirror-speed or installer acceptance test.** Hardware and interactive
desktop testing are required before treating a new artifact as ready for daily use.

The artifact is named `znlite-x86_64-aurora`; failure logs are retained separately.
Older `text-only` artifacts are historical, not the new desktop profile.
