# Derived paths and public maps are consumed by the caller.
# shellcheck disable=SC2034,SC2154
typeset -gA dot shells
dot=()
_dots_derive_paths() {
  local variable key relative value
  while IFS=$'\t' read -r variable key relative; do
    value=$DOTS
    [[ $relative == . ]] || value=$DOTS/$relative
    [[ $variable == - ]] || export "$variable=$value"
    [[ $key == - ]] || dot[$key]=$value
  done < "$DOTS/lib/dots/shell/paths.tsv"
}
_dots_derive_paths
unset -f _dots_derive_paths
export THEMESCMD="$DOTS/bin/theme"
export THEMESBIN="${XDG_STATE_HOME:-$HOME/.local/state}/dots/themes/commands/current/bin"
dot[config]=$_DOTS_CONFIG_PATH dot[state]=${XDG_STATE_HOME:-$HOME/.local/state}/dots
shells=( [root]="$SHELLS" [zsh]="$ZSH" [bash]="$SHELLS/bash" [pwsh]="$PWSH" )
_dots_shell_paths() {
  local directory part rest=${PATH:-} result='' separator=''
  # Remove only retired paths and our optional generated-command path.
  while :; do
    part=${rest%%:*}
    if [[ $part != "$DOTS/themes/bin" && $part != "$THEMESBIN" ]]; then
      result+=$separator$part; separator=:
    fi
    [[ $rest == *:* ]] || break
    rest=${rest#*:}
  done
  PATH=$result
  for directory in "$DOTBIN" "$DOTSCRIPTS"; do
    [[ -d $directory ]] || continue
    case :$PATH: in *":$directory:"*) ;; *) PATH="$directory${PATH:+:$PATH}" ;; esac
  done
  if [[ ${dots_options[DOTS_INIT_COMMANDS]} == 1 ]]; then PATH="${PATH:+$PATH:}$THEMESBIN"; fi
  export PATH
}
_dots_shell_paths
unset -f _dots_shell_paths
