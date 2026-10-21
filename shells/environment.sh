# Compatibility entry point for library-owned Dots paths and settings.
source "$DOTS/lib/dots/shell/config.bash"
_dots_config_load || return
source "$DOTS/lib/dots/shell/environment.bash"
source "$DOTS/shells/shared/starship-default.sh"
