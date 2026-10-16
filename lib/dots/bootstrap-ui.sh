# POSIX bootstrap diagnostics before the Python renderer is available.
# shellcheck shell=sh
dots_bootstrap_error() {
    dots_bootstrap_color=${DOTS_COLOR:-auto}
    dots_bootstrap_icons=${DOTS_ICONS:-auto}
    dots_bootstrap_text=$1
    shift
    for dots_bootstrap_arg do
        case $dots_bootstrap_arg in
            --color=*) dots_bootstrap_color=${dots_bootstrap_arg#*=} ;;
            --icons=*) dots_bootstrap_icons=${dots_bootstrap_arg#*=} ;;
        esac
    done
    dots_bootstrap_mark='[x]'
    if [ "$dots_bootstrap_icons" = always ] || { [ "$dots_bootstrap_icons" = auto ] && [ -t 2 ] && [ "${TERM:-dumb}" != dumb ]; }; then dots_bootstrap_mark=''; fi
    if [ "$dots_bootstrap_color" = always ] || { [ "$dots_bootstrap_color" = auto ] && [ -t 2 ] && [ "${TERM:-dumb}" != dumb ] && [ -z "${NO_COLOR:-}" ]; }; then
        printf '\033[91m%s\033[0m %s\n' "$dots_bootstrap_mark" "$dots_bootstrap_text" >&2
    else printf '%s %s\n' "$dots_bootstrap_mark" "$dots_bootstrap_text" >&2; fi
}
