# Znlite Linux

Znlite is a new, lightweight Linux distribution project for older laptops. It did not exist as a finished distribution before this repository was initialized. This repository now contains its first buildable system design: a minimal, x86-64 live image assembled with Buildroot and a customized upstream Linux kernel configuration.

## First prototype

The initial image is a small, text-mode live system intended to check that the kernel boots and recognizes laptop hardware. It includes a recent Linux 6.12 LTS kernel, BusyBox, device management, ConnMan, ACPI and power controls, and a selected set of common Intel, Broadcom, Atheros, and Realtek drivers and firmware.

This is an early prototype, not a finished daily-use operating system. It has no graphical desktop, installer, persistent storage setup, Znlite package repository, or unattended security-update service yet. Do not use it as your only operating system or write it over a laptop's internal drive.

The first build targets 64-bit x86 laptops. A 32-bit-only laptop needs a separate build target. Hardware-specific tuning is intentionally deferred until the exact laptop model and devices are known; disabling drivers without that information can make Wi-Fi, graphics, audio, suspend, or storage stop working.

## Build a live ISO

The build downloads pinned Buildroot and Linux sources, verifies the Linux source archive against a SHA-256 checksum, compiles the system, and creates a bootable ISO. Generated sources, downloads, and output images stay under the ignored `build/` directory.

On Debian or Ubuntu, install the host tools first:

```sh
sudo apt install bc bison build-essential cpio file flex g++ gcc git libelf-dev libncurses-dev make patch python3 rsync unzip wget xorriso mtools grub-common grub-pc-bin grub-efi-amd64-bin
```

Then build with a conservative number of parallel jobs on a low-memory machine:

```sh
JOBS=2 ./scripts/build.sh
```

The ISO is written to `build/output/images/znlite-live.iso`. Use a USB imaging tool such as Fedora Media Writer or balenaEtcher, select the USB device carefully, then boot the laptop from that USB device. The build currently requires an internet connection and several gigabytes of free disk space.

## Project layout

- `configs/znlite_x86_64_defconfig` defines the minimal root filesystem and selected hardware support.
- `board/znlite/x86_64/linux.config` is the baseline PC kernel configuration.
- `board/znlite/x86_64/linux.fragment` adds laptop power, storage, input, audio, graphics, and wireless support.
- `scripts/build.sh` fetches pinned Buildroot sources and builds the image.
- `scripts/make-iso.sh` packages the kernel and live root filesystem as an ISO.
- `patches/buildroot/` adds the verifiable checksum for the selected upstream kernel archive to the pinned Buildroot checkout.

The Linux source is fetched during the build rather than checked into this repository. Kernel source trees are very large; the source version, archive location, and checksum are recorded in the build configuration and patch.

## Hardware details needed for the next iteration

To tune the kernel and choose an appropriately light desktop, send the laptop's exact make and model, processor, RAM, and Wi-Fi adapter. From an existing Linux installation, useful output is:

```sh
lscpu
free -h
lspci -nn
lsusb
```

The correct next step is to test this live image on the target laptop, record what works and what fails, then make narrow, reproducible kernel or system changes against that hardware. A kernel configuration is already being customized; broad source-code changes without a reproducible problem or target device would make the first image less reliable, not less bloated.
