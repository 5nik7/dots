# shellcheck disable=SC1090,SC1091,SC2153
# Interactive entry point: portable settings, native hooks, optional tools.
[[ $- == *i* ]] || return 0
source "$DOTS/shells/shared/platform.sh"
source "$DOTS/shells/shared/environment.sh"
source "$DOTS/shells/shared/app-env.sh"
source "$DOTS/shells/shared/paths.sh"
source "$DOTS/shells/shared/functions.sh"
source "$DOTS/shells/bash/core/options.bash"
source "$DOTS/shells/shared/fzf.sh"
source "$DOTS/lib/dots/themes/shell.bash"
if [[ -r $DOTS/bin/dots-theme-init ]]; then set_theme 2>/dev/null
else source "$DOTS/lib/dots/themes/gum-env.bash"; fi
# Register before tool hooks so they can compose with the existing prompt.
declare -gA _DOTS_BASH_TOOL_READY
source "$DOTS/shells/bash/core/prompt.bash"
source "$DOTS/shells/bash/integrations/tools.bash"
source "$DOTS/shells/bash/core/completion.bash"
source "$DOTS/shells/shared/aliases.sh"
[[ ! -r $HOME/.bash_aliases || $HOME/.bash_aliases -ef $DOTS/shells/bash/aliases.bash ]] || source "$HOME/.bash_aliases"
source "$DOTS/shells/bash/integrations/fzf.bash"
true
