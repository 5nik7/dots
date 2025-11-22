#!/usr/bin/env zsh

declare -r esc=$'\033'
declare -r c_reset="${esc}[0m"
declare -r bold="${esc}[1m"
declare -r dim="${esc}[2m"
declare -r italic="${esc}[3m"
declare -r underline="${esc}[4m"
declare -r rev="${esc}[7m"
declare -r fg_black="${esc}[1;30m"
declare -r fg_red="${esc}[1;31m"
declare -r fg_green="${esc}[1;32m"
declare -r fg_yellow="${esc}[1;33m"
declare -r fg_darkblue="${esc}[0;34m"
declare -r fg_blue="${esc}[1;34m"
declare -r fg_magenta="${esc}[1;35m"
declare -r fg_cyan="${esc}[1;36m"
declare -r fg_white="${esc}[1;37m"
declare -r trashico=""
declare -r arrowico_l="<-"
declare -r arrowico_r="->"
declare -r arrowcolor="${fg_black}"
declare -r errico=""
declare -t errcolor="${fg_red}"
declare -r warnico=""
declare -t warncolor="${fg_yellow}"
declare -r trashcolor="${fg_green}"
declare -r dircolor="${fg_darkblue}"
declare -r debugico=""
declare -r debugcolor="${fg_cyan}"

BOLD="$(tput bold 2>/dev/null || printf '')"
UNDERLINE="$(tput smul 2>/dev/null || printf '')"
ITALIC="$(tput sitm 2>/dev/null || printf '')"
DIM="$(tput dim 2>/dev/null || printf '')"
INVERT="$(tput rev 2>/dev/null || printf '')"
BLINK="$(tput blink 2>/dev/null || printf '')"
INVIS="$(tput invis 2>/dev/null || printf '')"
GREY="$(tput setaf 7 2>/dev/null || printf '')"
BLACK="$(tput setaf 8 2>/dev/null || printf '')"
RED="$(tput setaf 1 2>/dev/null || printf '')"
GREEN="$(tput setaf 2 2>/dev/null || printf '')"
YELLOW="$(tput setaf 3 2>/dev/null || printf '')"
BLUE="$(tput setaf 4 2>/dev/null || printf '')"
DARKBLUE="$(tput setaf 12 2>/dev/null || printf '')"
MAGENTA="$(tput setaf 5 2>/dev/null || printf '')"
CYAN="$(tput setaf 6 2>/dev/null || printf '')"
NO_COLOR="$(tput sgr0 2>/dev/null || printf '')"

output() {
  printf ' %s\n' "$*"
}

debug() {
  if [[ "$buggin" -eq 1 ]]; then
    printf ' %s\n' "${debugcolor}${debugico}${c_reset} $*"
  fi
}

error() {
  printf ' %s\n' "${errcolor}${errico} $*${NO_COLOR}" >&2
}

warn() {
  printf ' %s\n' "${warncolor}${warnico} $*${NO_COLOR}"
}

info() {
  printf ' %s\n' "${GREY}${DIM}$*${NO_COLOR}"
}

disc() {
  printf ' %s\n' "${GREEN}$*${NO_COLOR}"
}

logo() {
  echo "${MAGENTA}$*${NO_COLOR}"
}

flag() {
  printf "  %-28s %s\n" "${BOLD}${CYAN}$1${NO_COLOR}" " ${GREEN}$2${NO_COLOR}"
}

usage() {
  while [ "$#" -gt 0 ]; do
    case "$1" in
    header)
      local header="
 █▀▀▀▄ ▄▀▀▀▄ █  ▄▀
 █▀▀▀▄ █▀▀▀█ █▀▀▄
 ▀▀▀▀  ▀   ▀ ▀   ▀"
      logo "${header}"
      disc "Utility for backing up your files"
      info "usage:${NO_COLOR} ${MAGENTA}${BOLD}bak${NO_COLOR} ${CYAN}[options]${NO_COLOR} ${BLUE}<file|dir>${NO_COLOR} ${BLUE}${DIM}[more files/dirs...]${NO_COLOR}"
      echo
      break
      ;;
    esac
  done
  info "Options:"
  flag "-h, --help" "Displays help"
  flag "-s, --store" "Place backups into ~/.bakstore"
  flag "-y, --yes" "Auto yes to prompts"
  flag "-q, --quiet" "Suppress output"
  flag "-v, --verbose" "All the output"
  echo
}

setopts() {
  _FZF_OPTS_="$fopts"
  _FZF_COLORS_="$fcolors"
  _FZF_PREVIEW_POS_="$fpos"
  __PREVIEW_="$fpreview"
  export _FZF_OPTS_ _FZF_COLORS_ _FZF_PREVIEW_POS_ __PREVIEW_

  export FZF_DEFAULT_OPTS="$_FZF_OPTS_"
  export FZF_DEFAULT_OPTS="$FZF_DEFAULT_OPTS \
$_FZF_COLORS_"
  export FZF_DEFAULT_OPTS="$FZF_DEFAULT_OPTS \
--preview-window='$_FZF_PREVIEW_POS_'"
  export FZF_DEFAULT_OPTS="$FZF_DEFAULT_OPTS \
--preview '$_PREVIEW_ {}'"
  debug "setopts: FZF_DEFAULT_OPTS=${FZF_DEFAULT_OPTS}"
}

fzfset() {
  local FZF_DEFAULT_OPTS fopts fpreview fpos fcolors
  fopts="$(echo "${_FZF_OPTS_}")"
  debug "fopts: ${fopts}"
  fpos="$(echo "${_FZF_PREVIEW_POS_}")"
  debug "fpos: ${fpos}"
  fcolors="$(echo "${_FZF_COLORS_}")"
  debug "fcolors: ${fcolors}"
  if [ -n "$BASH_VERSION" ]; then
    fpreview='fzf-preview.sh'
  elif [ -n "$ZSH_VERSION" ]; then
    fpreview='preview.zsh'
  else
    echo "Not bash or zsh"
    exit 1
  fi

  [ "$#" -gt 0 ] || {
    setopts
    debug "default: FZF_DEFAULT_OPTS=${FZF_DEFAULT_OPTS}"
    return
  }

  export FZF_DEFAULT_OPTS=''

  debug "FZF_DEFAULT_OPTS=${FZF_DEFAULT_OPTS}"

  while [ "$#" -gt 0 ]; do
    case "$1" in
    -h | --help)
      usage header
      return
      ;;
    opts)
      fopts="$2"
      debug "opts"
      shift 1
      ;;
    colors)
      fcolors="$2"
      debug "colors"
      shift 1
      ;;
    pos)
      fpos="$2"
      debug "pos"
      shift 1
      ;;
    *) break ;;
    esac
  done

  setopts
  debug "FZF_DEFAULT_OPTS=${FZF_DEFAULT_OPTS}"
}
