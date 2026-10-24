# shellcheck disable=SC1090,SC1091,SC2153
# Portable interactive environment. Private compatibility modules stay native.
export UTIL="$DOTS/bin/lib/common.sh"
source "$UTIL"
# Application defaults are resolved by the startup registry before this file.

# User tool paths; never put completion directories in executable PATH.
[[ ! -r $XDG_DATA_HOME/bob/env/env.sh ]] || _dots_hook_source "$XDG_DATA_HOME/bob/env/env.sh" bob
prepath "$GOBIN"
prepath "$HOME/.cargo/bin"
prepath "$HOME/.local/bin"
prepath "$HOME/bin"
extpath "$HOME/.fzf/bin"
true
