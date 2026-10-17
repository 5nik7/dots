#!/usr/bin/env bash
# Zsh-specific builtin expansions are intentionally guarded at runtime.
# shellcheck disable=SC2299,SC1090,SC2034,SC2154
# Sourceable Bash/Zsh theme helpers; lib/dots/shell owns prompt registration.
# Fast Zsh prompt checks use only builtins.
declare -gA theme themes dot
themes[root]=${DOTHEMES:-$DOTS/themes}
unset 'themes[default]' 'themes[global]' 'themes[local]'
_DOTS_THEME_STATE=${XDG_STATE_HOME:-$HOME/.local/state}/dots/themes
_DOTS_THEME_ACTIVE=${XDG_STATE_HOME:-$HOME/.local/state}/dots/current/theme
themes[file]=$_DOTS_THEME_ACTIVE/selection

# Existing shell helper APIs also accept a native family with its default flavor.
# Resolve only those calls through the shared Bash reader, never at shell startup.
_dots_theme_full_id() {
  REPLY=$1
  if [[ -f ${themes[root]}/$1/colors.toml || -f ${themes[root]}/$1/palette.toml ||
        -f ${XDG_CONFIG_HOME:-$HOME/.config}/dots/themes/$1/colors.toml ||
        -f ${XDG_CONFIG_HOME:-$HOME/.config}/dots/themes/$1/palette.toml ]]; then return 0; fi
  REPLY=$(command bash -c '
    DT_LIB=$1
    source "$DT_LIB/core.bash"
    source "$DT_LIB/families.bash"
    dt_family_index && dt_family_pick "$2" || exit
    printf "%s\n" "$REPLY"
  ' -- "$DOTS/lib/dots/themes" "$1")
}
has_theme() {
  { _dots_theme_full_id "$1" && "$DOTS/bin/dots-theme-show" "$REPLY"; } >/dev/null 2>&1
}
change_theme() {
  _dots_theme_full_id "$1" || return
  "$DOTS/bin/dots-theme-set" "$REPLY" || return
  set_theme
}
set_theme() {
  [[ -z ${ZSH_VERSION:-} ]] || setopt local_options nonomatch
  local requested=${1:-} generation='' output file colors vivid_theme=''
  # Follow the published artifact even when no generated shell palette exists.
  # Explicit session-only selections do not publish a matching Gum environment.
  if [[ -z $requested ]]; then
    source "$DOTS/lib/dots/themes/gum-env.bash" || return
  fi
  # Older generations and session-only palettes retain the role-based fallback.
  unset DOTS_THEME_FZF_COLORS
  if [[ -L $_DOTS_THEME_ACTIVE ]]; then
    if [[ -n ${ZSH_VERSION:-} ]]; then generation=${${_DOTS_THEME_ACTIVE:A}:t}
    else generation=$(readlink -- "$_DOTS_THEME_ACTIVE"); generation=${generation##*/}; fi
    [[ $generation == g.* && ${generation#g.} != *[^a-zA-Z0-9]* && -n ${generation#g.} ]] || return 1
  elif [[ -f $_DOTS_THEME_STATE/current && ! -L $_DOTS_THEME_STATE/current ]]; then
    IFS= read -r generation < "$_DOTS_THEME_STATE/current" || return 1
    [[ $generation == g.* && ${generation#g.} != *[^a-zA-Z0-9]* && -n ${generation#g.} ]] || return 1
  fi
  if [[ -n $generation && -z $requested ]]; then
    file=$_DOTS_THEME_STATE/generations/$generation/init.zsh
    [[ -f $file && ! -L $file ]] || return 1
    source "$file" || return
  else
    output=$(DOTS_THEME_SELECTION=$requested "$DOTS/bin/dots-theme-init" --shell zsh) || return
    [[ -n $output ]] || return 1
    eval "$output" || return
  fi
  [[ -n ${_DOTS_THEME_LS_BASE+x} ]] || _DOTS_THEME_LS_BASE=${LS_COLORS:-}
  if [[ ${dots_options[DOTS_INIT_COLORS]:-1} != 1 ]]; then
    for colors in "${_DOTS_THEME_COLOR_NAMES[@]-}"; do [[ ! $colors ]] || unset "$colors"; done
    _DOTS_THEME_COLOR_NAMES=()
  fi
  theme[current]=$THEME theme[flavor]=$FLAVOR
  dot[theme]=${DOTS_THEME_ID:-$THEME${FLAVOR:+-$FLAVOR}}
  export THEMEDIR=${themes[root]}/$THEME THEMESRC=${themes[root]}/$THEME/src
  _DOTS_THEME_GENERATION=$generation
  _DOTS_THEME_LOADED_DIR=$_DOTS_THEME_STATE/generations/$generation
  # Role-based rules also provide a fallback when Vivid is unavailable.
  export LS_COLORS="${_DOTS_THEME_LS_BASE:+$_DOTS_THEME_LS_BASE:}${DOTS_THEME_LS_COLORS:-}"
  _DOTS_THEME_FSH_FILE=''
  # Retain the expected path when absent so the FSH adapter can explain setup
  # failures. Explicit session-only palettes still use the last-good selection.
  [[ -n $requested ]] || _DOTS_THEME_FSH_FILE=$_DOTS_THEME_ACTIVE/fsh.ini
  if [[ -z $requested && -n $generation ]]; then
    [[ ! -r $_DOTS_THEME_LOADED_DIR/vivid.yml ]] || vivid_theme=$_DOTS_THEME_LOADED_DIR/vivid.yml
    [[ ! -r $_DOTS_THEME_LOADED_DIR/fsh.ini ]] || _DOTS_THEME_FSH_FILE=$_DOTS_THEME_LOADED_DIR/fsh.ini
  fi
  # Preserve the legacy selection only for old generations/session-only palettes.
  [[ -n $vivid_theme || $THEME != catppuccin ]] || vivid_theme=$THEME-$FLAVOR
  if [[ -n $vivid_theme ]]; then
    if [[ -z $requested && -r $_DOTS_THEME_LOADED_DIR/ls_colors ]]; then
      IFS= read -r LS_COLORS < "$_DOTS_THEME_LOADED_DIR/ls_colors" && export LS_COLORS
    elif [[ -n ${ZSH_VERSION:-} ]] && (( ${+functions[_dots_vivid_colors]} )); then
      _dots_vivid_colors "$vivid_theme" 2>/dev/null && export LS_COLORS=$REPLY
    elif command -v vivid >/dev/null 2>&1; then
      colors=$(command vivid generate "$vivid_theme" 2>/dev/null) && [[ -n $colors ]] && export LS_COLORS=$colors
    fi
  fi
  if [[ -n ${ZSH_VERSION:-} ]] && (( ${+functions[_dots_fsh_apply]} )); then
    _dots_fsh_apply || :
  fi
  if [[ -n ${_FZF_OPTS_:-} ]]; then
    export FZF_DEFAULT_OPTS="$_FZF_OPTS_ --bind=$_FZF_BINDS_ --preview-window=$_FZF_PREVIEW_POS_ --preview='$_PREVIEW_ {}'"
  else
    if [[ -z ${_DOTS_THEME_FZF_BASE+x} ]]; then _DOTS_THEME_FZF_BASE=${FZF_DEFAULT_OPTS:-}; fi
    export FZF_DEFAULT_OPTS=$_DOTS_THEME_FZF_BASE
  fi
  {
    export ZSH_AUTOSUGGEST_HIGHLIGHT_STYLE="fg=${dots_roles[muted]}"
    export _FZF_COLORS_="bg:-1,bg+:-1,fg:${dots_roles[foreground]},fg+:${dots_roles[foreground]},hl:${dots_roles[accent]},hl+:${dots_roles[accent]},info:${dots_roles[muted]},prompt:${dots_roles[accent]},pointer:${dots_roles[accent]},marker:${dots_roles[warning]},spinner:${dots_roles[info]},border:${dots_roles[muted]}"
    [[ ! ${DOTS_THEME_FZF_COLORS:-} ]] || export _FZF_COLORS_=$DOTS_THEME_FZF_COLORS
    export FZF_DEFAULT_OPTS="$FZF_DEFAULT_OPTS --color=$_FZF_COLORS_"
  }
  return 0
}
_dots_theme_commands() {
  local _dots_cmd_directory=$_DOTS_THEME_STATE/commands/current _dots_cmd_token='' _dots_cmd_shell=bash
  [[ -r $_dots_cmd_directory/fingerprint ]] || return 0
  IFS= read -r _dots_cmd_token < "$_dots_cmd_directory/fingerprint" || return
  [[ $_dots_cmd_token != "${_DOTS_THEME_COMMANDS_TOKEN:-}" ]] || return 0
  if [[ -n ${ZSH_VERSION:-} ]]; then
    (( ${+functions[compdef]} )) || return 0
    _dots_cmd_shell=zsh
  else typeset -f _dots_complete_bash >/dev/null || return 0; fi
  source "$_dots_cmd_directory/init.$_dots_cmd_shell" || return
  _DOTS_THEME_COMMANDS_TOKEN=$_dots_cmd_token
}
_dots_theme_precmd() {
  local previous_status=$? generation=''
  [[ ${dots_options[DOTS_INIT_COMPLETION]:-1} != 1 ]] || _dots_theme_commands
  [[ ${dots_options[DOTS_INIT_THEME]:-1} == 1 && ${dots_options[DOTS_THEME_AUTO_UPDATE]:-1} == 1 ]] || return "$previous_status"
  if [[ -L $_DOTS_THEME_ACTIVE ]]; then
    if [[ -n ${ZSH_VERSION:-} ]]; then generation=${${_DOTS_THEME_ACTIVE:A}:t}
    elif [[ -n ${_DOTS_THEME_LOADED_DIR:-} && $_DOTS_THEME_ACTIVE -ef $_DOTS_THEME_LOADED_DIR ]]; then
      return "$previous_status"
    elif [[ -n ${_DOTS_THEME_FAILED_DIR:-} && $_DOTS_THEME_ACTIVE -ef $_DOTS_THEME_FAILED_DIR ]]; then
      return "$previous_status"
    else generation=$(readlink -- "$_DOTS_THEME_ACTIVE"); generation=${generation##*/}; fi
  elif [[ -f $_DOTS_THEME_STATE/current && ! -L $_DOTS_THEME_STATE/current ]]; then
    IFS= read -r generation < "$_DOTS_THEME_STATE/current"
  fi
  if [[ -n $generation ]]; then
    if [[ $generation != "${_DOTS_THEME_GENERATION:-}" && $generation != "${_DOTS_THEME_FAILED:-}" ]]; then
      if set_theme; then _DOTS_THEME_FAILED=''; _DOTS_THEME_FAILED_DIR=''
      else
        _DOTS_THEME_FAILED=$generation
        _DOTS_THEME_FAILED_DIR=$_DOTS_THEME_STATE/generations/$generation
        printf '%s\n' 'dots theme: could not load updated theme; keeping previous colors' >&2
      fi
    fi
  fi
  return $previous_status
}
if [[ -n ${ZSH_VERSION:-} ]]; then
  # Zsh-only helper is checked with zsh -n, not Bash ShellCheck.
  # shellcheck disable=SC1091
  source "$DOTS/lib/dots/themes/fsh.zsh"
fi
