#!/bin/sh
set -eu
ROOT=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
if [ "$#" -ne 2 ]; then
    printf 'Usage: %s KERNEL_SOURCE REPORT_DIRECTORY\n' "$0" >&2
    exit 2
fi
SOURCE=$(CDPATH='' cd -- "$1" && pwd)
mkdir -p "$2"
REPORT=$(CDPATH='' cd -- "$2" && pwd)
make -C "$SOURCE" ARCH=x86 x86_64_defconfig
(
    cd "$SOURCE"
    ARCH=x86 ./scripts/kconfig/merge_config.sh -m .config \
        "$ROOT/kernel/trim.fragment" "$ROOT/kernel/znlite.fragment" "$ROOT/kernel/features.fragment" "$ROOT/kernel/platform.fragment"
    make ARCH=x86 olddefconfig
)
# Validate the RESOLVED configuration. Merely finding a symbol in a fragment
# does not prove Kconfig accepted it or its dependencies were satisfied.
cp "$SOURCE/.config" "$REPORT/kernel.config"
python3 "$ROOT/scripts/audit-kernel.py" --source "$SOURCE" --config "$SOURCE/.config" \
    --report "$REPORT/kernel-audit.json"
printf '%s\n' 'Resolved kernel configuration matches the Znlite policy.'
