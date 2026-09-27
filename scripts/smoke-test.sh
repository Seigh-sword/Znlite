#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
ISO=${1:-$ROOT/build/output/znlite-live-x86_64.iso}
LOG=${2:-$ROOT/build/output/qemu-boot.log}
MONITOR_LOG=${LOG%.log}-monitor.log
SCREEN=${LOG%.log}-screen.ppm
MONITOR_DELAY=${QEMU_SMOKE_DELAY:-30}
if ! command -v qemu-system-x86_64 >/dev/null 2>&1; then
    printf '%s\n' 'Missing build dependency: qemu-system-x86_64' >&2
    exit 1
fi
if [ ! -f "$ISO" ]; then
    printf 'Missing ISO image: %s\n' "$ISO" >&2
    exit 1
fi
set +e
{
    sleep "$MONITOR_DELAY"
    printf 'info block\nscreendump %s\n' "$SCREEN"
    sleep 1
    printf 'quit\n'
} | timeout 90s qemu-system-x86_64 -m 2048 -smp 2 -cdrom "$ISO" -boot d -display vnc=127.0.0.1:99 -monitor stdio -serial "file:$LOG" >"$MONITOR_LOG" 2>&1
QEMU_STATUS=$?
set -e
if [ "$QEMU_STATUS" -ne 0 ] && [ "$QEMU_STATUS" -ne 124 ]; then
    cat "$LOG" "$MONITOR_LOG" >&2
    exit "$QEMU_STATUS"
fi
if ! grep -Eiq 'Znlite Linux text-only live system|login:' "$LOG"; then
    cat "$LOG" "$MONITOR_LOG" >&2
    printf '%s\n' 'The live system did not reach a text login prompt in QEMU.' >&2
    exit 1
fi
printf 'QEMU reached the Znlite text login prompt. Log: %s\n' "$LOG"
