#!/usr/bin/env bash

source "$DT_LIB/core.bash"

CATPPUCCIN_SHOW_LOGO=${CATPPUCCIN_SHOW_LOGO:-1}

declare -r esc=$'\033'
declare -r rst="${esc}[0m"
declare -r bold="${esc}[1m"
declare -r italic="${esc}[3m"
declare -r underline="${esc}[4m"
declare -r ansi_red="${esc}[31m"
declare -r ansi_green="${esc}[32m"
declare -r ansi_yellow="${esc}[33m"
declare -r ansi_magenta="${esc}[35m"
declare -r ansi_white="${esc}[37m"
declare -r ansi_brightblack="${esc}[1;30m"
declare -r ansi_brightred="${esc}[1;31m"
declare -r ansi_brightgreen="${esc}[1;32m"
declare -r ansi_brightyellow="${esc}[1;33m"
declare -r ansi_brightblue="${esc}[1;34m"
declare -r ansi_brightmagenta="${esc}[1;35m"
declare -r ansi_brightcyan="${esc}[1;36m"
declare -r ansi_mauve="${esc}[38;2;203;166;247m"
declare -r ansi_peach="${esc}[38;2;250;179;135m"
declare -r ansi_lavender="${esc}[38;2;180;190;254m"
declare -r ansi_maroon="${esc}[38;2;235;160;172m"

declare -r prog="${0##*/}"
declare -r sdir="$DT_ROOT/bin"
declare -r caticon='󰄛'
declare -r block='󰄮'
declare -r default_flavor='mocha'
declare -r default_format='hex'

flavors=(mocha macchiato frappe latte)
palette=(rosewater flamingo pink mauve red maroon peach yellow green teal sky sapphire blue lavender text subtext1 subtext0 overlay2 overlay1 overlay0 surface2 surface1 surface0 base mantle crust)
supported_formats=(name hex rgb r g b rgb-r rgb-g rgb-b luminance brightness cmyk ansi-8bit ansi-8bit-value ansi-8bit-escapecode ansi-24bit ansi-24bit-escapecode esc)

declare -A current_palette=()

raw=0
array=0
FLAVOR=${FLAVOR:-$default_flavor}
COLOR=
COLORFORMAT=

