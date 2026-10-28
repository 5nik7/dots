#!/usr/bin/env bash
# blastoff-variants: narrow-terminal logo concepts.
# Unicode blocks; purple -> pink; foreground color only.
# Run with Bash. No Python, external font files, or image tools needed.

set -u

usage() {
  printf '%s\n' 'Usage: bash blastoff-variants.sh [ID] [OPTIONS]

ID: all (default), 1-5, or a name below.

  1 orbit       48 columns /  6 rows
  2 vector      48 columns /  6 rows
  3 cartridge   48 columns /  9 rows
  4 launchpad   32 columns / 13 rows
  5 prompt      37 columns /  8 rows

  --columns auto|N   Width limit; capped at 50.
  --color auto|always|never
  --no-color        Same as --color never.
  --list            Show the variant names.
  -h, --help        Show this help.

Auto width: COLUMNS, then optional tput,
then 50. Oversized art is skipped in all mode.
A single oversized selection exits with error.

Auto color requires terminal output, a TERM
other than dumb, and no nonempty NO_COLOR.
Always forces truecolor, including in files.
Only foreground colors are set and reset.

Examples:
  bash blastoff-variants.sh all
  bash blastoff-variants.sh 4
  bash blastoff-variants.sh prompt --no-color
  bash blastoff-variants.sh all --columns 40'
}

fail() {
  printf 'blastoff-variants: %s\n' "$*" >&2
  exit 2
}

valid_columns() {
  # Validate before any arithmetic. Accept 1-9999, including leading zeros.
  case "$1" in ''|*[!0-9]*) return 1 ;; esac
  (( ${#1} <= 4 )) || return 1
  (( 10#$1 > 0 ))
}

load_variant() {
  case "$1" in
    1)
      name=orbit; width=48; rows=6
      art='██     ██               ██    ▗▄███▄▖   ▄██  ▄██
██▄▄▄  ██  ▄██▄   ▄████ ████ ▗███ ▜██▖ ██▀▀ ██▀▀
██▀▀██ ██  ▀▀▀██ ██▄▄   ██   ███▌▀▐███ ████ ████
██  ██ ██ ▄█████  ▀▀▀██ ██   ███▘ ▝███ ██   ██
██▄▄██ ██ ██▄▄██ ▄▄▄▄██ ██▄▄ ▝█▌▄ ▄▐█▘ ██   ██
 ▀██▀  ▝█  ▀██▀█ ████▀   ▀██  ▝▀█▄█▀▘  ██   ██'
      ;;
    2)
      name=vector; width=48; rows=6
      art='   ████▄ █▌  ▄███▄ ▄████ █████  ▗▄███▄▖  ███ ███
   ██ ▐█ █▌  █▌ ▐█ █▙     ▐█   ▗███ ▜██▖ █▌  █▌
  ████▘ █▌  █▌ ▐█ ▀███▄  ▐█   ███▌▀▐███ ███ ███
 ██ ▐█ █▌  █████    ▐█  ▐█   ███▘ ▝███ █▌  █▌
 ██ ▐█ █▙▄ █▌ ▐█ ▄▄▄▟█  ▐█   ▝█▌▄ ▄▐█▘ █▌  █▌
████▀ ███ █▌ ▐█ ████▀  ▐█    ▝▀█▄█▀▘  █▌  █▌'
      ;;
    3)
      name=cartridge; width=48; rows=9
      art='╭──────────────────────────────────────────────╮
│ ███  █     ███   ███ █████  ▗▟███▙▖  ███ ███ │
│ █  █ █    █   █ █      █   ▐██▛▄▜██▌ █   █   │
│ ███  █    █████  ██    █   ███▌ ▐███ ███ ███ │
│ █  █ █    █   █    █   █   ▐█▛   ▜█▌ █   █   │
│ ███  ████ █   █ ███    █    ▝▜█▄█▛▘  █   █   │
│                                              │
│ STARSHIP THEME SWITCHER                      │
╰──────────────────────────────────────────────╯'
      ;;
    4)
      name=launchpad; width=32; rows=13
      art='████▄  ██     ▄██▄  ▄█████ █████
██ ▐██ ██    ██  ██ ██▄▄    ▐█
█████  ██    ██████  ▀▀██▄  ▐█
██ ▐██ ██    ██  ██ ▄▄  ██  ▐█
████▀  █████ ██  ██ █████▀  ▐█

  ▗▄█████▄▖    ▄██████  ▄██████
 ▟███▛ ▜███▙  ███▀▀▀▀▀ ███▀▀▀▀▀
▟████▘▄▝████▙ ███      ███
█████   █████ ██████   ██████
▜███▘   ▝███▛ ███      ███
 ▜█▙▄▙ ▟▄▟█▛  ███      ███
  ▝▀██▄██▀▘   ███      ███'
      ;;
    5)
      name=prompt; width=37; rows=8
      art='▌ █   █          █   ▗▄███▄▖  ▄██ ▄██
