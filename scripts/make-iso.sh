#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
IMAGE_DIR=$(CDPATH= cd -- "${1:?Usage: make-iso.sh IMAGE_DIR OUTPUT_ISO}" && pwd)
OUTPUT_ISO=${2:?Usage: make-iso.sh IMAGE_DIR OUTPUT_ISO}
OUTPUT_DIR=$(dirname -- "$OUTPUT_ISO")
mkdir -p "$OUTPUT_DIR"
OUTPUT_ISO=$(CDPATH= cd -- "$OUTPUT_DIR" && pwd)/$(basename -- "$OUTPUT_ISO")
for command in grub-mkrescue xorriso; do
    if ! command -v "$command" >/dev/null 2>&1; then
        printf 'Missing host dependency: %s\n' "$command" >&2
        exit 1
    fi
done
for image in bzImage rootfs.cpio.gz; do
    if [ ! -f "$IMAGE_DIR/$image" ]; then
        printf 'Missing Buildroot image: %s\n' "$IMAGE_DIR/$image" >&2
        exit 1
    fi
done
STAGING_DIR=$(mktemp -d "${TMPDIR:-/tmp}/znlite-iso.XXXXXX")
trap 'rm -rf "$STAGING_DIR"' EXIT HUP INT TERM
mkdir -p "$STAGING_DIR/boot/grub"
cp "$IMAGE_DIR/bzImage" "$STAGING_DIR/boot/bzImage"
cp "$IMAGE_DIR/rootfs.cpio.gz" "$STAGING_DIR/boot/rootfs.cpio.gz"
cat > "$STAGING_DIR/boot/grub/grub.cfg" <<'EOF'
set default=0
set timeout=5
menuentry "Znlite Linux live system" {
    linux /boot/bzImage loglevel=3
    initrd /boot/rootfs.cpio.gz
}
EOF
grub-mkrescue --output="$OUTPUT_ISO" "$STAGING_DIR"
printf 'Created %s\n' "$OUTPUT_ISO"
