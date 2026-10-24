# Shared Bash/Zsh startup hook. Detach keeps the outer shell as an escape hatch.
# shellcheck shell=bash
if [[ $- != *i* || ${DOTS_PLATFORM:-} != termux || -n ${TMUX:-} ||
      -z ${TERMUX_APP__PID:-} ||
      -n ${SSH_CONNECTION:-}${SSH_CLIENT:-}${SSH_TTY:-} ||
      ${DOTS_TERMUX_AUTOSTART:-${dots_options[DOTS_TERMUX_AUTOSTART]:-1}} == 0 || -n ${_DOTS_TERMUX_AUTOSTART_ATTEMPTED:-} ||
      ! -t 0 || ! -t 1 ]]; then
  return 0
fi
# Shell-local: reloads must not reattach after the user deliberately detaches.
_DOTS_TERMUX_AUTOSTART_ATTEMPTED=1
if [[ ! -r $DOTS/profiles/termux/bin/termux-bar ]]; then
  printf 'termux-bar: launcher unavailable; continuing in the plain shell\n' >&2
elif ! command -v python3 >/dev/null 2>&1; then
  printf 'termux-bar: python3 not found; continuing in the plain shell\n' >&2
else
  if command python3 -B "$DOTS/profiles/termux/bin/termux-bar" --auto; then
    :
  else
    # Only the launcher's confirmed normal session exit closes this outer shell.
    case $? in 20) exit 0 ;; esac
  fi
fi
true
