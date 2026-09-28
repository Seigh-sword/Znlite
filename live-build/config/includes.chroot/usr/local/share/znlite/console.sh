# shellcheck shell=sh
# Functions separated from the launcher for hardware-free regression tests.
znlite_console_mode() {
    mode=$(cat /etc/znlite/console-mode 2>/dev/null || printf raster)
    case " $(cat /proc/cmdline) " in
        *' znlite.console=raster '*) mode=raster ;;
    esac
    printf '%s\n' "$mode"
}
znlite_has_video() {
    for device in /dev/dri/card* /dev/fb0; do
        if [ -c "$device" ]; then return 0; fi
    done
    return 1
}
znlite_start_vector() {
    # Same authenticated agetty/login flow as upstream kmsconvt@.service.
    kmscon --vt=tty1 --no-switchvt --login -- \
        /sbin/agetty -8 -o '-p -- \u' --noclear -- - xterm-256color
}
znlite_start_raster() {
    exec /sbin/agetty -8 -o '-p -- \u' --noclear tty1 linux
}
znlite_console() {
    # Own tty1 only. No DRM/framebuffer (including serial CI) means raster.
    if [ "$(znlite_console_mode)" = vector ] &&
        command -v kmscon >/dev/null 2>&1 && znlite_has_video; then
        znlite_start_vector || true
        printf '%s\n' 'Znlite: vector console exited; returning to raster login.' >&2
    fi
    znlite_start_raster
}
