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
_dots_startup_entered=0
_dots_startup_prepared=0
for _dots_startup_attempt in cached retry prepare prepare-again; do
  if [[ $_dots_startup_attempt == prepare ]]; then
    _dots_debug_event cache miss cache
    _dots_debug_event begin preparation phase
  fi
  if [[ $_dots_startup_attempt == prepare* ]]; then
    _dots_prepare_args=(--observed "$_dots_startup_generation")
    if [[ ${_DOTS_STARTUP_MODE:-integration} == early && $- != *i* ]]; then _dots_prepare_args+=(--early); fi
    if command -v python3 >/dev/null 2>&1 &&
        DOTS_BUILD_SHELL_VERSION=${ZSH_VERSION:-${BASH_VERSION:-}} command python3 -B "$DOTS/lib/dots/startup.py" --shell "$_dots_startup_shell" --cache "$_dots_startup_cache" "${_dots_prepare_args[@]}"; then
      _dots_startup_prepared=1
    else
      _dots_debug_event end preparation phase 1
      break
    fi
  fi
  [[ -f $_dots_startup_cache/current && ! -L $_dots_startup_cache/current ]] || continue
  _dots_startup_last=$_dots_startup_generation
  IFS= read -r _dots_startup_generation < "$_dots_startup_cache/current" || continue
  [[ $_dots_startup_attempt != retry || $_dots_startup_generation != "$_dots_startup_last" ]] || continue
  [[ ${#_dots_startup_generation} == 24 && $_dots_startup_generation != *[!0123456789abcdef]* ]] || continue
  _dots_startup_file=$_dots_startup_cache/$_dots_startup_generation/bundle
  [[ -f $_dots_startup_file && ! -L $_dots_startup_file ]] || continue
  IFS= read -r _dots_header < "$_dots_startup_file" || continue
  [[ $_dots_header == '# dots startup bundle 2' ]] || continue
  # The shell holds the open bundle through its guard and entire body. Only
  # retry a retired candidate before the first integration side effect.
  if source "$_dots_startup_file"; then _dots_startup_status=0; else _dots_startup_status=$?; fi
  if (( _dots_startup_entered )); then
    (( _dots_startup_status == 0 )) || return "$_dots_startup_status"
    break
  fi
done
if (( _dots_startup_prepared )); then _dots_debug_event end preparation phase "$((1 - _dots_startup_entered))"; fi
if (( _dots_startup_entered )); then
  if (( _dots_startup_prepared )); then _dots_debug_event cache prepared cache
  else _dots_debug_event cache hit cache; fi
else
  _dots_debug_event cache fallback cache
  if [[ ${_DOTS_STARTUP_MODE:-integration} == early ]]; then
    source "$DOTS/shells/environment.sh" || return
  elif [[ ${_dots_profile_environment_ready:-0} == 1 ]]; then
    printf 'dots: startup preparation failed; previous profile environment retained\n' >&2
    return 1
  else
    printf 'dots: startup preparation unavailable; loading minimal integration\n' >&2
    source "$DOTS/lib/dots/shell/environment_runtime.bash"
    source "$DOTS/lib/dots/shell/integration.bash" || return
  fi
fi
# Interactive hooks may replace PATH or MANPATH. The initial environment
# already reconciled both when they were left alone.
if [[ ${_DOTS_STARTUP_MODE:-integration} != early && $- == *i* ]]; then
  if [[ ${_dots_startup_path-} != "$PATH" || ${_dots_startup_roots-} != "$DOTBIN:$DOTSCRIPTS:$THEMESBIN:${dots_options[DOTS_INIT_COMMANDS]}" ||
        ( -d $DOTSCRIPTS && :$PATH: != *":$DOTSCRIPTS:"* ) || ( -d $DOTBIN && :$PATH: != *":$DOTBIN:"* ) ]]; then
    _dots_shell_paths
  else
    _dots_manual_path
  fi
fi
unset _dots_startup_path _dots_startup_roots
unset _dots_prepare_args
_dots_debug_event end startup phase 0
unset _dots_editor _dots_candidate _dots_profile_path _dots_mise_shims _DOTS_INHERITED_PROFILE_PATHS _DOTS_PREVIOUS_CHECKOUT
unset _dots_startup_prepared _dots_startup_shell _dots_startup_cache _dots_startup_generation _dots_startup_entered _dots_startup_attempt _dots_startup_last _dots_startup_file _dots_startup_status _dots_header _dots_bundle_inputs
# Attachment blocks until detach/exit. Finish startup before handing over the
# terminal, including when preparation fell back to minimal integration.
if [[ ${_DOTS_STARTUP_MODE:-integration} == full ]]; then
  source "$DOTS/shells/shared/termux-tmux.sh"
fi
true