▌ █   █          █  ▗███ ▜██▖ █   █
▌ ██▄ █ ▀█▄ ▄██ ███ ███▌▀▐███ ███ ███
▌ █ █ █ ▄██ █▄▄  █  ███▘ ▝███ █   █
▌ █ █ █ █ █   █  █  ▝█▌▄ ▄▐█▘ █   █
▌ ██▀ █ ▀██ ██▀  ▀█  ▝▀█▄█▀▘  █   █

  starship / theme switcher'
      ;;
    *) return 2 ;;
  esac
}

# Byte-wise parsing does not depend on a UTF-8 locale. All embedded non-ASCII
# glyphs are three-byte Unicode blocks or box-drawing characters; each uses
# one terminal cell in ordinary monospace rendering.
render() {
  local LC_ALL=C
  local line rest glyph output column i red green blue
  local -a palette
  if (( ! use_color )); then
    printf '%s\n' "$art"
    return $?
  fi

  # The same purple-to-pink endpoints as the previous blastoff renderer.
  # A palette entry is reused for every row in that column.
  for ((i=0; i<width; i++)); do
    red=$((101 + 154 * i / (width - 1)))
    green=$((30 + 37 * i / (width - 1)))
    blue=$((255 - 64 * i / (width - 1)))
    printf -v "palette[$i]" '\033[38;2;%d;%d;%dm' "$red" "$green" "$blue"
  done

  while IFS= read -r line; do
    rest=$line; output=''; column=0
    while [[ -n $rest ]]; do
      if [[ ${rest:0:1} == $'\342' ]]; then
        glyph=${rest:0:3}; rest=${rest:3}
      else
        glyph=${rest:0:1}; rest=${rest:1}
      fi
      if [[ $glyph == ' ' ]]; then
        output+=' '
      else
        output+="${palette[$column]}$glyph"
      fi
      column=$((column+1))
    done
    # SGR 39 restores the default foreground; background is untouched.
    printf '%s\033[39m\n' "$output" || return $?
  done <<< "$art"
}

main() {
  local selection=all selected=0 color=auto requested_columns=auto list=0
  local columns='' use_color=0 id name='' width=0 rows=0 art=''
  local shown=0 skipped=0

  while (( $# > 0 )); do
    case "$1" in
      --columns)
        (( $# >= 2 )) || fail 'missing --columns value'
        requested_columns=$2; shift 2 ;;
      --columns=*) requested_columns=${1#*=}; shift ;;
      --color)
        (( $# >= 2 )) || fail 'missing --color value'
        color=$2; shift 2 ;;
      --color=*) color=${1#*=}; shift ;;
      --no-color) color=never; shift ;;
      --list) list=1; shift ;;
      -h|--help) usage; return 0 ;;
      all|[1-5]|orbit|vector|cartridge|launchpad|prompt)
        (( ! selected )) || fail 'choose one ID, or all'
        selection=$1; selected=1; shift ;;
      *) fail "unknown option or ID: $1" ;;
    esac
  done
  case "$color" in auto|always|never) ;; *) fail 'invalid color mode' ;; esac

  if [[ $requested_columns == auto ]]; then
    columns=${COLUMNS:-}
    if ! valid_columns "$columns"; then
      columns=''
      if { [[ -t 1 ]] || [[ -t 2 ]]; } && command -v tput >/dev/null 2>&1; then
        columns=$(tput cols 2>/dev/null) || columns=''
      fi
      valid_columns "$columns" || columns=50
    fi
  else
    valid_columns "$requested_columns" || fail 'columns must be auto or 1-9999'
    columns=$requested_columns
  fi
  columns=$((10#$columns))
  (( columns <= 50 )) || columns=50

  if (( list )); then
    for id in 1 2 3 4 5; do
      load_variant "$id" || return $?
      printf '%s %-10s %2s cols / %2s rows\n' "$id" "$name" "$width" "$rows" || return $?
    done
    return 0
  fi

  case "$selection" in
    orbit) selection=1 ;; vector) selection=2 ;; cartridge) selection=3 ;;
    launchpad) selection=4 ;; prompt) selection=5 ;;
  esac
  case "$color" in
    always) use_color=1 ;;
    auto)
      if [[ -t 1 && ${TERM:-dumb} != dumb && -z ${NO_COLOR:-} ]]; then
        use_color=1
      fi ;;
  esac

  if [[ $selection != all ]]; then
    load_variant "$selection" || return $?
    if (( width > columns )); then
      printf 'Needs %s cols; limit is %s.\n' "$width" "$columns" >&2
      printf 'Try 4 (32 cols) or 5 (37 cols).\n' >&2
      return 2
    fi
    render
    return $?
  fi

  for id in 1 2 3 4 5; do
    load_variant "$id" || return $?
    if (( width > columns )); then
      skipped=$((skipped+1))
      continue
    fi
    if (( shown > 0 )); then printf '\n' || return $?; fi
    # This label is shorter than its corresponding artwork.
    printf '%02d / %s / %s cols\n\n' "$id" "$name" "$width" || return $?
    render || return $?
    shown=$((shown+1))
  done
  if (( skipped > 0 )); then
    printf '\n%s wide variants skipped.\n' "$skipped" >&2
  fi
  if (( shown == 0 )); then
    printf 'Art needs at least 32 columns.\n' >&2
    return 2
  fi
}

main "$@"
