# Interactive entry point: explicit order, immediate readiness, one compinit.
[[ -n ${ZSH_DEBUGRC+1} ]] && zmodload zsh/zprof
export ZSH="$DOTS/shells/zsh"
[[ -n ${DOTS_PLATFORM:-} ]] || source "$ZSH/platforms/detect.zsh"
source "$ZSH/core/environment.zsh"
source "$ZSH/core/cache.zsh"
autoload -Uz colors
colors
export CLICOLOR=1

# Compatibility modules remain sourceable at their original locations.
source "$DOTS/shells/shared/functions.sh"
source "$ZSH/options.zsh"
source "$DOTS/shells/shared/fzf.sh"
source "$DOTS/lib/dots/shell/init.zsh"
source "$ZSH/completions.zsh"
source "$ZSH/integrations/plugins.zsh"
_dots_completion_plugins
source "$ZSH/core/completion.zsh"
_dots_shell_prompt
_dots_hook_snapshot
source "$ZSH/integrations/tools.zsh"
_dots_hook_record tools
source "$DOTS/shells/shared/aliases.sh"
[[ -r "${zsh[local]}" ]] && _dots_hook_source "${zsh[local]}" private-local 1
source "$ZSH/integrations/fzf.zsh"
_dots_widget_plugins

[[ -n ${ZSH_DEBUGRC+1} ]] && zprof
source "$DOTS/shells/shared/termux-tmux.sh"
# Do not propagate an optional tool's absence as the startup status.
true
