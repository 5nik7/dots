# Public app settings apply after Zsh compatibility modules, as before.
export DOCS="${DOCS:-$HOME/Documents}" NOTES="${NOTES:-$HOME/Notes}"
export DOTHEMES="${DOTHEMES:-$DOTS/themes}"
export THEMES="$DOTHEMES"
export DOTRUBY="$DOTS/ruby" RUBYCOMP="$DOTS/ruby/completion"
export THEMESBIN="${THEMESBIN:-$DOTHEMES/bin}" THEMESCMD="${THEMESCMD:-$DOTHEMES/bin/theme}"
if [[ -n ${ZSH_VERSION:-} ]]; then _dots_app_config=${dot[configs]:-$DOTFILES}
else _dots_app_config=$DOTFILES; fi
export STARSHIP_CONFIG="$_dots_app_config/starship/starship.toml"
export STARSHIP_DIR="$_dots_app_config/starship" STARSHIP_THEMES="$_dots_app_config/starship/themes"
export BAT_CONFIG_DIR="$_dots_app_config/bat" BAT_CONFIG_PATH="$_dots_app_config/bat/bat.conf"
export YAZI_CONFIG_HOME="$DOTFILES/yazi" GOBIN="${GOBIN:-$HOME/go/bin}"
unset _dots_app_config
