ORANGE="\033[38;5;216m"
PURPLE="\033[38;5;140m"
GRAY="\033[0;30m"
WHITE="\033[0;37m"
RED="\033[0;31m"
GREEN="\033[0;32m"
BLUE="\033[0;34m"
YELLOW="\033[0;33m"
CYAN="\033[0;36m"
PURPLE="\033[0;35m"
BRIGHTGRAY="\033[1;30m"
BRIGHTWHITE="\033[1;37m"
BRIGHTRED="\033[1;31m"
BRIGHTBLUE="\033[1;34m"
BRIGHTGREEN="\033[1;32m"
BRIGHTYELLOW="\033[1;33m"
BRIGHTCYAN="\033[1;36m"
BRIGHTPURPLE="\033[1;35m"

NC="\033[0m"

function rel_path() {
  echo "$(realpath --no-symlinks $1)" | sed "s|^$HOME/|~/|"
}

function fold1() {
  echo -e "$(basename "$1")"
}

function fold2() {
  echo -e "$(basename "$(dirname "$1")")/$(basename "$1")"
}

function fold3() {
  echo -e "$(basename "$(dirname "$(dirname "$1")")")/$(basename "$(dirname "$1")")/$(basename "$1")"
}

function extend_path() {
  [[ -d "$1" ]] || return

  if ! echo "$PATH" | tr ":" "\n" | grep -qx "$1"; then
    export PATH="$PATH:$1"
  fi
}

function prepend_path() {
  [[ -d "$1" ]] || return

  if ! echo "$PATH" | tr ":" "\n" | grep -qx "$1"; then
    export PATH="$1:$PATH"
  fi
}

function zource() {
  if [ -f "$1" ]; then
    source "$1"
  fi
}

function is_droid() {
	[[ -d  "$HOME/.termux" ]] &> /dev/null
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

function linebreak() {
  echo -e ""
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

function success() {
  print_in_green "\n Done.\n"
}

function print_link() {
  local rel1
  rel1=$(rel_path "$1")
  local rel2
  rel2=$(rel_path "$2")
  print_in_green "\n [] "
  print_in_blue "$rel1"
  print_in_black " -> "
  print_in_cyan "$rel2\n"
}

function ask(){
  while true; do
    read -rp "$1 [Y/n]: " yn
    case $yn in
      [Yy]* ) break;;
      [Nn]* ) exit;;
      * ) break;;
    esac
  done
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

# ============================================================================ #

function bak(){
    # TODO: switch this to a .backupstore folder for keeping this stuff instead
    # cp -av -- "$filename" "$backupdir/$bakfile"
    for filename in "$@"; do
        [ -n "$filename" ] || { echo "usage: bak filename"; return 1; }
        [ -f "$filename" ] || { echo "file '$filename' does not exist"; return 1; }
        [[ $filename =~ .*\.bak\..* ]] && continue
        local bakdir
        # bakdir="$HOME/.backups"
        local bakfile
        # bakfile="$bakdir/$filename.bak.$(date '+%F_%T' | sed 's/:/-/g')"
        bakfile="$filename.bak.$(date '+%F_%T' | sed 's/:/-/g')"
        until ! [ -f "$bakfile" ]; do
            echo "WARNING: bakfile '$bakfile' already exists, retrying with a new timestamp"
            sleep 1
            bakfile="$filename.bak.$(date '+%F_%T' | sed 's/:/-/g')"
        done
        mv -v  "$filename" "$bakfile"
    done
}

function unbak(){
    # restores the most recent backup of a file
    for filename in "$@"; do
        #[ -n "$filename" -o "${filename: -4}" != ".bak" ] || { echo "usage: unbak filename.bak"; return 1; }
        [ -n "$filename" ] || { echo "usage: unbak filename"; return 1; }
        #[ -f "$filename" ] || { echo "file '$filename' does not exist"; return 1; }
        local bakfile
        local dirname
        dirname="$(dirname "$filename")"
        filename="${filename##*/}"
        # don't use -t switch, we want the newest by name, not one that got touched recently
        bakfile="$(find "$dirname" -path "*/$filename.bak.*" -o -path "*/$filename.*.bak" 2>/dev/null | sort | tail -n 1)"
        echo "restoring $bakfile"
        cp -av -- "$bakfile" "$dirname/$filename"
    done
}

function backup() {
  if [ -f "$1" ]; then
    time_stamp="$(date +"%m-%d-%Y.%H%M")"
    relfile="$(rel_path "$1")"
    if [ -e "$backups" ]; then
      addir "$backups"
      backupfile="${backups}/${1}.${time_stamp}.bak"
    else
      backupfile="${1}.${time_stamp}.bak"
    fi
    mv -f "$1" "${backupfile}"
    print_success "${relfile} backed up @ ${backupfile}"
  fi
}

function symlink() {
  local base_file
  base_file="$(realpath "$1")"
  local target_file
  target_file="$(realpath "$2")"
  local target_dir
  target_dir="$(realpath --logical "$(dirname "$2")")"
  if [ -f "$base_file" ]; then
    if [ -f "$target_file" ]; then
      # addir "$target_dir"
      bak "$target_file"
      ln -s "$base_file" "$target_file"
      print_link "$base_file" "$target_file"
    else
      ln -s "$base_file" "$target_file"
      print_link "$base_file" "$target_file"
    fi
  else
    echo "$(rel_path "$base_file") does not exist."
  fi
}
