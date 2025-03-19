function rl() {
  current_shell="$(basename "$SHELL")"
  if [ "$current_shell" = "zsh" ]; then
    src ~/.zshrc
    print_in_yellow "\n ZShell reloaded.\n"
  elif [ "$current_shell" = "bash" ]; then
    src ~/.bashrc
    print_in_yellow "\n Bash reloaded.\n"
  else
    print_in_red "\n Shell not supported.\n"
  fi
}
# alias rl='rlp'

function src() {
  if [ -f "$1" ]; then
    # shellcheck disable=SC1090
    source "$1"
  fi
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

function cmd_exists() {
  command -v "$1" &>/dev/null
}

function addir() {
  if [ ! -d "$1" ]; then
    mkdir -p "$1"
  fi
}

function is_installed() {
  dpkg -s "$1" &>/dev/null
  return $?
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
  print_in_red "\n [✖] $1\n"
}

function print_success() {
  print_in_green "\n [] $1\n"
}

function print_warning() {
  print_in_yellow "\n [!] $1\n"
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

function ask() {
  while true; do
    read -rp "$1 [Y/n]: " yn
    case $yn in
    [Yy]*) break ;;
    [Nn]*) exit ;;
    *) break ;;
    esac
  done
}

function backup() {
  time_stamp=$(date +"%m-%d-%Y.%H%M")
  relfile=$(rel_path "$1")
  if [ -f "$1" ]; then
    mv -f "$1" "${1}.${time_stamp}.bak"
    print_success "${relfile} backed up @ ${relfile}.${time_stamp}.bak."
  fi
}

function symlink() {
  base="$(realpath "$1")"
  target="$(realpath "$2")"
  target_dir="$(realpath --logical "$(dirname "$2")")"
  if [ -e "$base" ]; then
    if [ ! -e "$2" ]; then
      addir "$target_dir"
      ln -s "$base" "$target"
      print_link "$base" "$target"
    else
      backup "$target"
      ln -s "$base" "$target"
      print_link "$base" "$target"
    fi
  else
    echo "$(rel_path "$base") does not exist."
  fi
}

# settitle ()
# {
#   echo -ne "\e]2;$@\a\e]1;$@\a";
# }
