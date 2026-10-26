# shellcheck disable=SC1090,SC1091,SC2153
# Interactive entry point: portable settings, native hooks, optional tools.
[[ $- == *i* ]] || return 0
source "$DOTS/shells/shared/session.sh"
source "$DOTS/shells/shared/functions.sh"
source "$DOTS/shells/bash/core/options.bash"
source "$DOTS/shells/shared/fzf.sh"
source "$DOTS/lib/dots/shell/init.bash"
# Register before tool hooks so they can compose with the existing prompt.
declare -gA _DOTS_BASH_TOOL_READY
source "$DOTS/shells/bash/core/prompt.bash"
_dots_hook_snapshot
source "$DOTS/shells/bash/integrations/tools.bash"
_dots_hook_record tools
source "$DOTS/shells/bash/core/completion.bash"
source "$DOTS/shells/shared/aliases.sh"
[[ ! -r $HOME/.bash_aliases || $HOME/.bash_aliases -ef $DOTS/shells/bash/aliases.bash ]] || _dots_hook_source "$HOME/.bash_aliases" private-aliases 1
source "$DOTS/shells/bash/integrations/fzf.bash"
source "$DOTS/shells/shared/tmux-workspaces.sh"
source "$DOTS/shells/shared/termux-tmux.sh"
true
