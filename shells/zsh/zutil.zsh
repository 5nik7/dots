
function is_droid() {
  [[ -z "$TERMUX_VERSION" ]] &> /dev/null
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


