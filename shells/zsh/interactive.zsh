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
source "$ZSH/functions.zsh"
source "$ZSH/options.zsh"
source "$ZSH/fzf.zsh"
source "$DOTS/lib/dots/shell/init.zsh"
source "$ZSH/completions.zsh"
source "$ZSH/integrations/plugins.zsh"
_dots_completion_plugins
source "$ZSH/core/completion.zsh"
_dots_shell_prompt
source "$ZSH/integrations/tools.zsh"
source "$DOTS/shells/shared/aliases.sh"
[[ -r "${zsh[local]}" ]] && source "${zsh[local]}"
source "$ZSH/integrations/fzf.zsh"
_dots_widget_plugins

[[ -n ${ZSH_DEBUGRC+1} ]] && zprof
source "$DOTS/shells/shared/termux-tmux.sh"
# Do not propagate an optional tool's absence as the startup status.
true
