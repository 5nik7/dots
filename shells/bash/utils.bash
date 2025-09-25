function is_droid() {
  [[ -d "$HOME/.termux" ]] &>/dev/null
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
  echo
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
  print_in_green "\n [] "
  print_in_blue "$1"
  print_in_black " -> "
  print_in_cyan "$2\n"
}

function timestamp() {
  printf "%s" "$(date '+%F %T')  $*"
  [ $# -gt 0 ] && printf '\n'
}
alias tstamp=timestamp

function timestampcmd() {
  local output
  output="$("$@" 2>&1)"
  timestamp "$output"
}
alias tstampcmd=timestampcmd

function bakfile() {
  # TODO: switch this to a .backupstore folder for keeping this stuff instead
  # cp -av -- "$filename" "$backupdir/$bakfile"
  for filename in "$@"; do
    [ -n "$filename" ] || {
      echo "usage: bak filename"
      return 1
    }
    [ -f "$filename" ] || {
      echo "file '$filename' does not exist"
      return 1
    }
    [[ $filename =~ .*\.bak\..* ]] && continue
    local bakfile
    bakfile="$filename.bak.$(date '+%F_%T' | sed 's/:/-/g')"
    until ! [ -f "$bakfile" ]; do
      echo "WARNING: bakfile '$bakfile' already exists, retrying with a new timestamp"
      sleep 1
      bakfile="$filename.bak.$(date '+%F_%T' | sed 's/:/-/g')"
    done
    cp -v "$filename" "$bakfile"
  done
}

function bak() {
  local usage="usage: bak [options] <file|dir> [more files/dirs...]
Create timestamped backups of files or directories.
Skips inputs that already contain '.bak.' in their name.

Options:
  -h, --help     Show this help message and exit
  -s, --store    Place backups into ~/.bakstore; prompt to create it if missing
      --yes      With --store, auto-create ~/.bakstore without prompting
"

  # No args?
  [ "$#" -gt 0 ] || {
    echo "$usage"
    return 1
  }

  # Flags
  local store_mode=0 auto_yes=0
  local args=()

  # Parse flags
  while [ "$#" -gt 0 ]; do
    case "$1" in
    -h | --help)
      echo "$usage"
      return 0
      ;;
    -s | --store) store_mode=1 ;;
    --yes) auto_yes=1 ;;
    --)
      shift
      args+=("$@")
      break
      ;;
    -*)
      echo "error: unknown option '$1'" >&2
      echo "$usage"
      return 1
      ;;
    *) args+=("$1") ;;
    esac
    shift
  done

  # Need at least one path to back up
  [ "${#args[@]}" -gt 0 ] || {
    echo "$usage"
    return 1
  }

  # Portable yes/no prompt function (works in bash/zsh/dash; handles no TTY)
  _bak_confirm() {
    # $1: prompt
    local reply
    if [ "$auto_yes" -eq 1 ]; then
      return 0
    fi
    if [ -t 0 ]; then
      printf "%s" "$1"
      IFS= read -r reply
    elif [ -r /dev/tty ]; then
      printf "%s" "$1" >/dev/tty
      IFS= read -r reply </dev/tty
    else
      echo "error: cannot prompt (no TTY). Use --yes to auto-create." >&2
      return 2
    fi
    case "$reply" in
    [Yy] | [Yy][Ee][Ss]) return 0 ;;
    *) return 1 ;;
    esac
  }

  # If --store, ensure ~/.bakstore exists (prompt if missing)
  local store_dir
  if [ "$store_mode" -eq 1 ]; then
    store_dir="$HOME/.bakstore"
    if [ ! -d "$store_dir" ]; then
      if _bak_confirm "~/.bakstore does not exist. Create it now? [y/N]: "; then
        if ! mkdir -p -- "$store_dir"; then
          echo "error: failed to create '$store_dir'" >&2
          return 1
        fi
      else
        echo "error: store directory not created; aborting." >&2
        return 1
      fi
    fi
  fi

  # Backup loop
  for src in "${args[@]}"; do
    if [ ! -e "$src" ]; then
      echo "error: '$src' does not exist" >&2
      continue
    fi

    # Skip if already a .bak.
    case "$src" in
    *.bak.*) continue ;;
    esac

    local ts bakname bakpath
    ts="$(date '+%F_%T' | sed 's/:/-/g')" # e.g., 2025-09-25_14-03-07
    bakname="$(basename "$src").bak.${ts}"
    if [ "$store_mode" -eq 1 ]; then
      bakpath="$store_dir/$bakname"
    else
      bakpath="${src}.bak.${ts}"
    fi

    # Avoid collisions (file or dir), retry with new timestamp
    while [ -e "$bakpath" ]; do
      echo "WARNING: '$bakpath' already exists, retrying..."
      sleep 1
      ts="$(date '+%F_%T' | sed 's/:/-/g')"
      bakname="$(basename "$src").bak.${ts}"
      if [ "$store_mode" -eq 1 ]; then
        bakpath="$store_dir/$bakname"
      else
        bakpath="${src}.bak.${ts}"
      fi
    done

    cp -av -- "$src" "$bakpath"
  done
}