err() { printf '\n%s %s %s\n\n' "${ansi_maroon}${caticon}${rst}" "${ansi_brightred}${bold}[ERROR]${rst}" "${ansi_red}$*${rst}" >&2; }
die() {
  local code=1
  local err cmd
  if [[ $# -eq 0 ]]; then
    exit 1
  fi

  while [[ $# -gt 0 ]]; do
    case "$1" in
    -n | --code)
      code="$2"
      shift 2
      ;;
    -c | --cmd)
      cmd="$2"
      printf '%s' "$cmd"
      shift 2
      ;;
    *)
      err="$(err $1)"
      printf '%s' "$err"
      shift
      ;;
    esac
  done
  printf '%s\n' "$*"
  exit "$code"
}

logo() {
  local logo_file="${sdir}/logo"
  [[ -f "$logo_file" ]] || return 0
  while IFS= read -r line; do
    printf '%s\n' "$line"
  done <"$logo_file"
}

usage() {
  if [[ -n ${CATPPUCCIN_SHOW_LOGO:-} ]]; then
    logo
  fi
  cat <<EOF
${ansi_lavender}${italic}Usage:${rst} ${ansi_brightmagenta}${bold}${underline}${prog}${rst} [${ansi_brightyellow}options${rst}] [${ansi_brightgreen}flavor${rst}] [${ansi_brightcyan}color${rst}] [${ansi_brightblue}format${rst}]

Print Catppuccin palette values, color previews, or shell-friendly arrays.

${ansi_lavender}${bold}Options${rst}
  ${ansi_yellow}-h${rst}, ${ansi_yellow}--help${rst}                  Print this message and exit
  ${ansi_yellow}-f${rst}, ${ansi_yellow}--flavor${rst} ${ansi_brightgreen}FLAVOR${rst}         Select a flavor: ${ansi_green}mocha${rst}, ${ansi_brightgreen}macchiato${rst}, ${ansi_brightgreen}frappe${rst}, ${ansi_brightgreen}latte${rst}
  ${ansi_yellow}-c${rst}, ${ansi_yellow}--color${rst} ${ansi_brightcyan}COLOR${rst}           Select a color name from the palette
  ${ansi_yellow}-F${rst}, ${ansi_yellow}--format${rst} ${ansi_brightblue}FORMAT${rst}         Select an output format
  ${ansi_yellow}-r${rst}, ${ansi_yellow}--raw${rst}                   Print plain values instead of the preview table
  ${ansi_yellow}-a${rst}, ${ansi_yellow}--array${rst}                 Alias for --raw; emits shell assignment-friendly output
  ${ansi_yellow}--all${rst}                       Print every flavor in the preview table
  ${ansi_yellow}init${rst}, ${ansi_yellow}--init${rst}                Emit sourceable Bash arrays for the current flavor
  ${ansi_yellow}--completion${rst} ${ansi_brightcyan}SHELL${rst}          Print shell completion script: ${ansi_brightcyan}bash${rst} or ${ansi_brightcyan}zsh${rst}

${ansi_lavender}${bold}Supported colors${rst}
  ${ansi_brightcyan}rosewater${rst}, ${ansi_brightcyan}flamingo${rst}, ${ansi_brightcyan}pink${rst}, ${ansi_brightcyan}mauve${rst}, ${ansi_brightcyan}red${rst}, ${ansi_brightcyan}maroon${rst}, ${ansi_brightcyan}peach${rst}, ${ansi_brightcyan}yellow${rst},
  ${ansi_brightcyan}green${rst}, ${ansi_brightcyan}teal${rst}, ${ansi_brightcyan}sky${rst}, ${ansi_brightcyan}sapphire${rst}, ${ansi_brightcyan}blue${rst}, ${ansi_brightcyan}lavender${rst}, ${ansi_brightcyan}text${rst}, ${ansi_brightcyan}subtext1${rst},
  ${ansi_brightcyan}subtext0${rst}, ${ansi_brightcyan}overlay2${rst}, ${ansi_brightcyan}overlay1${rst}, ${ansi_brightcyan}overlay0${rst}, ${ansi_brightcyan}surface2${rst}, ${ansi_brightcyan}surface1${rst},
  ${ansi_brightcyan}surface0${rst}, ${ansi_brightcyan}base${rst}, ${ansi_brightcyan}mantle${rst}, ${ansi_brightcyan}crust${rst}

${ansi_lavender}${bold}Supported formats${rst}
  ${ansi_brightblue}name${rst}, ${ansi_brightblue}hex${rst}, ${ansi_brightblue}rgb${rst}, ${ansi_brightblue}r${rst}, ${ansi_brightblue}g${rst}, ${ansi_brightblue}b${rst}, ${ansi_brightblue}rgb-r${rst}, ${ansi_brightblue}rgb-g${rst}, ${ansi_brightblue}rgb-b${rst}, ${ansi_brightblue}luminance${rst}, ${ansi_brightblue}brightness${rst}, ${ansi_brightblue}cmyk${rst},
  ${ansi_brightblue}ansi-8bit${rst}, ${ansi_brightblue}ansi-8bit-value${rst}, ${ansi_brightblue}ansi-8bit-escapecode${rst}, ${ansi_brightblue}ansi-24bit${rst},
  ${ansi_brightblue}ansi-24bit-escapecode${rst}, ${ansi_brightblue}esc${rst}

${ansi_lavender}${bold}Examples${rst}
  ${ansi_brightmagenta}${bold}${prog}${rst} ${ansi_brightgreen}mocha${rst}
  ${ansi_brightmagenta}${bold}${prog}${rst} ${ansi_yellow}${italic}--color${rst} ${ansi_brightcyan}${bold}blue${rst} ${ansi_yellow}${italic}--format${rst} ${ansi_brightblue}rgb${rst}
  ${ansi_mauve}${bold}eval${rst} ${ansi_green}"${ansi_peach}\$${ansi_green}(${ansi_brightmagenta}${bold}${prog}${rst} ${bold}${ansi_brightyellow}${italic}init${rst}${ansi_green})"${rst}
EOF
}

completion_func_name() {
  local name=${prog//[^A-Za-z0-9_]/_}
  printf '_%s' "$name"
}

completion_bash() {
  local fn qprog
  fn=$(completion_func_name)
  printf -v qprog '%q' "$prog"

  cat <<EOF
# bash completion for ${prog}
# Install:
#   ${prog} --completion bash > ~/.local/share/bash-completion/completions/${prog}

${fn}() {
  local cur prev
  COMPREPLY=()

  if [[ -z \"\${COMP_WORDS[*]:-}\" ]]; then
    return 0
  fi

  cur="\${COMP_WORDS[COMP_CWORD]}"
  prev="\${COMP_WORDS[COMP_CWORD-1]}"

  case "\$prev" in
    -f|--flavor)
      COMPREPLY=( \$(compgen -W "mocha macchiato frappe latte" -- "\$cur") )
      return 0
      ;;
    -c|--color)
      COMPREPLY=( \$(compgen -W "rosewater flamingo pink mauve red maroon peach yellow green teal sky sapphire blue lavender text subtext1 subtext0 overlay2 overlay1 overlay0 surface2 surface1 surface0 base mantle crust" -- "\$cur") )
      return 0
      ;;
    -F|--format)
      COMPREPLY=( \$(compgen -W "name hex rgb r g b rgb-r rgb-g rgb-b luminance brightness cmyk ansi-8bit ansi-8bit-value ansi-8bit-escapecode ansi-24bit ansi-24bit-escapecode esc" -- "\$cur") )
      return 0
      ;;
    --completion|completion)
      COMPREPLY=( \$(compgen -W "bash zsh" -- "\$cur") )
      return 0
      ;;
  esac

  case "\$cur" in
    -*)
      COMPREPLY=( \$(compgen -W "-h --help -f --flavor -c --color -F --format -r --raw -a --array --all init --init --completion" -- "\$cur") )
      ;;
    *)
      COMPREPLY=( \$(compgen -W "mocha macchiato frappe latte rosewater flamingo pink mauve red maroon peach yellow green teal sky sapphire blue lavender text subtext1 subtext0 overlay2 overlay1 overlay0 surface2 surface1 surface0 base mantle crust name hex rgb r g b rgb-r rgb-g rgb-b luminance brightness cmyk ansi-8bit ansi-8bit-value ansi-8bit-escapecode ansi-24bit ansi-24bit-escapecode esc init --all --init" -- "\$cur") )
      ;;
  esac
}

