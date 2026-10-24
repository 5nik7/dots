# Dots integration only; no personal plugins or aliases.
_DOTS_STARTUP_MODE=integration
source "$DOTS/lib/dots/shell/startup.bash" || { unset _DOTS_STARTUP_MODE; return 1; }
unset _DOTS_STARTUP_MODE
