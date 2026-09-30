# Translate the FZF template as literal data, never shell code.
# Literal shell expressions below are generated code or exact input grammar.
# shellcheck disable=SC2016
dt_fzf_colors() {
  local dir=$1 line text colors='' file
  REPLY=''
  local fzf_assignment='^export _FZF_COLORS_="([^"]+)"$'
  local fzf_atom='(#[a-fA-F0-9]{6}|-1|[0-9]{1,2}|1[0-9]{2}|2[0-4][0-9]|25[0-5]|regular|bold|dim|italic|underline|blink|reverse|strikethrough|strip|nobold|nodim|noitalic|nounderline|noblink|noreverse|nostrikethrough)'
  local fzf_entry="[a-z][a-z+-]*:$fzf_atom(:$fzf_atom)*"
  local fzf_colors="^$fzf_entry(,$fzf_entry)*$"
  file=$dir/fzf.sh
  if [[ -f $file ]]; then
    text=$(<"$file")
    text=${text//$'\\\n'/}
    while IFS= read -r line || [[ $line ]]; do
      [[ $line =~ ^[[:space:]]*(#.*)?$ ]] && continue
      if [[ $line =~ $fzf_assignment && ! $colors ]]; then
        colors=${BASH_REMATCH[1]}
        [[ $colors =~ $fzf_colors ]] || { dt_error 'invalid literal FZF color list'; return 1; }
      elif [[ $line != 'export FZF_DEFAULT_OPTS="${FZF_DEFAULT_OPTS} --color=$_FZF_COLORS_"' ]]; then
        dt_error 'fzf.sh must contain only literal FZF color assignments'; return 1
      fi
    done <<< "$text"
    [[ $colors ]] || { dt_error 'fzf.sh is missing _FZF_COLORS_'; return 1; }
  fi
  REPLY=$colors
}
dt_app_init() {
  local dir=$1 colors
  dt_fzf_colors "$dir" || return
  colors=$REPLY
  # All validation finishes before adding code to the generated initialization.
  {
    printf 'export DOTS_THEME_FZF_COLORS=%q\n' "$colors"
    if [[ $colors ]]; then
      printf '%s\n' 'if [[ -z ${_DOTS_THEME_FZF_BASE+x} ]]; then _DOTS_THEME_FZF_BASE=${FZF_DEFAULT_OPTS:-}; fi'
      printf '%s\n' 'export _FZF_COLORS_=$DOTS_THEME_FZF_COLORS' 'export FZF_DEFAULT_OPTS="$_DOTS_THEME_FZF_BASE --color=$_FZF_COLORS_"'
    else
      printf '%s\n' 'if [[ -n ${_DOTS_THEME_FZF_BASE+x} ]]; then export FZF_DEFAULT_OPTS=$_DOTS_THEME_FZF_BASE; unset _FZF_COLORS_; fi'
    fi
  } >> "$dir/init.zsh" || return
  {
    printf "set -gx DOTS_THEME_FZF_COLORS '%s'\n" "$colors"
    if [[ $colors ]]; then
      printf '%s\n' 'if not set -q _DOTS_THEME_FZF_BASE' ' set -g _DOTS_THEME_FZF_BASE "$FZF_DEFAULT_OPTS"' 'end' 'set -gx _FZF_COLORS_ "$DOTS_THEME_FZF_COLORS"' 'set -gx FZF_DEFAULT_OPTS "$_DOTS_THEME_FZF_BASE --color=$_FZF_COLORS_"'
    else
      printf '%s\n' 'if set -q _DOTS_THEME_FZF_BASE' ' set -gx FZF_DEFAULT_OPTS "$_DOTS_THEME_FZF_BASE"' ' set -e _FZF_COLORS_' 'end'
    fi
  } >> "$dir/init.fish"
}
