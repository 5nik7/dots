# Public app settings apply after Zsh compatibility modules, as before.
export DOCS="${DOCS:-$HOME/Documents}" NOTES="${NOTES:-$HOME/Notes}"
export DOTRUBY="$DOTS/ruby" RUBYCOMP="$DOTS/ruby/completion"
if [[ -n ${ZSH_VERSION:-} ]]; then _dots_app_config=${dot[configs]:-$DOTFILES}
else _dots_app_config=$DOTFILES; fi
source "$DOTS/shells/shared/starship-default.sh"
export STARSHIP_DIR="$_dots_app_config/starship" STARSHIP_THEMES="$_dots_app_config/starship/themes"
export BAT_CONFIG_DIR="$_dots_app_config/bat" BAT_CONFIG_PATH="$_dots_app_config/bat/bat.conf"
export YAZI_CONFIG_HOME="$DOTFILES/yazi" GOBIN="${GOBIN:-$HOME/go/bin}"
unset _dots_app_config
