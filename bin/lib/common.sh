#!/usr/bin/env bash
# Sourceable Bash/Zsh helpers. Loading defines functions without starting tools.
# Zsh parameter flags are evaluated only in the Zsh branches.
# shellcheck disable=SC2296
if [[ -n ${ZSH_VERSION:-} ]]; then
  _DOTS_COMMON_UI=${(%):-%x}
else
  _DOTS_COMMON_UI=${BASH_SOURCE[0]}
fi
[[ $_DOTS_COMMON_UI == /* ]] || _DOTS_COMMON_UI=$PWD/$_DOTS_COMMON_UI
_DOTS_COMMON_UI=${_DOTS_COMMON_UI%/*}/../../lib/dots/ui.bash

chcmd() {
  (($#)) || return 2
  "$@"
}

extpath() {
  [[ $# == 1 && -n $1 ]] || return 2
  [[ -d $1 ]] || return 1
  case :${PATH:-}: in *:"$1":*) return 0 ;; esac
  export PATH="${PATH:+$PATH:}$1"
}
prepath() {
  [[ $# == 1 && -n $1 ]] || return 2
  [[ -d $1 ]] || return 1
  case :${PATH:-}: in *:"$1":*) return 0 ;; esac
  export PATH="$1${PATH:+:$PATH}"
}

_dots_common_message() {
  local _util_level=$1 _util_text _util_mark
  shift
  if ! typeset -f "dots::$_util_level" >/dev/null 2>&1 && [[ -r $_DOTS_COMMON_UI ]]; then
    # shellcheck source=lib/dots/ui.bash
    source "$_DOTS_COMMON_UI"
  fi
  for _util_text in "$@"; do
    # Keep caller-supplied terminal controls inert in human messages.
    if [[ $_util_text == *[[:cntrl:]]* ]]; then printf -v _util_text '%q' "$_util_text"; fi
    _util_text=${_util_text//|/ | }
    if typeset -f "dots::$_util_level" >/dev/null 2>&1; then
      "dots::$_util_level" "$_util_text"
    else
      case $_util_level in success) _util_mark='[+]' ;; warning) _util_mark='[!]' ;; info) _util_mark='[i]' ;; *) _util_mark='[x]' ;; esac
      if [[ $_util_level == success || $_util_level == info ]]; then printf '%s %s\n' "$_util_mark" "$_util_text"
      else printf '%s %s\n' "$_util_mark" "$_util_text" >&2; fi
    fi
  done
}
err() { _dots_common_message error "$@"; }
ok() { _dots_common_message success "$@"; }
warn() { _dots_common_message warning "$@"; }

has() {
  local _util_verbose=0 _util_command
  if [[ ${1:-} == -v ]]; then _util_verbose=1; shift; fi
  (($#)) || return 1
  for _util_command in "$@"; do
    _util_command=${_util_command%% *}
    if [[ ! $_util_command ]] || ! command -v "$_util_command" >/dev/null 2>&1; then
      (( ! _util_verbose )) || err "$_util_command not found"
      return 1
    fi
  done
  return 0
}

fileicon() {
  (($#)) || return 2
  local _util_output='' _util_line
  if command -v eza >/dev/null 2>&1; then
    _util_output=$(command eza --treat-dirs-as-files --oneline --icons=always --color=always -- "$@" 2>/dev/null) || _util_output=''
  fi
  while IFS= read -r _util_line; do printf '%s\n' "${_util_line%% *}"; done <<< "$_util_output"
}

# Internal formatters assign the caller's local REPLY, avoiding command substitution.
_dots_common_basename() {
  local _util_value=$1
  while [[ $_util_value == */ && $_util_value != / ]]; do _util_value=${_util_value%/}; done
  if [[ $_util_value == / ]]; then REPLY=/; else REPLY=${_util_value##*/}; fi
}
_dots_common_dirname() {
  local _util_value=$1
  while [[ $_util_value == */ && $_util_value != / ]]; do _util_value=${_util_value%/}; done
  if [[ $_util_value != */* ]]; then REPLY=.; return; fi
  _util_value=${_util_value%/*}
  while [[ $_util_value == */ && $_util_value != / ]]; do _util_value=${_util_value%/}; done
  REPLY=${_util_value:-/}
}
_dots_common_abbreviate() {
  REPLY=$1
  if [[ -n ${HOME:-} ]]; then
    # shellcheck disable=SC2088
    case $REPLY in "$HOME") REPLY='~' ;; "$HOME"/*) REPLY="~/${REPLY#"$HOME"/}" ;; esac
  fi
}

filename() {
  (($#)) || return 2
  local _util_file _util_output _util_eza=0 REPLY
  command -v eza >/dev/null 2>&1 && _util_eza=1
  for _util_file in "$@"; do
    _util_output=$_util_file
    if ((_util_eza)); then
      _util_output=$(command eza --treat-dirs-as-files --oneline --icons=never --color=always -- "$_util_file" 2>/dev/null) || _util_output=$_util_file
    fi
    _dots_common_basename "$_util_output"
    printf '%s\n' "$REPLY"
  done
}

pathout() {
  local _util_file _util_raw=0 REPLY
  if [[ ${1:-} == -r || ${1:-} == --raw ]]; then _util_raw=1; shift; fi
  [[ ${1:-} != -- ]] || shift
  for _util_file in "$@"; do
    REPLY=$_util_file
    (( _util_raw )) || _dots_common_abbreviate "$_util_file"
    printf '%s\n' "$REPLY"
  done
}

dirout() {
  local _util_file _util_slash='' _util_color='' _util_reset='' _util_raw=0 _util_styled=0 REPLY
  while (($#)); do
    case $1 in
      -r|--raw) _util_raw=1 ;;
      -j|--join) _util_slash=/ ;;
      -c|--color) _util_styled=1 ;;
      --) shift; break ;;
      *) break ;;
    esac
    shift
  done
  if (( _util_styled )); then
    setup_colors
    _util_color=$DOTS_UI_BLUE _util_reset=$DOTS_UI_RESET
  fi
  (($#)) || set -- "$PWD"
  for _util_file in "$@"; do
    _dots_common_dirname "$_util_file"
    (( _util_raw )) || _dots_common_abbreviate "$REPLY"
    printf '%s%s%s%s\n' "$_util_color" "$REPLY" "$_util_slash" "$_util_reset"
  done
}

shell() { printf '%s\n' "${SHELL##*/}"; }