complete -F ${fn} -- ${qprog}
EOF
}

completion_zsh() {
  local fn
  fn=$(completion_func_name)

  cat <<EOF
#compdef ${prog}
# zsh completion for ${prog}
# Install:
#   ${prog} --completion zsh > ~/.zfunc/_${prog}
# Then ensure ~/.zfunc is in \$fpath and run: autoload -Uz compinit && compinit

${fn}() {
  local -a flavors colors formats options
  flavors=(mocha macchiato frappe latte)
  colors=(rosewater flamingo pink mauve red maroon peach yellow green teal sky sapphire blue lavender text subtext1 subtext0 overlay2 overlay1 overlay0 surface2 surface1 surface0 base mantle crust)
  formats=(name hex rgb r g b rgb-r rgb-g rgb-b luminance brightness cmyk ansi-8bit ansi-8bit-value ansi-8bit-escapecode ansi-24bit ansi-24bit-escapecode esc)
  options=(-h --help -f --flavor -c --color -F --format -r --raw -a --array --all --completion init --init)

  case "\${words[CURRENT-1]}" in
    -f|--flavor)
      compadd -- \${flavors[@]}
      return
      ;;
    -c|--color)
      compadd -- \${colors[@]}
      return
      ;;
    -F|--format)
      compadd -- \${formats[@]}
      return
      ;;
    --completion|completion)
      compadd -- bash zsh
      return
      ;;
  esac

  compadd -- \${options[@]} \${flavors[@]} \${colors[@]} \${formats[@]}
}

