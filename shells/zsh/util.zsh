function zieces() {
  local dir file
  if [[ -f "$ZSHDOTS/$1.zsh" ]]; then
    source "$ZSHDOTS/$1.zsh"
  fi
}

function extpath() {
	if [[ -d "$1" ]]; then
    if ! echo "$PATH" | tr ":" "\n" | grep -qx "$1"; then
      export PATH="$PATH:$1"
    fi
  fi 2> /dev/null
}

function prepath() {
	if [[ -d "$1" ]]; then
    if ! echo "$PATH" | tr ":" "\n" | grep -qx "$1"; then
		  export PATH="$1:$PATH"
	  fi
  fi 2> /dev/null
}

function err() {
  local erricon=""
  printf "${BOLD}${BRIGHTRED}${erricon} %s${RST}\n" "$*" | box -hp 1 -bc "${DIM}${RED}" }

function ok() { printf "${BRIGHTGREEN}%s${RST}\n" "$*" | box -hp 1 -bc "${DIM}${GREEN}" }

function warn() { printf "${BRIGHTYELLOW}%s${RST}\n" "$*" | box -hp 1 -bc "${DIM}${YELLOW}" }

function has() {
  local verbose=0
  if [[ $1 == '-v' ]]; then
    verbose=1
    shift
  fi
  for c; do
    c="${c%% *}"
    if ! command -v "$c" &>/dev/null; then
      ((verbose)) && err "$c not found"
      return 1
    fi
  done
}

if has eza; then
  function fileicon() {
    eza --icons=always --treat-dirs-as-files $@ | awk '{print $1}'
  }
else
  function fileicon() {}
fi

function pathout() {
	local p
  local raw=0
  if [[ $1 == '-r' ]]; then
    raw=1
    shift
  fi
  for p in "$@"; do
    if (( raw )); then
      printf '%s\n' "$p"
    else
		case "$p" in
			"$HOME")
				printf '~\n'
				;;
			"$HOME"/*)
				printf '~/%s\n' "${p#"$HOME"/}"
				;;
			*)
				printf '%s\n' "$p"
				;;
		esac
    fi
  done
}

function so() {
  local file
  local verbose=0
  if [[ $1 == '-v' ]]; then
    verbose=1
    shift
  fi
  for file in "$@"; do
    local out=$(pathout $file)
    if [ -f "$file" ]; then
      local icon=$(fileicon $file)
      source "$file"
      ((verbose)) && ok "$icon $out: sourced"
    else
      ((verbose)) && err "$out: not found"
    fi
  done
}

function checkdir() {
  local dir
  local verbose=0
  local first=0
  if [[ $1 == '-v' ]]; then
    verbose=1
    shift
  fi
  if [[ $1 == '-1' ]]; then
    first=1
    shift
  fi
for dir in "$@"; do
  local out=$(pathout $dir)
    if [ -d "$dir" ]; then
      local icon=$(fileicon $dir)
      ((verbose)) && ok "$icon $out: found"
      ((first)) && return 0
    else
      ((verbose)) && err "$dir: not found"
    fi
  done
  return 1
}

function addir() {
  local dir
  local verbose=0
  if [[ $1 == '-v' ]]; then
    verbose=1
    shift
  fi
  for dir in "$@"; do
    local out=$(pathout $dir)
    if [ ! -e "$dir" ]; then
      mkdir -p "$dir" &>/dev/null
      local icon=$(fileicon $dir)
      ((verbose)) && ok "$icon $out: created"
    else
      local icon=$(fileicon $dir)
      ((verbose)) && warn "$out: already exists"
    fi
  done
}

function has() {
  local verbose=0
  if [[ $1 == '-v' ]]; then
    verbose=1
    shift
  fi
  for c; do
    c="${c%% *}"
    if ! command -v "$c" &>/dev/null; then
      ((verbose)) && err "$c not found"
      return 1
    fi
  done
}

function cmd_exists() {
 local verbose=0
  if [[ $1 == '-v' ]]; then
    verbose=1
    shift
  fi
  for c; do
    c="${c%% *}"
    if ! command -v "$c" &>/dev/null; then
      ((verbose)) && err "$c not found"
      return 1
    fi
  done
}

function is_installed() {
  dpkg -s "$1" &>/dev/null
  return $?
}



function upper() { echo "${@}" | awk '{print toupper($0)}'; }
lower() { echo "${@}" | awk '{print tolower($0)}'; }

function timestamp(){
    printf "%s" "$(date '+%F %T')  $*"
    [ $# -gt 0 ] && printf '\n'
}

function timestampcmd(){
    local output
    output="$("$@" 2>&1)"
    timestamp "$output"
}

# vim: set noet ft=zsh tw=4 sw=4 ff=unix
