#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
BUILD_ROOT="$ROOT/build"
BUILDROOT_DIR="$BUILD_ROOT/buildroot"
OUTPUT_DIR="$BUILD_ROOT/output"
BUILDROOT_TAG=2026.08
BUILDROOT_COMMIT=d5180309b1b66ef3b8eaccca70ad69be8e0729a1
KERNEL_HASH=597f2f0f549f9bbd649b1e3f8f82af0fb5f8e389983cb6748523c3559857c2ab
mkdir -p "$BUILD_ROOT"
if [ ! -d "$BUILDROOT_DIR/.git" ]; then
    git clone --depth 1 --branch "$BUILDROOT_TAG" https://github.com/buildroot/buildroot.git "$BUILDROOT_DIR"
fi
ACTUAL_COMMIT=$(git -C "$BUILDROOT_DIR" rev-parse HEAD)
if [ "$ACTUAL_COMMIT" != "$BUILDROOT_COMMIT" ]; then
    printf 'Unexpected Buildroot revision: %s\nExpected: %s\n' "$ACTUAL_COMMIT" "$BUILDROOT_COMMIT" >&2
    exit 1
fi
HASH_FILE="$BUILDROOT_DIR/linux/linux.hash"
if ! grep -F "$KERNEL_HASH  v6.12.111.tar.gz" "$HASH_FILE" >/dev/null 2>&1; then
    git -C "$BUILDROOT_DIR" apply "$ROOT/patches/buildroot/0001-linux-hash-6.12.111.patch"
fi
JOBS=${JOBS:-$(getconf _NPROCESSORS_ONLN 2>/dev/null || printf '2')}
make -C "$BUILDROOT_DIR" O="$OUTPUT_DIR" BR2_EXTERNAL="$ROOT" znlite_x86_64_defconfig
make -C "$BUILDROOT_DIR" O="$OUTPUT_DIR" BR2_EXTERNAL="$ROOT" -j"$JOBS"
"$ROOT/scripts/make-iso.sh" "$OUTPUT_DIR/images" "$OUTPUT_DIR/images/znlite-live.iso"
