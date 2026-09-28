#!/bin/sh
set -eu
ROOT=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
ISO=${1:-$ROOT/build/output/znlite-live-x86_64.iso}
LOG=${2:-$ROOT/build/output/qemu-boot.log}
STDERR_LOG=${LOG%.log}-stderr.log
# Software emulation on shared CI runners can take longer than 90 seconds.
QEMU_TIMEOUT=${QEMU_TIMEOUT:-300}
case "$QEMU_TIMEOUT" in
    ''|*[!0-9]*|0)
        printf '%s\n' 'QEMU_TIMEOUT must be a positive number of seconds.' >&2
        exit 1
        ;;
esac
if [ "$QEMU_TIMEOUT" -eq 0 ]; then
    printf '%s\n' 'QEMU_TIMEOUT must be a positive number of seconds.' >&2
    exit 1
fi
for command in qemu-system-x86_64 timeout; do
    if ! command -v "$command" >/dev/null 2>&1; then
        printf 'Missing build dependency: %s\n' "$command" >&2
        exit 1
    fi
done
if [ ! -f "$ISO" ]; then
    printf 'Missing ISO image: %s\n' "$ISO" >&2
    exit 1
fi
mkdir -p "$(dirname -- "$LOG")"
# Truncate old logs so an earlier successful boot cannot mask a failure.
: > "$LOG"
: > "$STDERR_LOG"
set +e
timeout --kill-after=10s "${QEMU_TIMEOUT}s" qemu-system-x86_64 \
    -accel tcg -m 2048 -smp 2 -cdrom "$ISO" -boot d \
    -display none -monitor none -audiodev none,id=audio0 \
    -serial "file:$LOG" </dev/null >"$STDERR_LOG" 2>&1
QEMU_STATUS=$?
set -e
if [ "$QEMU_STATUS" -ne 0 ] && [ "$QEMU_STATUS" -ne 124 ]; then
    cat "$LOG" "$STDERR_LOG" >&2
    exit "$QEMU_STATUS"
fi
# An issue banner alone is not proof that a login prompt was reached.
if ! grep -Eq '(^|[[:space:]])[[:alnum:]_.-]+ login:' "$LOG"; then
    cat "$LOG" "$STDERR_LOG" >&2
    printf '%s\n' 'The live system did not reach a text login prompt in QEMU.' >&2
    exit 1
fi
printf 'QEMU reached the Znlite text login prompt. Log: %s\n' "$LOG"
