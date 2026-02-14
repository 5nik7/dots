BOLD="$(tput bold 2>/dev/null || printf '')"
UNDERLINE="$(tput smul 2>/dev/null || printf '')"
ITALIC="$(tput sitm 2>/dev/null || printf '')"
DIM="$(tput dim 2>/dev/null || printf '')"
INVERT="$(tput rev 2>/dev/null || printf '')"
BLINK="$(tput blink 2>/dev/null || printf '')"
INVIS="$(tput invis 2>/dev/null || printf '')"
BLACK="$(tput setaf 0 2>/dev/null || printf '')"
RED="$(tput setaf 1 2>/dev/null || printf '')"
GREEN="$(tput setaf 2 2>/dev/null || printf '')"
YELLOW="$(tput setaf 3 2>/dev/null || printf '')"
BLUE="$(tput setaf 4 2>/dev/null || printf '')"
MAGENTA="$(tput setaf 5 2>/dev/null || printf '')"
CYAN="$(tput setaf 6 2>/dev/null || printf '')"
GREY="$(tput setaf 7 2>/dev/null || printf '')"
BRIGHTBLACK="$(tput setaf 8 2>/dev/null || printf '')"
BRIGHTRED="$(tput setaf 9 2>/dev/null || printf '')"
BRIGHTGREEN="$(tput setaf 10 2>/dev/null || printf '')"
BRIGHTYELLOW="$(tput setaf 11 2>/dev/null || printf '')"
BRIGHTBLUE="$(tput setaf 12 2>/dev/null || printf '')"
BRIGHTMAGENTA="$(tput setaf 13 2>/dev/null || printf '')"
BRIGHTCYAN="$(tput setaf 14 2>/dev/null || printf '')"
WHITE="$(tput setaf 15 2>/dev/null || printf '')"
RST="$(tput sgr0 2>/dev/null || printf '')"


function is_droid() {
  [[ -z "$ANDROID_DATA" ]] &> /dev/null
	return $?
}

function addir() {
  if [ ! -d "$1" ]; then
    mkdir -p "$1"
  fi
}

function cmd_exists() {
  command -v "$1" &>/dev/null
}

function is_installed() {
  dpkg -s "$1" &>/dev/null
  return $?
}

function check_dir() {
  if [ ! -d "$(dirname "$1")" ]; then
    mkdir -p "$(dirname "$1")"
  fi
}


function print_in_color() {
  printf "%b" \
    "$(tput setaf "$2" 2>/dev/null)" \
    "$1" \
    "$(tput sgr0 2>/dev/null)"
}

function print_in_green() {
  print_in_color "$1" 2
}

function print_in_purple() {
  print_in_color "$1" 5
}

function print_in_red() {
  print_in_color "$1" 1
}

function print_in_yellow() {
  print_in_color "$1" 3
}

function print_in_cyan() {
  print_in_color "$1" 6
}

function print_in_blue() {
  print_in_color "$1" 4
}

function print_in_white() {
  print_in_color "$1" 7
}

function print_in_black() {
  print_in_color "$1" 8
}

function print_error() {
  print_in_red "\n [✖] $1"
}

function print_success() {
  print_in_green "\n [] $1"
}

function print_warning() {
  print_in_yellow "\n [!] $1"
}

function print_link() {
  print_in_green "\n [] "
  print_in_blue "$1"
  print_in_black " -> "
  print_in_cyan "$2\n"
}

function timestamp(){
    printf "%s" "$(date '+%F %T')  $*"
    [ $# -gt 0 ] && printf '\n'
}
alias tstamp=timestamp

function timestampcmd(){
    local output
    output="$("$@" 2>&1)"
    timestamp "$output"
}
alias tstampcmd=timestampcmd

# vim: set noet ft=zsh tw=4 sw=4 ff=unix
