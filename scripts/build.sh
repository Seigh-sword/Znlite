#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
BUILD_ROOT="$ROOT/build"
DOWNLOAD_DIR="$BUILD_ROOT/dl"
SOURCE_PARENT="$BUILD_ROOT/src"
KERNEL_LOCK="$ROOT/kernel/source.lock"
KERNEL_VERSION=$(sed -n 's/^version=//p' "$KERNEL_LOCK")
KERNEL_ARCHIVE="$DOWNLOAD_DIR/v$KERNEL_VERSION.tar.gz"
KERNEL_URL=$(sed -n 's/^archive_url=//p' "$KERNEL_LOCK")
KERNEL_SHA256=$(sed -n 's/^sha256=//p' "$KERNEL_LOCK")
KERNEL_SOURCE="$SOURCE_PARENT/linux-$KERNEL_VERSION"
LIVE_BUILD_DIR="$BUILD_ROOT/live-build"
OUTPUT_DIR="$BUILD_ROOT/output"
JOBS=${JOBS:-2}
for command in curl sha256sum tar make lb sudo dpkg-deb find sed; do
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
make -C "$KERNEL_SOURCE" ARCH=x86 x86_64_defconfig
(
    cd "$KERNEL_SOURCE"
    ./scripts/config \
        --disable HIBERNATION \
        --disable KEXEC \
        --disable CRASH_DUMP \
        --disable DEBUG_KERNEL \
        --disable DEBUG_INFO \
        --disable DEBUG_INFO_BTF \
        --disable DEBUG_INFO_DWARF5 \
        --disable FTRACE \
        --disable KPROBES \
        --disable KUNIT \
        --disable KVM \
        --disable KVM_GUEST \
        --disable HYPERVISOR_GUEST \
        --disable PARAVIRT \
        --disable NET_9P \
        --disable NETFILTER \
        --disable VIRTIO_PCI \
        --disable VIRTIO_BLK \
        --disable SCSI_VIRTIO \
        --disable VIRTIO_NET \
        --disable VIRTIO_CONSOLE \
        --disable VIRTIO_BALLOON \
        --disable VIRTIO_INPUT \
        --disable VIRTIO_MMIO \
        --disable VIRTIO_MMIO_CMDLINE_DEVICES \
        --disable DRM_VIRTIO_GPU \
        --disable DRM_QXL \
        --disable DRM_BOCHS \
        --disable NET_9P_VIRTIO \
        --disable PM_DEBUG \
        --disable CPU_FREQ_DEFAULT_GOV_USERSPACE \
        --enable HZ_250
    ARCH=x86 ./scripts/kconfig/merge_config.sh -m .config "$ROOT/kernel/znlite.fragment"
    ./scripts/config --set-str LOCALVERSION ""
    make ARCH=x86 olddefconfig
)
KERNEL_RELEASE=$(make -s -C "$KERNEL_SOURCE" ARCH=x86 LOCALVERSION=-znlite kernelrelease)
if [ "$KERNEL_RELEASE" != "$KERNEL_VERSION-znlite" ]; then
    printf 'Unexpected kernel release string: %s\n' "$KERNEL_RELEASE" >&2
    exit 1
fi
find "$SOURCE_PARENT" -maxdepth 1 -type f -name 'linux-image-*.deb' -delete
make -C "$KERNEL_SOURCE" -j"$JOBS" ARCH=x86 LOCALVERSION=-znlite KDEB_PKGVERSION="$KERNEL_VERSION-1" bindeb-pkg
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
    sha256sum znlite-live-x86_64.iso znlite-kernel-6.12.111-amd64.deb > SHA256SUMS
)
printf '%s\n' 'Znlite live ISO and custom kernel package built successfully.'
printf 'ISO: %s\n' "$OUTPUT_DIR/znlite-live-x86_64.iso"
printf 'Kernel package: %s\n' "$OUTPUT_DIR/znlite-kernel-6.12.111-amd64.deb"
printf 'Kernel source: %s\n' "$KERNEL_SOURCE"