compdef ${fn} ${prog}
EOF
}

print_completion() {
  local shell=$1

  case "$shell" in
  bash) completion_bash ;;
  zsh) completion_zsh ;;
  *) die "Unsupported completion shell: $shell" ;;
  esac
}

load_flavor() {
  dt_load catppuccin "$1" || return
  current_palette=()
  local color
  for color in "${palette[@]}"; do current_palette[$color]=${DT_COLORS[$color]}; done
}

hex_to_rgb() {
  local hex="${1#\#}"
  printf '%d %d %d\n' "$((16#${hex:0:2}))" "$((16#${hex:2:2}))" "$((16#${hex:4:2}))"
}

rgb_escape() {
  local r=$1
  local g=$2
  local b=$3
  printf '%s[38;2;%s;%s;%sm' "$esc" "$r" "$g" "$b"
}

ansi8_escape() {
  local code=$1
  printf '%s[38;5;%sm' "$esc" "$code"
}

rgb_to_ansi8() {
  local r=$1
  local g=$2
  local b=$3
  local rc gc bc

  if ((r == g && g == b)); then
    if ((r < 8)); then
      printf '16\n'
      return
    fi
    if ((r > 248)); then
      printf '231\n'
      return
    fi
    printf '%d\n' "$((232 + ((r - 8) * 24 / 247)))"
    return
  fi

  rc=$(((r * 5 + 127) / 255))
  gc=$(((g * 5 + 127) / 255))
  bc=$(((b * 5 + 127) / 255))
  printf '%d\n' "$((16 + 36 * rc + 6 * gc + bc))"
}

format_value() {
  dt_value "$1" "$2" "$3" || return
  printf '%s' "$REPLY"
  case $2 in esc|*-escapecode) ;; *) printf '
' ;; esac
}

swatch() {
  local hex=$1
  local r g b
  read -r r g b <<<"$(hex_to_rgb "$hex")"
  printf '%s%s%s' "$(rgb_escape "$r" "$g" "$b")" "$block" "$rst"
}

list_colors() {
  load_flavor "$FLAVOR" || load_flavor "$default_flavor" || return 1

  if ((raw)); then
    printf '%s\n' "${palette[@]}"
    return
  fi

  printf '%s\n' 'Colors:'
  local name
  for name in "${palette[@]}"; do
    printf '  %s %s\n' "$(swatch "${current_palette[$name]}")" "$name"
  done
}

list_flavors() {
  if ((raw)); then
    printf '%s\n' "${flavors[@]}"
    return
  fi

  printf '%s\n' 'Flavors:'
  local flavor current=${FLAVOR}
  for flavor in "${flavors[@]}"; do
    if [[ $flavor == "$current" ]]; then
      printf '  %s%s%s%s\n' "$ansi_magenta" "$flavor" "$rst" " ${ansi_brightblack}(current)${rst}"
    elif [[ $flavor == "$default_flavor" ]]; then
      printf '  %s%s%s%s\n' "$ansi_white" "$flavor" "$rst" " ${ansi_brightblack}(default)${rst}"
    else
      printf '  %s%s%s\n' "$ansi_white" "$flavor" "$rst"
    fi
  done
}

list_formats() {
  printf '%s\n' 'Formats:'
  printf '  %s\n' "${supported_formats[@]}"
}

validate_format() {
  local format=$1
  case "$format" in
  name | hex | rgb | r | g | b | rgb-r | rgb-g | rgb-b | luminance | brightness | cmyk | ansi-8bit | ansi-8bit-value | ansi-8bit-escapecode | ansi-24bit | ansi-24bit-escapecode | esc)
    return 0
    ;;
  *)
    die "Unsupported format: $format" -c "$(list_formats)"
    ;;
  esac
}

