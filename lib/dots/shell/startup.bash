source "$DOTS/lib/dots/shell/debug.bash"
_dots_debug_event begin startup phase
# Shared native loader. Cache checks never invoke Python on a warm startup.
_DOTS_INHERITED_PROFILE_PATHS=${DOTS_PROFILE_PATHS:-}
_DOTS_PREVIOUS_CHECKOUT=${DOTS_PROFILE_CHECKOUT:-}
source "$DOTS/lib/dots/shell/platform.bash"
_dots_startup_shell=bash
[[ -z ${ZSH_VERSION:-} ]] || _dots_startup_shell=zsh
_dots_startup_cache=${XDG_CACHE_HOME:-$HOME/.cache}/dots/startup/$_dots_startup_shell-$DOTS_PLATFORM-$DOTS_DISTRO
_dots_startup_generation=''
if [[ -f $_dots_startup_cache/current && ! -L $_dots_startup_cache/current ]]; then
  IFS= read -r _dots_startup_generation < "$_dots_startup_cache/current"
fi
_dots_startup_valid=0
_dots_startup_prepared=0
if [[ $_dots_startup_generation =~ ^[a-f0-9]+$ && -r $_dots_startup_cache/$_dots_startup_generation/guard ]]; then
  if source "$_dots_startup_cache/$_dots_startup_generation/guard"; then _dots_startup_valid=1; fi
fi
if (( ! _dots_startup_valid )); then
  _dots_debug_event cache miss cache
  _dots_debug_event begin preparation phase
  if command -v python3 >/dev/null 2>&1 &&
      DOTS_BUILD_SHELL_VERSION=${ZSH_VERSION:-${BASH_VERSION:-}} command python3 -B "$DOTS/lib/dots/startup.py" --shell "$_dots_startup_shell" --cache "$_dots_startup_cache"; then
    _dots_startup_prepared=1
    IFS= read -r _dots_startup_generation < "$_dots_startup_cache/current"
    if [[ $_dots_startup_generation =~ ^[a-f0-9]+$ ]] && source "$_dots_startup_cache/$_dots_startup_generation/guard"; then _dots_startup_valid=1; fi
  fi
  _dots_debug_event end preparation phase "$((1 - _dots_startup_valid))"
fi
if (( _dots_startup_valid )); then
  if (( _dots_startup_prepared )); then _dots_debug_event cache prepared cache
  else _dots_debug_event cache hit cache; fi
  source "$_dots_startup_cache/$_dots_startup_generation/bundle" || return
else
  _dots_debug_event cache fallback cache
  if [[ ${_dots_profile_environment_ready:-0} == 1 ]]; then
    printf 'dots: startup preparation failed; previous profile environment retained\n' >&2
    return 1
  fi
  printf 'dots: startup preparation unavailable; loading minimal integration\n' >&2
  source "$DOTS/lib/dots/shell/environment_runtime.bash"
  source "$DOTS/lib/dots/shell/integration.bash" || return
fi
_dots_debug_event end startup phase 0
unset _dots_startup_prepared _dots_startup_shell _dots_startup_cache _dots_startup_generation _dots_startup_valid _dots_bundle_inputs
# Attachment blocks until detach/exit. Finish startup before handing over the
# terminal, including when preparation fell back to minimal integration.
if [[ ${_DOTS_STARTUP_MODE:-integration} == full ]]; then
  source "$DOTS/shells/shared/termux-tmux.sh"
fi
true
