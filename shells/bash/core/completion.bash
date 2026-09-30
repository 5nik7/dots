# shellcheck disable=SC1090,SC1091,SC2153
# Native completion only; never source Zsh completion functions in Bash.
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
_dots_bash_tool_completion() {
  local name=$1
  case $name in
    dots) source "$DOTS/lib/dots/completion/bash" ;;
    anodize) source "$DOTS/lib/dots/anodize/completion/bash" ;;
    uv) _dots_bash_generated uv generate-shell-completion bash && eval "$REPLY" ;;
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
declare -gA _DOTS_BASH_COMPLETION_READY
_dots_bash_tool_completions() {
  local name
  _dots_bash_completion_base || return
  for name in dots anodize uv uvx starship pip ipinfo; do
    [[ -z ${_DOTS_BASH_COMPLETION_READY[$name]:-} ]] || continue
    if [[ $name == dots || $name == anodize ]] || has "$name"; then
      if _dots_bash_tool_completion "$name"; then _DOTS_BASH_COMPLETION_READY[$name]=1; fi
    fi
  done
  return 0
}
_dots_bash_reload_completions() {
  _DOTS_BASH_COMPLETION_READY=()
  _dots_bash_tool_completions
}
_dots_bash_tool_completions