print_colors() {
  local format=${COLORFORMAT:-$default_format}
  local name hex value

  for name in "${palette[@]}"; do
    hex="${current_palette[$name]}"
    value="$(format_value "$name" "$format" "$hex")"
    if ((raw)); then
      if ((array)); then
        printf '%s=%q\n' "$name" "$value"
      else
        printf '%s\n' "$value"
      fi
    else
      printf '%s %-10s %s\n' "$(swatch "$hex")" "$name" "$value"
    fi
  done
}

print_all() {
  local flavor
  for flavor in "${flavors[@]}"; do
    load_flavor "$flavor" || continue
    printf '%s\n' "${bold}${flavor}${rst}"
    print_colors
    printf '\n'
  done
}

# These are inputs consumed by the shared engine.
# shellcheck disable=SC2034
init() { DT_THEME=catppuccin DT_FLAVOR=$FLAVOR; dt_cached_init bash; }

main() {
  if [[ $# -eq 0 ]]; then
    usage
    exit 0
  fi

  while [[ $# -gt 0 ]]; do
    case "$1" in
    init | --init)
      init
      exit 0
      ;;
    -a | --array)
      raw=1
      array=1

      shift
      ;;
    -r | --raw)
      raw=1

      shift
      ;;
    -h | --help)
      usage
      exit 0
      ;;
    --all)
      load_flavor "$FLAVOR" || load_flavor "$default_flavor"
      print_all
      exit 0
      ;;
    --completion)
      [[ $# -ge 2 ]] || die "missing shell for --completion"
      print_completion "$2"
      exit 0
      ;;
    --completion=*)
      print_completion "${1#--completion=}"
      exit 0
      ;;
    completion)
      [[ $# -ge 2 ]] || die "missing shell for completion"
      print_completion "$2"
      exit 0
      ;;
    -f | --flavor)
      if [[ -n ${2:-} ]]; then
        FLAVOR=$2
        shift 2
      else
        list_flavors
        exit 0
      fi
      ;;
    mocha | macchiato | frappe | latte)
      FLAVOR=$1
      shift
      ;;
    -c | --color)
      if [[ -n ${2:-} ]]; then
        COLOR=$2
        shift 2
      else
        list_colors
        exit 0
      fi
      ;;
    rosewater | flamingo | pink | mauve | red | maroon | peach | yellow | green | teal | sky | sapphire | blue | lavender | text | subtext1 | subtext0 | overlay2 | overlay1 | overlay0 | surface2 | surface1 | surface0 | base | mantle | crust)
      COLOR=$1
      shift
      ;;
    -F | --format)
      if [[ -n ${2:-} ]]; then
        COLORFORMAT=$2
        shift 2
      else
        list_formats
        exit 0
      fi
      ;;
    esc | -e)
      COLORFORMAT='esc'
      shift
      ;;
    name | hex | rgb | r | g | b | rgb-r | rgb-g | rgb-b | luminance | brightness | cmyk | ansi-8bit | ansi-8bit-value | ansi-8bit-escapecode | ansi-24bit | ansi-24bit-escapecode)
      COLORFORMAT=$1
      shift
      ;;
    *)
      CATPPUCCIN_SHOW_LOGO=''
      die "Unknown option: $1" -c "$(usage)"
      ;;
    esac
  done

  COLORFORMAT=${COLORFORMAT:-$default_format}
  validate_format "$COLORFORMAT"

  load_flavor "$FLAVOR" || {
    die "'$FLAVOR' is not a flavor." -c "$(list_flavors)"
  }

  if [[ -n ${COLOR:-} ]]; then
    if [[ -n ${current_palette[$COLOR]+x} ]]; then
      format_value "$COLOR" "$COLORFORMAT" "${current_palette[$COLOR]}"
    else
      die "Color '$COLOR' not found in flavor '$FLAVOR'." -c "$(list_colors)"
    fi
  else
    print_colors
  fi
}

main "$@"
