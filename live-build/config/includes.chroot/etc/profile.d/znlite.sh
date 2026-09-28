# shellcheck shell=sh
# This file is sourced by both /etc/profile and /etc/bash.bashrc.
# Silent for noninteractive shells, SSH commands, file transfers, and dumb terms.
case $- in
    *i*) ;;
    *) return 0 ;;
esac
[ -n "${BASH_VERSION:-}" ] || return 0
[ -t 1 ] || return 0
[ "${TERM:-dumb}" != dumb ] || return 0
[ "${ZNLITE_THEME:-1}" != 0 ] || return 0
if [ -z "${NO_COLOR+x}" ]; then
    PS1='\[\e[1;36m\]\u@\h\[\e[0;90m\] / \[\e[0;37m\]\w\n\[\e[1;36m\]zn \$\[\e[0m\] '
else
    PS1='\u@\h / \w\nzn \$ '
fi
# One greeting per login tree, never one per nested shell. No forced animation.
if [ -z "${ZNLITE_GREETED:-}" ] && [ "${ZNLITE_WELCOME:-1}" != 0 ]; then
    ZNLITE_GREETED=1
    export ZNLITE_GREETED
    if command -v znfetch >/dev/null 2>&1; then
        znfetch || :
    fi
fi
