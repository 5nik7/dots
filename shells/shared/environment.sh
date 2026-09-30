# shellcheck disable=SC1090,SC1091,SC2153
# Portable interactive environment. Private compatibility modules stay native.
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-$HOME/.cache}"
export XDG_CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"
export XDG_DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
export XDG_STATE_HOME="${XDG_STATE_HOME:-$HOME/.local/state}"
export UTIL="$DOTS/bin/lib/common.sh"
source "$UTIL"
build_color_arrays
if has nvim; then EDITOR=nvim
elif has vim; then EDITOR=vim
elif has vi; then EDITOR='vi'
elif has code; then EDITOR=code
else EDITOR=nano
fi
export EDITOR VISUAL="$EDITOR" SYSTEMD_EDITOR="$EDITOR"
export EDITOR_TERM="${TERMINAL:-} -e $EDITOR"
