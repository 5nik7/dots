# shellcheck disable=SC1090,SC1091,SC2153
# Native completion only; never source Zsh completion functions in Bash.
_dots_bash_local_completion_path() {
  [[ $- == *i* ]] || return 0
  local entry base="$DOTS/profiles/termux/shells/bash" result=''
  local user_base="${XDG_DATA_HOME:-$HOME/.local/share}/bash-completion"
  local -a entries
  IFS=: read -r -a entries <<< "${BASH_COMPLETION_USER_DIR:-$user_base}"
  [[ ! -d $user_base ]] || entries+=("$user_base")
  for entry in "${entries[@]}"; do
    [[ $entry && $entry != "$base" ]] || continue
    case :$result: in *:"$entry":*) continue ;; esac
    result+=${result:+:}$entry
  done
  if [[ ${DOTS_PLATFORM:-} == termux && -d $DOTS/profiles/termux ]]; then
    result+=${result:+:}$base
  fi
  export BASH_COMPLETION_USER_DIR=$result
}
_dots_bash_local_completion_path
_dots_bash_completion_base() {
  [[ -z ${_DOTS_BASH_COMPLETION_BASE_READY:-} ]] || return 0
  local file
  for file in "${PREFIX:-/usr}/share/bash-completion/bash_completion" /etc/bash_completion; do
    if [[ -r $file ]]; then
      source "$file" || return
      _DOTS_BASH_COMPLETION_BASE_READY=1
      break
    fi
  done
  return 0
}
# uv emits a static native completion template. A function, script shim or
# the uvx launcher can select a different tool per project; run those in-session.
_dots_bash_open_uv_template() {
  local descriptor permissions cached
  [[ -f $1 && ! -L $1 ]] || return 1
  exec {descriptor}<"$1" || return 1
  # The descriptor pins the inode while another shell replaces the cache.
  if [[ -O /dev/fd/$descriptor ]] &&
      permissions=$(command stat -Lc %a -- "/dev/fd/$descriptor" 2>/dev/null) &&
      [[ $permissions == 600 || $permissions == 400 ]] &&
      IFS= read -r cached <&"$descriptor" && [[ $cached == "$2" ]]; then
    REPLY=$descriptor
    return 0
  fi
  exec {descriptor}<&-
  return 1
}
_dots_bash_uv_template() {
  local name=$1 executable magic signature cached temporary directory target permissions
  executable=$(command -v "$name") || return 1
  [[ $executable == /* && -f $executable ]] || return 1
  IFS= read -r -N 4 magic < "$executable" && [[ $magic == $'\177ELF' ]] || return 1
  signature=$(command stat -Lc '%d:%i:%s:%y:%z' -- "$executable" 2>/dev/null) || return 1
  printf -v signature '# %q %s' "$executable" "$signature"
  directory="${XDG_CACHE_HOME:-$HOME/.cache}/dots/bash/$BASH_VERSION"
  target="$directory/$name.bash"
  [[ -d $directory ]] || (umask 077; command mkdir -p -- "$directory") 2>/dev/null || return 1
  [[ -O $directory && ! -L $directory ]] || return 1
  permissions=$(command stat -c %a -- "$directory" 2>/dev/null) || return 1
  (( (8#$permissions & 8#22) == 0 )) || return 1
  _dots_bash_open_uv_template "$target" "$signature" && return 0
  # No caller environment or project settings enter the reusable template.
  # Publish only complete, parseable output from the selected executable.
  shift
  (
    builtin cd -- "$directory" || exit 1
    temporary=$(command mktemp -- ".$name.XXXXXXXX") || exit 1
    trap '[[ ! -e $temporary ]] || command rm -f -- "$temporary"' EXIT
    { printf '%s\n' "$signature" && command env -i HOME="$PWD" "$executable" --no-config "$@" 2>/dev/null; } >| "$temporary" &&
        { IFS= read -r cached && IFS= read -r cached; } < "$temporary" &&
        command bash --noprofile --norc -n "$temporary" && command mv -f -- "$temporary" "$name.bash"
  ) 2>/dev/null || return 1
  _dots_bash_open_uv_template "$target" "$signature"
}
_dots_bash_uv_completion() {
  local REPLY descriptor result
  if _dots_bash_uv_template "$@"; then
    descriptor=$REPLY
    source "/dev/fd/$descriptor"; result=$?
    exec {descriptor}<&-
    return "$result"
  fi
  _dots_bash_generated "$@" && eval "$REPLY"
}
_dots_bash_tool_completion() {
  local name=$1
  case $name in
    dots) [[ ${dots_options[DOTS_INIT_COMPLETION]:-1} == 1 ]] || return 0; source "$DOTS/lib/dots/completion/bash" ;;
    anodize) source "$DOTS/plugins/anodize/completion/bash" ;;
    uv) _dots_bash_uv_completion uv generate-shell-completion bash ;;
    uvx) _dots_bash_generated uvx --generate-shell-completion bash && eval "$REPLY" ;;
    starship) _dots_bash_generated starship completions bash && eval "$REPLY" ;;
    pip) _dots_bash_generated pip completion --bash && eval "$REPLY" ;;
    ipinfo) complete -o default -C "$(command -v ipinfo)" ipinfo ;;
    *)
      if typeset -f _comp_load >/dev/null; then _comp_load "$name"
      elif typeset -f _completion_loader >/dev/null; then _completion_loader "$name"
      else return 1; fi ;;
  esac
}
_dots_bash_reload_completion() {
  local name result=0
  for name in "$@"; do
    if ! _dots_bash_tool_completion "$name"; then
      printf 'dots: no Bash completion available for %s\n' "$name" >&2
      result=1
    fi
  done
  return "$result"
}
# Bash retries the original completion when a function installs a replacement
# and returns 124. The first Tab therefore runs the generated provider itself.
_dots_bash_lazy_completion() {
  local name=${1##*/} specification
  _dots_bash_tool_completion "$name" || return 1
  specification=$(complete -p "$name" 2>/dev/null) || return 1
  [[ $specification != *' -F _dots_bash_lazy_completion '* ]] || return 1
  return 124
}
declare -gA _DOTS_BASH_COMPLETION_READY
_dots_bash_tool_completions() {
  local name
  _dots_bash_completion_base || return
  for name in dots anodize uv uvx starship pip ipinfo; do
    [[ -z ${_DOTS_BASH_COMPLETION_READY[$name]:-} ]] || continue
    if [[ $name == dots || $name == anodize ]] || has "$name"; then
      case $name in
        uv|uvx|starship|pip)
          complete -o default -F _dots_bash_lazy_completion "$name" || continue ;;
        *) _dots_bash_tool_completion "$name" || continue ;;
      esac
      _DOTS_BASH_COMPLETION_READY[$name]=1
    fi
  done
  return 0
}
_dots_bash_reload_completions() {
  _DOTS_BASH_COMPLETION_READY=()
  _dots_bash_tool_completions
}
_dots_bash_tool_completions
