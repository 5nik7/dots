# shellcheck disable=SC1090,SC1091,SC2153
# Portable interactive environment. Private compatibility modules stay native.
export UTIL="$DOTS/bin/lib/common.sh"
[[ -n ${_dots_login_common:-} && $_dots_login_common -ef $UTIL ]] || source "$UTIL"
# Application defaults are resolved by the startup registry before this file.

# User tool paths; never put completion directories in executable PATH.
[[ ! -r $XDG_DATA_HOME/bob/env/env.sh ]] || _dots_hook_source "$XDG_DATA_HOME/bob/env/env.sh" bob
true