_dots_common_report() {
  local _util_level=$1 _util_action=$2 REPLY
  _dots_common_abbreviate "$3"
  _dots_common_message "$_util_level" "$_util_action|$REPLY"
}

_dots_common_files() {
  local _util_mode=$1 _util_verbose=0 _util_first=0 _util_found=0 _util_failure=0
  local _util_file _util_candidate _util_shell _util_rc
  shift
  [[ ${buggin:-0} == 0 || -z ${buggin:-} ]] || _util_verbose=1
  while (($#)); do
    case $1 in
      -v|--verbose|--verboss) _util_verbose=1 ;;
      -1|--first) _util_first=1 ;;
      --) shift; break ;;
      *) break ;;
    esac
    shift
  done
  if [[ -n ${ZSH_VERSION:-} ]]; then _util_shell=zsh; else _util_shell=bash; fi
  for _util_file in "$@"; do
    _util_candidate=$_util_file
    if [[ $_util_mode == module ]]; then _util_candidate=${DOTS:-$HOME/dots}/shells/$_util_shell/$_util_file.$_util_shell; fi
    if ! case $_util_mode in
      module) [[ -f $_util_candidate && -r $_util_candidate ]] ;;
      source) [[ -f $_util_candidate && -r $_util_candidate && -s $_util_candidate ]] ;;
      directory) [[ -d $_util_candidate ]] ;;
      *) [[ -e $_util_candidate ]] ;;
    esac; then
      (( ! _util_verbose )) || _dots_common_report error 'not found' "$_util_candidate"
      continue
    fi
    _util_found=1
    if [[ $_util_mode == source || $_util_mode == module ]]; then
      # Source the checked path literally, without a PATH lookup for bare names.
      [[ $_util_candidate == /* ]] || _util_candidate=./$_util_candidate
      # shellcheck disable=SC1090
      if source "$_util_candidate"; then
        (( ! _util_verbose )) || _dots_common_report success sourced "$_util_candidate"
      else
        _util_rc=$?
        (( _util_failure )) || _util_failure=$_util_rc
        (( ! _util_verbose )) || _dots_common_report error "source failed ($_util_rc)" "$_util_candidate"
      fi
    else
      (( ! _util_verbose )) || _dots_common_report success found "$_util_candidate"
    fi
    (( ! _util_first )) || break
  done
  (( ! _util_failure )) || return "$_util_failure"
  (( _util_found ))
}
shellmod() { _dots_common_files module "$@"; }
alias zieces='shellmod'
so() { _dots_common_files source "$@"; }
check() { _dots_common_files exists "$@"; }
checkdir() { _dots_common_files directory "$@"; }

addir() {
  local _util_directory _util_verbose=0 _util_failure=0 _util_rc
  [[ ${buggin:-0} == 0 || -z ${buggin:-} ]] || _util_verbose=1
  case ${1:-} in -v|--verbose|--verboss) _util_verbose=1; shift ;; esac
  [[ ${1:-} != -- ]] || shift
  (($#)) || { err 'Usage: addir [-v] [--] DIRECTORY...'; return 2; }
  for _util_directory in "$@"; do
    if [[ -d $_util_directory ]]; then
      (( ! _util_verbose )) || _dots_common_report warning 'already exists' "$_util_directory"
    elif [[ -e $_util_directory || -L $_util_directory ]]; then
      err "Not a directory: $_util_directory"
      _util_failure=1
    elif command mkdir -p -- "$_util_directory"; then
      (( ! _util_verbose )) || _dots_common_report success created "$_util_directory"
    else
      _util_rc=$?
      (( _util_failure )) || _util_failure=$_util_rc
    fi
  done
  return "$_util_failure"
}

is_installed() {
  [[ $# == 1 && -n $1 ]] || return 2
  command -v dpkg-query >/dev/null 2>&1 || return 1
  local _util_status
  # shellcheck disable=SC2016
  _util_status=$(command dpkg-query -W -f='${db:Status-Status}' -- "$1" 2>/dev/null) || return 1
  [[ $_util_status == installed ]]
}

upper() {
  local _util_text="$*"
  if [[ -n ${ZSH_VERSION:-} ]]; then printf '%s\n' "${(U)_util_text}"
  else printf '%s\n' "${_util_text^^}"; fi
}
lower() {
  local _util_text="$*"
  if [[ -n ${ZSH_VERSION:-} ]]; then printf '%s\n' "${(L)_util_text}"
  else printf '%s\n' "${_util_text,,}"; fi
}

# Explicit global array construction; loading common does not allocate these.
# Public arrays are consumed by callers.
# shellcheck disable=SC2034
color_array() {
  typeset -gA COLOR
  COLOR=()
  local _common_index
  for ((_common_index=0; _common_index<256; _common_index++)); do
    COLOR[$_common_index]=$'\e'"[38;5;${_common_index}mcolor $_common_index"
  done
}
# Public arrays are consumed by callers.
# shellcheck disable=SC2034
fg_array() {
  typeset -gA FG
  FG=()
  local _common_index
  for ((_common_index=0; _common_index<256; _common_index++)); do
    FG[$_common_index]=$'\e'"[38;5;${_common_index}m"
  done
}
# Public arrays are consumed by callers.
# shellcheck disable=SC2034
bg_array() {
  typeset -gA BG
  BG=()
  local _common_index
  for ((_common_index=0; _common_index<256; _common_index++)); do
    BG[$_common_index]=$'\e'"[48;5;${_common_index}m"
  done
}
build_color_arrays() { color_array; fg_array; bg_array; }

# Styling belongs to the renderer, never to readonly copies of shell colors.
setup_colors() {
  if ! typeset -f dots::style >/dev/null 2>&1 && [[ -r $_DOTS_COMMON_UI ]]; then
    # shellcheck source=lib/dots/ui.bash
    source "$_DOTS_COMMON_UI"
  fi
  if typeset -f dots::style >/dev/null 2>&1; then
    dots::style "${1:-1}"
  else
    DOTS_UI_RESET='' DOTS_UI_BOLD='' DOTS_UI_BLUE='' DOTS_UI_GREEN=''
    DOTS_UI_YELLOW='' DOTS_UI_RED='' DOTS_UI_CYAN=''
    DOTS_UI_INFO='[i]' DOTS_UI_OK='[+]' DOTS_UI_WARN='[!]' DOTS_UI_ERROR='[x]'
  fi
}
log_info() { _dots_common_message info "$@"; }
log_success() { ok "$@"; }
log_warning() { warn "$@"; }
log_error() { err "$@"; }

_dots_common_text() {
  REPLY=$1
  [[ $REPLY != *[[:cntrl:]]* ]] || printf -v REPLY '%q' "$REPLY"
}
_dots_common_format() {
  local _common_kind=$1 REPLY
  _dots_common_text "${2:-}"
  setup_colors
  case $_common_kind in
    key|cmd) printf '%s%s%s%s' "$DOTS_UI_CYAN" "$DOTS_UI_BOLD" "$REPLY" "$DOTS_UI_RESET" ;;
    value) printf '%s%s%s' "$DOTS_UI_CYAN" "$REPLY" "$DOTS_UI_RESET" ;;
    path) printf '%s%s%s' "$DOTS_UI_BLUE" "$REPLY" "$DOTS_UI_RESET" ;;
    title) printf '%s%s %s %s\n' "$DOTS_UI_BLUE" "$DOTS_UI_BOLD" "$REPLY" "$DOTS_UI_RESET" ;;
    underline)
      local _common_underline=''
      [[ ! $DOTS_UI_RESET ]] || _common_underline=$'\e[4m'
      printf '%s%s%s%s%s\n' "$DOTS_UI_BLUE" "$DOTS_UI_BOLD" "$_common_underline" "$REPLY" "$DOTS_UI_RESET" ;;
  esac
}
fmt_key() { _dots_common_format key "$@"; }
fmt_value() { _dots_common_format value "$@"; }
fmt_cmd() { _dots_common_format cmd "$@"; }
fmt_path() { _dots_common_format path "$@"; }
fmt_title() { _dots_common_format title "$@"; }
fmt_title_underline() { _dots_common_format underline "$@"; }
fmt_title_border() {
  local REPLY _common_rule _common_h='-' _common_v='|' _common_tl='+' _common_tr='+' _common_bl='+' _common_br='+'
  _dots_common_text "${1:-}"
  setup_colors
  if [[ $DOTS_UI_OK != '[+]' ]]; then
    _common_h='─' _common_v='│' _common_tl='┌' _common_tr='┐' _common_bl='└' _common_br='┘'
  fi
  printf -v _common_rule '%*s' "$((${#REPLY}+2))" ''
  _common_rule=${_common_rule// /$_common_h}
  printf '%s%s%s%s%s%s\n' "$DOTS_UI_BLUE" "$DOTS_UI_BOLD" "$_common_tl" "$_common_rule" "$_common_tr" "$DOTS_UI_RESET"
  printf '%s%s%s %s %s%s\n' "$DOTS_UI_BLUE" "$DOTS_UI_BOLD" "$_common_v" "$REPLY" "$_common_v" "$DOTS_UI_RESET"
  printf '%s%s%s%s%s%s\n' "$DOTS_UI_BLUE" "$DOTS_UI_BOLD" "$_common_bl" "$_common_rule" "$_common_br" "$DOTS_UI_RESET"
}

# Restore only the signals this invocation temporarily owns.
_dots_common_restore_traps() {
  if [[ -z ${ZSH_VERSION:-} ]]; then
    trap - INT TERM
    eval "$_common_saved_traps"
  fi
}
_dots_common_clear_spinner() {
  if (( _common_drawn )); then printf '\r%*s\r' "$_common_drawn" '' >&2; fi
}

# A brace body keeps an asynchronous caller's $! attached to the actual worker.
# Foreground calls restore caller traps before returning; the cursor stays visible.
spinner() {
  [[ $# -ge 1 && $1 =~ ^[0-9]+$ ]] || return 2
  local _common_pid=$1 _common_style=${2:-1} REPLY _common_chars _common_index=0 _common_drawn=0
  local _common_width=${COLUMNS:-80} _common_line
  (( _common_pid > 0 )) || return 2
  [[ ${DOTS_PROGRESS:-auto} == auto && -t 1 && -t 2 && ${TERM:-dumb} != dumb ]] || return 0
  command -v sleep >/dev/null 2>&1 || return 0
  setup_colors 2
  _dots_common_text "${3:-Working...}"
  case $_common_style in
    1) _common_chars='⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏' ;;
    2) _common_chars='▁▂▃▄▅▆▇█▇▆▅▄▃▂' ;;
    3) _common_chars='←↖↑↗→↘↓↙' ;;
    4) _common_chars='▉▊▋▌▍▎▏▎▍▌▋▊▉' ;;
    5) _common_chars='▖▘▝▗' ;;
    6) _common_chars='┤┘┴└├┌┬┐' ;;
    7) _common_chars='◢◣◤◥' ;;
    8) _common_chars='◰◳◲◱' ;;
    9) _common_chars='◴◷◶◵' ;;
    10) _common_chars='◐◓◑◒' ;;
    11) _common_chars='⣾⣽⣻⢿⡿⣟⣯⣷' ;;
    12) _common_chars='•●○' ;;
    13) _common_chars='✶✸✹✺✹✸' ;;
    14) _common_chars='⠁⠂⠄⡀⢀⠠⠐⠈' ;;
    15) _common_chars='≈≋≋≈≈≋≋≈' ;;
    16) _common_chars='⌜⌝⌟⌞' ;;
    17) _common_chars='◜◝◞◟' ;;
    18) _common_chars='⬖⬘⬗⬙' ;;
    19) _common_chars='⏳⌛' ;;
    *) _common_chars='/-\|' ;;
  esac
  [[ $DOTS_UI_OK != '[+]' ]] || _common_chars='/-\|'
  [[ $_common_width =~ ^[0-9]{1,4}$ ]] || _common_width=80
  _common_width=$((10#$_common_width))
  (( _common_width > 1 )) || _common_width=80
  local _common_saved_traps _common_signal_status=0
  if [[ -n ${ZSH_VERSION:-} ]]; then
    setopt localoptions localtraps
  else
    _common_saved_traps=$(trap -p INT TERM)
  fi
  trap '_common_signal_status=130' INT
  trap '_common_signal_status=143' TERM
  command sleep 0.5 || :
  while (( ! _common_signal_status )) && kill -0 "$_common_pid" 2>/dev/null; do
    _common_line="${_common_chars:_common_index:1} $REPLY"
    _common_line=${_common_line:0:_common_width-1}
    printf '\r%s%s%s' "$DOTS_UI_CYAN" "$_common_line" "$DOTS_UI_RESET" >&2
    _common_drawn=${#_common_line}
    _common_index=$(((_common_index+1)%${#_common_chars}))
    command sleep 0.1 || break
  done
  _dots_common_clear_spinner
  _dots_common_restore_traps
  return "$_common_signal_status"
}

_dots_common_stop_children() {
  if [[ $_common_spinner_pid ]]; then
    kill "$_common_spinner_pid" 2>/dev/null || :
    wait "$_common_spinner_pid" 2>/dev/null || :
    _common_spinner_pid=''
  fi
  if [[ $_common_command_pid ]]; then
    kill "$_common_command_pid" 2>/dev/null || :
    wait "$_common_command_pid" 2>/dev/null || :
    _common_command_pid=''
  fi
}

# The legacy command-string interface evaluates trusted shell code once.
run_with_spinner() {
  (($#)) || return 2
  local _common_cmd=$1 _common_style=${2:-0} _common_message=${3:-Working...} _common_show=${4:-0}
  local _common_command_pid='' _common_spinner_pid='' _common_rc=0 _common_saved_traps _common_signal_status=0
  if [[ -n ${ZSH_VERSION:-} ]]; then
    setopt localoptions localtraps
  else
    _common_saved_traps=$(trap -p INT TERM)
  fi
  trap '_common_signal_status=130; _dots_common_stop_children' INT
  trap '_common_signal_status=143; _dots_common_stop_children' TERM
  (eval "$_common_cmd") &
  _common_command_pid=$!
  spinner "$_common_command_pid" "$_common_style" "$_common_message" &
  _common_spinner_pid=$!
  wait "$_common_command_pid" || _common_rc=$?
  _common_command_pid=''
  _dots_common_stop_children
  _dots_common_restore_traps
  (( ! _common_signal_status )) || return "$_common_signal_status"
  if [[ $_common_show == 1 ]]; then
    if (( _common_rc == 0 )); then log_success 'Success!'; else log_error 'Failed!'; fi
  fi
  return "$_common_rc"
}
