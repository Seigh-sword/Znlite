# Znlite Linux

Znlite is an experimental, text-only Linux distribution for older laptops. This first usable design is based on Debian 13 Trixie so the installed system has APT and can be expanded with packages later. The live image has no graphical desktop or X server.

Acer TravelMate B is a product family, not one hardware specification. Acer publishes separate support pages for models such as the B115-M and B117-M. Those families include different processor, Wi-Fi, storage, and firmware combinations. Intel's specifications identify both the Celeron N2840 and N3060 as 64-bit processors, so the current amd64 target is a reasonable starting point for those variants. The exact model code is still needed to confirm its wireless device and boot firmware.

- [Acer TravelMate B115-M support](https://www.acer.com/us-en/support?search=TravelMate+B115-M&filter=global_download)
- [Acer TravelMate B117-M support](https://www.acer.com/gb-en/support/product-support/TravelMate_B117-M)
- [Intel Celeron N2840 specifications](https://www.intel.com/content/www/us/en/products/sku/82103/intel-celeron-processor-n2840-1m-cache-up-to-2-58-ghz/specifications.html)
- [Intel Celeron N3060 specifications](https://www.intel.com/content/www/us/en/products/sku/91832/intel-celeron-processor-n3060-2m-cache-up-to-2-48-ghz/specifications.html)

## What this build includes

- A Debian 13 text-only live image with a text installer and APT.
- A custom Debian kernel package built from the pinned upstream Linux 6.12.111 source.
- Kernel settings for laptop ACPI and battery reporting, Intel integrated graphics, common storage, audio, USB, and a broad selection of Intel, Realtek, Atheros, Broadcom, and Ralink network devices.
- Selected non-free firmware packages from Debian's firmware repository.
- BIOS and 64-bit UEFI boot paths and a QEMU boot smoke test in GitHub Actions.

No desktop packages are installed in the image. After installing Znlite to disk and connecting to a network, a desktop can be added with APT, for example `sudo apt update` followed by `sudo apt install xfce4 lightdm`. Packages added to a temporary live session are lost when it reboots; install Znlite to a drive first if changes need to persist.

This is an early preview, not a finished independent package distribution. It uses Debian's package repositories and release process. Hardware support has not yet been tested on the exact laptop. It has no Znlite update repository, custom desktop, or long-term security-maintenance policy. Do not replace an existing installation until the image has been tested and important data is backed up.

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

Run the configuration checks with `./scripts/check.sh`. GitHub Actions performs these checks, builds the ISO and kernel package, boots the ISO under QEMU, and uploads the ISO, kernel package, and verified upstream source archive as artifacts. A successful artifact can then be published as a preview GitHub Release.

## Hardware details needed

Please send the full model code from the bottom label, such as `TravelMate B115-M-...` or `B117-M-...`, plus the amount of RAM. Wi-Fi chips can vary even within a model family. From an existing Linux installation, these commands help identify the hardware:

```sh
lscpu
free -h
lspci -nn
lsusb
```
