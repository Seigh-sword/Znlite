#!/bin/sh
set -eu
ROOT=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
BUILD_ROOT="$ROOT/build"
DOWNLOAD_DIR="$BUILD_ROOT/dl"
SOURCE_PARENT="$BUILD_ROOT/src"
KERNEL_LOCK="$ROOT/kernel/source.lock"
KERNEL_VERSION=$(sed -n 's/^version=//p' "$KERNEL_LOCK")
KERNEL_PACKAGE_REVISION=$(sed -n 's/^package_revision=//p' "$KERNEL_LOCK")
KERNEL_LOCALVERSION=$(sed -n 's/^localversion=//p' "$KERNEL_LOCK")
KERNEL_ARCHIVE="$DOWNLOAD_DIR/v$KERNEL_VERSION.tar.gz"
KERNEL_URL=$(sed -n 's/^archive_url=//p' "$KERNEL_LOCK")
KERNEL_SHA256=$(sed -n 's/^sha256=//p' "$KERNEL_LOCK")
KERNEL_SOURCE="$SOURCE_PARENT/linux-$KERNEL_VERSION"
LIVE_BUILD_DIR="$BUILD_ROOT/live-build"
OUTPUT_DIR="$BUILD_ROOT/output"
JOBS=${JOBS:-2}
for command in curl sha256sum tar make lb sudo dpkg-deb find sed python3; do
    if ! command -v "$command" >/dev/null 2>&1; then
        printf 'Missing build dependency: %s\n' "$command" >&2
        exit 1
    fi
done
mkdir -p "$DOWNLOAD_DIR" "$SOURCE_PARENT" "$OUTPUT_DIR"
if [ ! -f "$KERNEL_ARCHIVE" ]; then
    curl --fail --location --retry 3 "$KERNEL_URL" --output "$KERNEL_ARCHIVE"
fi
printf '%s  %s\n' "$KERNEL_SHA256" "$KERNEL_ARCHIVE" | sha256sum --check --status || {
    printf '%s\n' 'Linux source checksum verification failed.' >&2
    exit 1
}
printf '%s  %s\n' "$KERNEL_SHA256" "$(basename -- "$KERNEL_ARCHIVE")" > "$KERNEL_ARCHIVE.sha256"
if [ ! -f "$KERNEL_SOURCE/Makefile" ]; then
    mkdir -p "$KERNEL_SOURCE"
    tar --extract --gzip --file "$KERNEL_ARCHIVE" --strip-components=1 --directory "$KERNEL_SOURCE" --no-same-owner
fi
"$ROOT/scripts/configure-kernel.sh" "$KERNEL_SOURCE" "$OUTPUT_DIR"
KERNEL_RELEASE=$(make -s -C "$KERNEL_SOURCE" ARCH=x86 LOCALVERSION="$KERNEL_LOCALVERSION" kernelrelease)
if [ "$KERNEL_RELEASE" != "$KERNEL_VERSION$KERNEL_LOCALVERSION" ]; then
    printf 'Unexpected kernel release string: %s\n' "$KERNEL_RELEASE" >&2
    exit 1
fi
find "$SOURCE_PARENT" -maxdepth 1 -type f -name 'linux-image-*.deb' -delete
make -C "$KERNEL_SOURCE" -j"$JOBS" ARCH=x86 LOCALVERSION="$KERNEL_LOCALVERSION" KDEB_PKGVERSION="$KERNEL_VERSION-$KERNEL_PACKAGE_REVISION" bindeb-pkg
KERNEL_DEB=$(find "$SOURCE_PARENT" -maxdepth 1 -type f -name "linux-image-${KERNEL_RELEASE}_*_amd64.deb" ! -name '*dbg*' -print -quit)
if [ -z "$KERNEL_DEB" ]; then
    printf '%s\n' 'The kernel build completed without producing a Debian image package.' >&2
    exit 1
fi
if [ -d "$LIVE_BUILD_DIR" ]; then
    sudo rm -rf -- "$LIVE_BUILD_DIR"
fi
mkdir -p "$LIVE_BUILD_DIR"
cp -R "$ROOT/live-build/." "$LIVE_BUILD_DIR/"
sudo mkdir -p "$LIVE_BUILD_DIR/config/packages.chroot"
sudo cp "$KERNEL_DEB" "$LIVE_BUILD_DIR/config/packages.chroot/"
cd "$LIVE_BUILD_DIR"
sudo lb config
sudo lb bootstrap
sudo lb chroot
if [ -e "chroot/boot/initrd.img-$KERNEL_RELEASE" ]; then
    sudo chroot chroot update-initramfs -u -k "$KERNEL_RELEASE"
else
    sudo chroot chroot update-initramfs -c -k "$KERNEL_RELEASE"
fi
printf '%s\n' 'LB_LINUX_PACKAGES="linux-image"' | sudo tee -a config/binary >/dev/null
sudo lb binary
ISO=$(find "$LIVE_BUILD_DIR" -maxdepth 2 -type f -name '*.iso' -print -quit)
if [ -z "$ISO" ]; then
    printf '%s\n' 'The live-build completed without producing an ISO.' >&2
    exit 1
fi
cp "$ISO" "$OUTPUT_DIR/znlite-live-x86_64.iso"
cp "$KERNEL_DEB" "$OUTPUT_DIR/znlite-kernel-6.12.111-amd64.deb"
(
    cd "$OUTPUT_DIR"
    sha256sum znlite-live-x86_64.iso znlite-kernel-6.12.111-amd64.deb kernel.config kernel-audit.json > SHA256SUMS
)
printf '%s\n' 'Znlite live ISO and custom kernel package built successfully.'
printf 'ISO: %s\n' "$OUTPUT_DIR/znlite-live-x86_64.iso"
printf 'Kernel package: %s\n' "$OUTPUT_DIR/znlite-kernel-6.12.111-amd64.deb"
printf 'Kernel source: %s\n' "$KERNEL_SOURCE"
