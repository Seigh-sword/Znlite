#!/bin/sh
set -eu
ROOT=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
for script in "$ROOT"/scripts/*.sh "$ROOT/live-build/auto/config"; do
    sh -n "$script"
done
for script in "$ROOT"/live-build/config/includes.chroot/usr/local/bin/*; do
    bash -n "$script"
    test -x "$script"
done
for script in "$ROOT"/live-build/config/hooks/live/*.hook.chroot \
    "$ROOT"/live-build/config/includes.chroot/usr/local/libexec/* \
    "$ROOT"/live-build/config/includes.chroot/etc/profile.d/*.sh \
    "$ROOT"/live-build/config/includes.chroot/usr/local/share/znlite/*.sh; do
    case "$script" in
        *.py) python3 -c 'import ast, sys; ast.parse(open(sys.argv[1]).read())' "$script" ;;
        *) sh -n "$script" ;;
    esac
done
# A zero/missing timeout leaves unattended BIOS boots stuck at the menu.
awk '$1 == "timeout" { timeout = $2 } END { exit !(timeout > 0 && timeout <= 100) }' \
    "$ROOT/live-build/config/bootloaders/isolinux/isolinux.cfg"
grep -Fx 'version=6.12.111' "$ROOT/kernel/source.lock" >/dev/null
grep -Fx 'commit=e2acc2211022246c77740d5df08265cc27eedcc5' "$ROOT/kernel/source.lock" >/dev/null
grep -F 'sha256=' "$ROOT/kernel/source.lock" >/dev/null
grep -F 'CONFIG_LOCALVERSION=""' "$ROOT/kernel/znlite.fragment" >/dev/null
grep -Fx 'localversion=-znlite3' "$ROOT/kernel/source.lock" >/dev/null
grep -Fx 'package_revision=3' "$ROOT/kernel/source.lock" >/dev/null
grep -F 'CONFIG_DRM_I915=y' "$ROOT/kernel/znlite.fragment" >/dev/null
grep -F 'CONFIG_ACPI_BATTERY=y' "$ROOT/kernel/znlite.fragment" >/dev/null
grep -F 'CONFIG_SQUASHFS=y' "$ROOT/kernel/znlite.fragment" >/dev/null
grep -F 'CONFIG_HZ_250=y' "$ROOT/kernel/znlite.fragment" >/dev/null
grep -Fx 'CONFIG_HYPERVISOR_GUEST=y' "$ROOT/kernel/platform.fragment" >/dev/null
grep -Fx 'CONFIG_DEBUG_INFO=n' "$ROOT/kernel/trim.fragment" >/dev/null
grep -F -- '--linux-packages none' "$ROOT/live-build/auto/config" >/dev/null
grep -F -- 'boot=live components console=tty0 console=ttyS0,115200n8' "$ROOT/live-build/auto/config" >/dev/null
grep -Fx 'vector' "$ROOT/live-build/config/includes.chroot/etc/znlite/console-mode" >/dev/null
grep -Fx 'kmscon/trixie-backports' "$ROOT/live-build/config/package-lists/znlite.list.chroot" >/dev/null
grep -Fx 'fonts-dejavu-core' "$ROOT/live-build/config/package-lists/znlite.list.chroot" >/dev/null
grep -Fx 'apt' "$ROOT/live-build/config/package-lists/znlite.list.chroot" >/dev/null
grep -Fx 'network-manager' "$ROOT/live-build/config/package-lists/znlite.list.chroot" >/dev/null
for package in sway greetd foot waybar libgl1-mesa-dri pipewire-audio python3 gpgv; do
    grep -Fx "$package" "$ROOT/live-build/config/package-lists/znlite.list.chroot" >/dev/null
done

python3 "$ROOT/scripts/audit-kernel.py" --lint
git -C "$ROOT" diff --check
printf '%s\n' 'Znlite configuration checks passed.'
