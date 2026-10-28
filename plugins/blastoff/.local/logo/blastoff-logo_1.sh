#!/usr/bin/env bash
# blastoff-logo: Unicode block art with a purple-to-pink foreground gradient.
# Self-contained; requires Bash and a terminal/font that displays UTF-8 blocks.
# Optional tput improves automatic terminal-width detection.

set -u

usage() {
  printf '%s\n' 'Usage: blastoff-logo [OPTIONS]

  --size auto|compact|wide|word  Artwork size (default: auto).
  --color auto|always|never     Color mode (default: auto).
  --no-color                   Same as --color never.
  -h, --help                   Show this help.

Sizes: compact = 60 columns / 8 rows; wide = 96 columns / 11 rows.
Auto uses wide at 96+ columns, compact at 60-95, and a small word below 60.
Unknown terminal width defaults to 60 columns. COLUMNS overrides detection.
Color auto requires terminal stdout, TERM other than dumb, and no nonempty
NO_COLOR. Always forces 24-bit color, including when redirecting to a file.
Only foreground colors are emitted; your terminal background is untouched.

Examples:
  bash blastoff-logo.sh
  bash blastoff-logo.sh --size wide
  bash blastoff-logo.sh --size compact --no-color
  bash blastoff-logo.sh --size wide --color always > blastoff.ansi'
}

fail() {
  printf 'blastoff-logo: %s\n' "$*" >&2
  exit 2
}

size=auto
color=auto
while (( $# > 0 )); do
  case "$1" in
    --size)
      (( $# >= 2 )) || fail 'missing value for --size'
      size=$2; shift 2 ;;
    --size=*) size=${1#*=}; shift ;;
    --color)
      (( $# >= 2 )) || fail 'missing value for --color'
      color=$2; shift 2 ;;
    --color=*) color=${1#*=}; shift ;;
    --no-color) color=never; shift ;;
    -h|--help) usage; exit 0 ;;
    *) fail "unknown argument: $1 (use --help)" ;;
  esac
done
case "$size" in auto|compact|wide|word) ;; *) fail 'size must be auto, compact, wide, or word' ;; esac
case "$color" in auto|always|never) ;; *) fail 'color must be auto, always, or never' ;; esac

# Width is an integer in the range 1-9999. Validate before arithmetic.
valid_columns() {
  case "$1" in ''|*[!0-9]*) return 1 ;; esac
  (( ${#1} <= 4 )) || return 1
  (( 10#$1 > 0 ))
}

if [[ $size == auto ]]; then
  columns=${COLUMNS:-}
  if ! valid_columns "$columns"; then
    columns=''
    if [[ -t 1 ]] && command -v tput >/dev/null 2>&1; then
      columns=$(tput cols 2>/dev/null) || columns=''
    fi
    valid_columns "$columns" || columns=60
  fi
  columns=$((10#$columns))
  if (( columns >= 96 )); then size=wide
  elif (( columns >= 60 )); then size=compact
  else size=word
  fi
fi

case "$size" in
  compact)
    width=60
    art='██▌       ██▙                   ██▌              ▗▟███ ▗▟███
██▌▗▄▖    ███  ▄▄▄▄▄     ▄▄▄▄▄  ██▙▄▄▄  ▗▟███▙▖  ▟████ ▟████
███████▙  ███  ██████▌ ▗██████▌ ██████ ▗██▛ ▜██▖ ██▙▄▖ ██▙▄▖
██▛▀▀▀██▙ ███  ▀▀▀▀▜██ ██▛▀▀▀▀  ██▛▀▀▀ ▟██▘█▝██▙ ████▌ ████▌
██▌   ▐██ ███ ▗███████ ▜██████▖ ██▌    ███   ███ ██▀▀  ██▀▀▘
██▙   ▟██ ███ ██▛▀▀▜██  ▀▀▀▀▜██ ██▙    ▜█▌▗▗▖▐█▛ ██▌   ██
▜███████▘ ███ ████████ ▟██████▛ ▜█████ ▝█▙█████▘ ██▌   ██
 ▀████▛▘  ▜██ ▝▜█████▘ ██████▛▘  ▀████   ▀███▀   ██▘   ██'
    ;;
  wide)
    width=96
    art='████           ███▙                               ████                       ▄███████   ▄███████
████           ████                               ████          ▄▄▄▄▄▄     ▗█████████ ▗█████████
████▗▄▄▄▄▄▖    ████  ▗▄▄▄▄▄▄▄▄▄▄     ▄▄▄▄▄▄▄▄▄▄▄  ████▄▄▄▄▄   ▄███▛▜███▄   ▟████▀▀▀▀▀ █████▀▀▀▀▀
███████████▙▖  ████  ▐███████████▖ ▗████████████  █████████  ▟███▛  ▜███▙  ████▙▄▄▄▖  ████▙▄▄▄▖
█████████████▖ ████  ▝▀▀▀▀▀▀▀█████ ████████████▀  ████████▀ ▐████▘▗▖▝████▌ ████████▌  █████████
████     ▝███▙ ████   ▗▄▄▄▄▄▄▄████ ████▄▄▄▄▄▄▄▖   ████      █████    █████ ████████▌  ████████▛
████      ▜███ ████ ▗█████████████ ▝████████████▖ ████      ████▀    ▀████ ████▌      ████▌
████     ▗████ ████ ████▀▀▀▀▀▀████   ▀▀▀▀▀▀▀▀████ ████      ▜██▌ ▗▖▗▖ ▐██▛ ████▌      ████▌
▜████▙▄▄█████▘ ████ ████▄▄▄▄▄▟████ ▗▄▄▄▄▄▄▄▄▟████ ▜████▙▄▄▄ ▝██▙▟████▙▟██▘ ████▌      ████▌
▝███████████▘  ████ ▐████████████▛ █████████████▘ ▝████████  ▝▜████████▛▘  ████▌      ████▌
  ▀▜█████▀▀    ▀███  ▝▀████████▛▀  ██████████▛▀     ▀▜█████    ▝▜████▛▘    ████▌      ████▌'
    ;;
  word)
    width=8
    art='blastoff'
    ;;
esac

use_color=0
case "$color" in
  always) use_color=1 ;;
  auto)
    if [[ -t 1 && ${TERM:-dumb} != dumb && -z ${NO_COLOR:-} ]]; then
      use_color=1
    fi
    ;;
esac

if (( ! use_color )); then
  printf '%s\n' "$art"
  exit $?
fi

render_color() {
  # Byte-safe splitting even under LC_ALL=C. The embedded artwork contains
  # ASCII spaces/letters and three-byte U+2580..U+259F block characters only.
  local LC_ALL=C
  local line rest glyph output column i red green blue
  local -a palette
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
    # Restore default foreground without changing background or other styles.
    printf '%s\033[39m\n' "$output" || return $?
  done <<< "$art"
}

render_color
