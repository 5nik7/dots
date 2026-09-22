typeset -gU fpath
local directory="$XDG_CACHE_HOME/dots/zsh/${DOTS_PLATFORM:-linux}-$ZSH_VERSION"
mkdir -p -- "$directory"
: ${ZSH_COMPDUMP:="$directory/zcompdump"}
autoload -Uz compinit
zmodload zsh/complist
# compdump emits unquoted autoload names. A provider such as Termux's _uu-[
# therefore breaks the next shell, even though the first compinit succeeds.
# Limit noglob to those declarations; compinit itself still needs globbing.
_dots_literal_completion_dump() {
  local dump=$ZSH_COMPDUMP contents literal temporary
  [[ -f $dump ]] || return 0
  contents=$(<"$dump")
  literal=${contents//$'\nautoload -Uz '/$'\nnoglob autoload -Uz '}
  [[ $literal == "$contents" ]] && return 0
  temporary="$dump.literal.$$"
  if (umask 077; print -r -- "$literal" >| "$temporary") &&
      command mv -f -- "$temporary" "$dump"; then
    command rm -f -- "$dump.zwc"
  else
    command rm -f -- "$temporary"
    return 1
  fi
}
_dots_compinit() {
  # Repair existing dumps before loading them. With read-only cache storage,
  # rebuild in memory instead of sourcing a dump that could abort autoloading.
  if ! _dots_literal_completion_dump; then
    compinit -D
    return $?
  fi
  compinit -d "$ZSH_COMPDUMP" || return
  _dots_literal_completion_dump
}
if [[ -z ${_DOTS_COMPINIT_READY:-} ]]; then
  _dots_compinit && _DOTS_COMPINIT_READY=1
fi
# The old first compinit retained these system registrations even after local
# files without #compdef headers or narrower plugin headers took precedence.
# Keep those working associations explicitly with the single-pass catalog.
_dots_completion_compat() {
  autoload -Uz _figlet _npm
  compdef _figlet figlet
  compdef _npm npm
  [[ -n ${_comps[nano]:-} ]] && compdef "${_comps[nano]}" rnano
  if [[ -n ${_comps[adb]:-} ]]; then
    compdef "${_comps[adb]}" '-value-,ADB_TRACE,-default-' \
      '-value-,ANDROID_SERIAL,-default-' '-value-,ANDROID_LOG_TAGS,-default-'
  fi
  if [[ ${DOTS_PLATFORM:-} == termux ]] && (( ${+functions[_pkgtool]} )); then
    compdef _pkgtool makepkg
  fi
}
_dots_completion_compat
(( ${_comp_options[(Ie)globdots]} )) || _comp_options+=(globdots)
# ipinfo and optional NVM use Bash-compatible completion.
autoload -Uz bashcompinit
(( ${+functions[complete]} )) || bashcompinit

reload-completion() {
  local comp
  for comp in "$@"; do
    unfunction "_$comp" 2>/dev/null
    autoload -Uz "_$comp"
  done
}
alias rlc=reload-completion
reload-completions() {
  rm -f -- "$ZSH_COMPDUMP" "$ZSH_COMPDUMP.zwc"
  local name directory="$XDG_CACHE_HOME/dots/zsh/${DOTS_PLATFORM:-linux}-$ZSH_VERSION"
  for name in uv uvx starship; do rm -f -- "$directory/$name.zsh"; done
  autoload -Uz compinit
  _dots_compinit || return
  _dots_completion_compat
  _dots_tool_completions
  # compinit redefines completion widgets; explicitly reconnect fzf-tab.
  (( ${+functions[enable-fzf-tab]} )) && enable-fzf-tab
  return 0
}
alias rlcs=reload-completions
