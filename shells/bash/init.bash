# shellcheck shell=bash
# Resolve this sourced file before looking for any Dots helper.
_dots_bash_source_dir() {
  local file=$1 directory target hops=0
  [[ $file == /* ]] || file=$PWD/$file
  while :; do
    directory=$(CDPATH='' builtin cd -P -- "${file%/*}" && builtin pwd -P) || return 1
    file=$directory/${file##*/}
    [[ -L $file ]] || break
    (( ++hops <= 40 )) || return 1
    target=$(command readlink "$file") || return 1
    if [[ $target == /* ]]; then file=$target
    else file=$directory/$target; fi
  done
  [[ -r $file ]] || return 1
  printf '%s\n' "$directory"
}
_dots_bash_directory=$(_dots_bash_source_dir "${BASH_SOURCE[0]}") || {
  unset -f _dots_bash_source_dir
  printf 'dots: cannot resolve Bash startup file\n' >&2
  return 1
}
unset -f _dots_bash_source_dir
if [[ ! -r $_dots_bash_directory/../environment.sh || ! -r $_dots_bash_directory/../../bin/dots ]]; then
  unset _dots_bash_directory
  printf 'dots: Bash startup requires the Dots checkout layout\n' >&2
  return 1
fi
export DOTS="${_dots_bash_directory%/*/*}"
unset _dots_bash_directory
source "$DOTS/shells/environment.sh" || return
[[ $- == *i* ]] || return 0
source "$DOTS/shells/bash/interactive.bash"
