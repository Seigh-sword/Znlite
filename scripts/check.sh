#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
for script in "$ROOT/scripts/build.sh" "$ROOT/scripts/make-iso.sh" "$ROOT/board/znlite/x86_64/post-build.sh"; do
    sh -n "$script"
done
grep -F 'BR2_LINUX_KERNEL_CUSTOM_TARBALL_LOCATION="https://github.com/gregkh/linux/archive/refs/tags/v6.12.111.tar.gz"' "$ROOT/configs/znlite_x86_64_defconfig" >/dev/null
grep -F 'BR2_TARGET_ROOTFS_CPIO_GZIP=y' "$ROOT/configs/znlite_x86_64_defconfig" >/dev/null
grep -F 'v6.12.111.tar.gz' "$ROOT/patches/buildroot/0001-linux-hash-6.12.111.patch" >/dev/null
grep -F 'CONFIG_ACPI_BATTERY=y' "$ROOT/board/znlite/x86_64/linux.fragment" >/dev/null
if [ -d "$ROOT/build/buildroot/.git" ]; then
    BUILDROOT_DIR="$ROOT/build/buildroot"
    EXPECTED_COMMIT=d5180309b1b66ef3b8eaccca70ad69be8e0729a1
    ACTUAL_COMMIT=$(git -C "$BUILDROOT_DIR" rev-parse HEAD)
    [ "$ACTUAL_COMMIT" = "$EXPECTED_COMMIT" ]
    make -C "$BUILDROOT_DIR" O="$ROOT/build/config-check" BR2_EXTERNAL="$ROOT" znlite_x86_64_defconfig
    make -C "$BUILDROOT_DIR" O="$ROOT/build/config-check" BR2_EXTERNAL="$ROOT" olddefconfig
fi
printf '%s\n' 'Znlite configuration checks passed.'
