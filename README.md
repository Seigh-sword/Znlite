# Znlite Linux

Znlite is an experimental, text-only Linux distribution for older laptops. This first usable design is based on Debian 13 Trixie so the installed system has APT and can be expanded with packages later. The live image has no graphical desktop or X server.

Acer TravelMate B is a product family, not one hardware specification. Acer publishes separate support pages for models such as the B115-M and B117-M. Those families include different processor, Wi-Fi, storage, and firmware combinations. Intel's specifications identify both the Celeron N2840 and N3060 as 64-bit processors, so the current amd64 target is a reasonable starting point for those variants. The exact model code is still needed to confirm its wireless device and boot firmware.

- [Acer TravelMate B115-M support](https://www.acer.com/us-en/support?search=TravelMate+B115-M&filter=global_download)
- [Acer TravelMate B117-M support](https://www.acer.com/gb-en/support/product-support/TravelMate_B117-M)
- [Intel Celeron N2840 specifications](https://www.intel.com/content/www/us/en/products/sku/82103/intel-celeron-processor-n2840-1m-cache-up-to-2-58-ghz/specifications.html)
- [Intel Celeron N3060 specifications](https://www.intel.com/content/www/us/en/products/sku/91832/intel-celeron-processor-n3060-2m-cache-up-to-2-48-ghz/specifications.html)

## What this build includes

- A Debian 13-based text-only live image with Znlite Aurora identity, boot menus, and a text installer.
- A cyan mascot/system-info display (`znfetch` or `neofetch`), themed shell prompt, and optional reveal animation.
- A FreeType-rendered vector-font console on tty1, using Kmscon and DejaVu Sans Mono, with native raster rescue consoles.
- A guarded `znlite update` command for signed APT package updates.
- A custom Debian kernel package built from the pinned upstream Linux 6.12.111 source.
- Kernel settings for laptop ACPI and battery reporting, Intel integrated graphics, common storage, audio, USB, and a broad selection of Intel, Realtek, Atheros, Broadcom, and Ralink network devices.
- Selected non-free firmware packages from Debian's firmware repository.
- BIOS and 64-bit UEFI boot paths and a QEMU boot smoke test in GitHub Actions.

No desktop packages are installed in the image. After installing Znlite to disk and connecting to a network, a desktop can be added with APT, for example `sudo apt update` followed by `sudo apt install xfce4 lightdm`. Packages added to a temporary live session are lost when it reboots; install Znlite to a drive first if changes need to persist.

This is an early preview, not a finished independent package distribution. It uses Debian's package repositories and release process. Hardware support has not yet been tested on the exact laptop. It has no Znlite update repository, custom desktop, or long-term security-maintenance policy. Do not replace an existing installation until the image has been tested and important data is backed up.

## Aurora appearance and commands

Znlite remains terminal-only: there is **no desktop, display manager, or X server**. Its own `/etc/os-release`, login message, cyan-on-midnight console palette, prompt, and BIOS/UEFI menus replace the stock Debian presentation. The underlying distribution is still Debian, and tools that inspect `/etc/debian_version` or package origins will correctly show that relationship. Debian's installer and third-party applications retain their upstream branding.

```sh
znfetch                       # Real, offline system information + mascot
neofetch                      # Familiar entry point for the same Znlite tool
znfetch --full                # Always show the full user-supplied mascot
znlite welcome --animate     # Optional short line-reveal effect
znlite help
```

The supplied mascot and its cyan shading are preserved in `usr/local/share/znlite/mascot.txt` and `mascot.awk` inside the image. CPU, memory, kernel, uptime, packages, shell, and disk information are read from the running machine; no external IP service or telemetry is contacted. Large terminals get the full mascot alongside the information. Smaller terminals get a compact mark; `--full` always shows the original. The `neofetch` command is a wrapper for our own tool, **not upstream neofetch or its entire option set**.

Effects are deliberately restrained: animation is opt-in, never delays login, and is disabled for redirected output/dumb terminals. `NO_COLOR=1` disables color, `ZNLITE_NO_ANIMATION=1` disables animation, `ZNLITE_WELCOME=0` suppresses the automatic greeting, and `ZNLITE_THEME=0` disables the shell customization. Put preferences in `~/.profile` (before it sources `~/.bashrc`) or export them before starting a shell. Serial/noninteractive commands do not get forced animation, and noninteractive shell startup stays silent.

### Vector fonts by default, raster available

The kernel's VT console cannot directly render scalable outlines. **Kmscon + FreeType** renders TrueType outlines on **tty1** using DRM/framebuffer access, without starting a desktop. DejaVu Sans Mono at 18 pixels is the default. The font is downloaded during the image build from Debian's signed `fonts-dejavu-core` package, not from an unverified font mirror. Kmscon and libtsm4 are explicitly selected from signed **Trixie backports**, which is also kept in the installed system's APT sources for their updates; the rest of the image stays on Trixie unless a dependency requires otherwise.

```sh
znlite fonts status
sudo znlite fonts raster     # Native bitmap VT on tty1 after the next boot
sudo znlite fonts vector     # Restore the scalable-font default next boot
```

Font changes do not kill your current login session. Edit `/etc/kmscon/kmscon.conf` as root to change the vector family, size, palette, or XKB keyboard layout (for example `xkb-layout=us`). Kmscon supports Ctrl-plus / Ctrl-minus for changing font size in the current session. On a live image, persistent preferences require persistent storage or installation to disk.

**Rescue paths:** Ctrl+Alt+F2 opens an independently enabled raster login. Serial gettys are unchanged. Both boot menus provide a raster-rescue entry; adding `znlite.console=raster` to the kernel command line also bypasses Kmscon. If there is no display device, or Kmscon exits, tty1 falls back to a normal raster login. A renderer that hangs without exiting may still require switching to tty2 or booting rescue. Bootloader text, early kernel messages, and rescue VTs remain bitmap-rendered; vector rendering starts at the userspace login console. The original mascot is still ASCII art—vector *fonts* do not turn it into an SVG image.

Vector output needs testing on the target GPU. The existing serial QEMU smoke test verifies boot/login, **not** vector rendering. On the actual laptop, check `journalctl -b -u getty@tty1`, try both font modes, and confirm Ctrl+Alt+F2 works before relying on this preview.

### Updating the system

```sh
sudo znlite update --check    # Refresh package lists and preview changes
sudo znlite update            # Refresh, then review APT's full-upgrade confirmation
sudo znlite update --yes      # Explicitly accept APT's confirmation
```

APT downloads and verifies packages through the configured repositories. A failed index refresh stops the command before upgrading. APT retains its normal lock and dependency handling. Znlite does not automatically remove packages, reboot the machine, switch Debian releases, or run remote installation scripts. Back up important files, check free disk space, and keep the laptop connected to power before upgrading. `--check` updates the package indexes but does not install/remove packages.

Live sessions are refused by default because upgrades consume the writable overlay and can disappear at reboot. Use `sudo znlite update --allow-live` only when you understand that limitation.

**Current scope:** this updates Debian-provided applications, libraries, firmware, and the installed backports packages. There is **no signed Znlite release repository yet**, so the custom `-znlite` kernel and files supplied by the image overlay (Znlite commands, branding, and configuration) are **not** updated by this command. They require a new verified image or a deliberately installed replacement package. This is not an automatic Znlite release-upgrade mechanism, and the custom kernel must not be assumed to receive Debian kernel security updates.

## The Linux kernel source

The kernel source is not copied into Git because the source archive is about 235 MB and its extracted tree is much larger. `kernel/source.lock` records the exact upstream tag, commit, download URL, and SHA-256. `scripts/build.sh` downloads the archive, verifies it, extracts it to `build/src/linux-6.12.111`, trims the generic x86-64 configuration, applies `kernel/znlite.fragment`, builds a Debian kernel package, and includes that package in the ISO. The upstream C source remains unchanged for now; source patches should follow a reproducible hardware bug or measured need.

GitHub Actions publishes the exact kernel source archive alongside the ISO and `.deb` package when a preview release is created. The kernel configuration and reproducible build steps are visible in this repository.

## Build locally

The build host needs Debian/Ubuntu packages for kernel compilation, Debian live-build, and ISO creation. For example:

```sh
sudo apt update
sudo apt install bc bison build-essential ca-certificates cpio curl debhelper dpkg-dev dwarves fakeroot file flex git grub-common grub-efi-amd64-bin grub-pc-bin initramfs-tools libelf-dev libssl-dev live-build make mtools qemu-system-x86 rsync sudo xorriso
```

Run the build with a conservative job count:

```sh
JOBS=2 ./scripts/build.sh
```

This build uses `sudo` for Debian live-build. It writes generated files under the ignored `build/` directory:

- `build/output/znlite-live-x86_64.iso`
- `build/output/znlite-kernel-6.12.111-amd64.deb`
- `build/output/SHA256SUMS`
- `build/dl/v6.12.111.tar.gz`

Run the configuration checks with `./scripts/check.sh` and the boot-wrapper and user-command regression tests with `python3 -m unittest discover -s tests -v` (Python 3 is required; QEMU/APT/video operations are mocked and the tests neither boot an image nor upgrade the host). GitHub Actions runs on pushes, pull requests, and manual dispatches. It performs these checks, builds the ISO and kernel package, uploads the ISO, kernel package, and verified upstream source archive as candidate artifacts, and boots the ISO under QEMU. Artifacts are retained even if the boot test fails; only artifacts from a successful run should be published as a preview GitHub Release. Failed runs also upload the configuration, test, build, and QEMU logs as `znlite-failure-diagnostics`.

The BIOS menu boots its default live entry after five seconds without keyboard input. Run `./scripts/smoke-test.sh` to test the built ISO locally. The test uses headless QEMU software emulation and requires a serial login prompt, allowing up to 300 seconds for slow CI hosts. Override that limit with `QEMU_TIMEOUT=600 ./scripts/smoke-test.sh` if needed. No VNC server or host audio service is required.

### Appearance assets and validation

`./scripts/check.sh` checks shell syntax, required packages, and basic boot configuration. `python3 -m unittest discover -s tests -v` covers the fetch layouts/color fallbacks, updater safeguards, console fallback, and QEMU wrapper. Build hooks verify that the selected font and Kmscon are present. Actual DRM/font rendering and the Debian installer still need hardware/VM testing after rebuilding the ISO.

The original boot backdrop is generated by `scripts/make-boot-art.py` using Pillow and the system DejaVu fonts; the small generated PNGs are included for reproducible builds without an art-generation dependency. Font copyright/license information is supplied by Debian at `/usr/share/doc/fonts-dejavu-core/copyright`. The mascot comes from the user-provided artwork, not a downloaded image.

References for the console integration:
- [Kmscon in Trixie backports](https://packages.debian.org/trixie-backports/kmscon)
- [Kmscon configuration and font options](https://manpages.debian.org/trixie-backports/kmscon/kmscon.1.en.html)
- [Upstream authenticated VT service](https://github.com/kmscon/kmscon/blob/v10.0.1/scripts/systemd/kmsconvt%40.service.in)

## Hardware details needed

Please send the full model code from the bottom label, such as `TravelMate B115-M-...` or `B117-M-...`, plus the amount of RAM. Wi-Fi chips can vary even within a model family. From an existing Linux installation, these commands help identify the hardware:

```sh
lscpu
free -h
lspci -nn
lsusb
```
