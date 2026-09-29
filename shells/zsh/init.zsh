# Resolve the source file, including file and parent-directory symlinks.
_dots_zsh_file=${${(%):-%x}:A}
if [[ ! -r $_dots_zsh_file || ! -r ${_dots_zsh_file:h}/../environment.sh || ! -r ${_dots_zsh_file:h}/../../bin/dots ]]; then
  unset _dots_zsh_file
  print -ru2 -- 'dots: Zsh startup requires a resolvable Dots checkout'
  return 1
fi
export DOTS="${_dots_zsh_file:h:h:h}"
unset _dots_zsh_file
source "$DOTS/shells/environment.sh" || return
[[ -o interactive ]] || return 0
source "$ZSH/interactive.zsh"
