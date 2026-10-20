# One native palette grammar for Dots routes and generated compatibility commands.
source "$DT_LIB/families.bash"
dt_palette_help() {
  local family=$1 flavor=${2:-} id='' current='' logo=''
  if [[ ! $flavor ]]; then
    dt_current_id 2>/dev/null && current=$REPLY
    if [[ ${DT_ID_FAMILIES[$current]:-} == "$family" ]]; then flavor=${DT_ID_FLAVORS[$current]}; fi
  fi
  dt_family_pick "$family" "$flavor" 2>/dev/null && id=$REPLY
  if [[ $id ]] && dt_find_theme "$id" && [[ -f $DT_THEME_DIR/logo.txt && ! -L $DT_THEME_DIR/logo.txt ]]; then logo=$DT_THEME_DIR/logo.txt
  elif [[ -f ${DT_FAMILY_DIRS[$family]}/logo.txt ]]; then logo=${DT_FAMILY_DIRS[$family]}/logo.txt; fi
  [[ $family != catppuccin || ${CATPPUCCIN_SHOW_LOGO:-1} != 0 ]] || logo=''
  dots::settings || return
  local -a artwork=()
  [[ ! $logo ]] || artwork=(--logo "$logo")
  {
    printf '%s — %s\n\n' "$family" "${id:-choose a flavor}"
    printf 'Usage: %s [FLAVOR] [ACTION | COLOR [FORMAT]]\n\n' "$family"
    printf '%s\n' 'Actions:' '  FLAVOR / show   Preview the native palette' '  set             Activate through Dots' '  init            Export shell color arrays' '  --help          Show this usage' '' 'Examples:'
    printf '  %s %s\n  %s %s blue hex\n  %s %s set --dry-run\n' "$family" "${flavor:-${DT_FAMILY_DEFAULTS[$family]:-FLAVOR}}" "$family" "${flavor:-${DT_FAMILY_DEFAULTS[$family]:-FLAVOR}}" "$family" "${flavor:-${DT_FAMILY_DEFAULTS[$family]:-FLAVOR}}"
    printf '\n%s\n' 'Options:' '  --color=auto|always|never|none   Output decoration' '  -c / --color NAME              Query a palette color' '  -f / --flavor, -F / --format, -r / --raw, -a / --array' '  --all, --dry-run, --background, -v / --verbose (set), --completion bash|zsh|fish|powershell' '' 'Flavors:'
    dt_family_flavors "$family"; printf '  %s\n' "${DT_FAMILY_FLAVORS[@]}"
    printf '\nFormats:'; printf ' %s' "${DT_FORMATS[@]}"; printf '\n'
  } | DOTS_COLOR="${DOTS_COLOR:-${dots_options[DOTS_COLOR]:-auto}}" python3 -B "$DT_LIB/presentation.py" --theme "${id:-$family}" "${artwork[@]}"
}
dt_palette_completion_script() {
  local family=$1 shell=$2 fish_path=${DT_LIB%/themes}/completion/fish
  fish_path=${fish_path//\\/\\\\}; fish_path=${fish_path//\'/\\\'}
  case $shell in
    powershell) cat "${DT_LIB%/themes}/completion/powershell" ;;
    bash) printf 'source %q\ncomplete -F _dots_complete_bash -- %q\n' "${DT_LIB%/themes}/completion/bash" "$family" ;;
    zsh) printf '#compdef %s\nsource %q\ncompdef _dots %q\n' "$family" "${DT_LIB%/themes}/completion/zsh" "$family" ;;
    fish) printf "source '%s'\ncomplete -c '%s' -f -a '(__dots_complete_fish)'\n" "$fish_path" "$family" ;;
    *) return 2 ;;
  esac
}
dt_palette_command() {
  local target=$1 family flavor='' color='' format=hex raw=0 array=0 all=0 action=show token name id
  shift
  # Presentation uses equals syntax; --color NAME remains a palette query.
  local -a arguments=()
  local argument
  for argument in "$@"; do
    case $argument in
      --color=*)
        case ${argument#*=} in auto|always|never) export DOTS_COLOR=${argument#*=} ;; none) export DOTS_COLOR=never ;; *) return 2 ;; esac ;;
      *) arguments+=("$argument") ;;
    esac
  done
  set -- "${arguments[@]}"
  dt_family_index || return
  if [[ ${DT_ID_FAMILIES[$target]:-} ]]; then
    family=${DT_ID_FAMILIES[$target]} flavor=${DT_ID_FLAVORS[$target]}
  elif [[ ${DT_FAMILY_DIRS[$target]:-} ]]; then family=$target
  else dt_error "unknown theme: $target"; return 1; fi
  if (($# == 0)); then dt_palette_help "$family" "$flavor"; return; fi
  local -a flags=() names=() flavors=()
  while (($#)); do
    token=$1; shift
    case $token in
      -h|--help|help) dt_palette_help "$family" "$flavor"; return ;;
      -r|--raw) raw=1 ;; -a|--array) raw=1 array=1 ;; --all) all=1 ;;
      --dry-run|--background|-v|--verbose) flags+=("$token") ;;
      show|set|init|--init) action=${token#--} ;;
      color) action=show ;;
      --completion|completion) (($# == 1)) || return 2; dt_palette_completion_script "$family" "$1"; return ;;
      --completion=*) dt_palette_completion_script "$family" "${token#*=}"; return ;;
      -f|--flavor)
        if (($#)); then flavor=$1; shift
        else dt_family_flavors "$family"; printf '%s\n' "${DT_FAMILY_FLAVORS[@]}"; return; fi ;;
      -c|--color)
        if (($#)); then color=$1; shift
        else dt_family_pick "$family" "$flavor" && dt_load_native "$REPLY" && printf '%s\n' "${DT_NAMES[@]}"; return; fi ;;
      -F|--format)
        if (($#)); then format=$1; shift
        else printf '%s\n' "${DT_FORMATS[@]}"; return; fi ;;
      -e) format=esc ;;
      -*) return 2 ;;
      *)
        if [[ ${DT_FAMILY_VARIANTS[$family:$token]:-} ]]; then flavor=$token
        else
          local found=0
          for name in "${DT_FORMATS[@]}"; do [[ $name != "$token" ]] || { format=$token; found=1; break; }; done
          if (( ! found )); then [[ ! $color ]] && dt_key "$token" || return 2; color=$token; fi
        fi ;;
    esac
  done
  if [[ $action != show ]]; then
    (( ! all && ! raw )) && [[ ! $color ]] || return 2
    dt_family_pick "$family" "$flavor" || return; id=$REPLY
    if [[ $action == set ]]; then
      "${DT_LIB%/lib/dots/themes}/bin/dots-theme-set" "$id" "${flags[@]}"
    else
      ((${#flags[@]} == 0)) || return 2
      dt_load "$id" && dt_cached_init bash
    fi
    return
  fi
  ((${#flags[@]} == 0)) || return 2
  if ((all)); then dt_family_flavors "$family"; flavors=("${DT_FAMILY_FLAVORS[@]}")
  else dt_family_pick "$family" "$flavor" || return; flavors=("${DT_ID_FLAVORS[$REPLY]}"); fi
  for flavor in "${flavors[@]}"; do
    dt_family_pick "$family" "$flavor" && dt_load_native "$REPLY" || return
    if [[ ! $color && $format == hex && $raw == 0 ]]; then dt_native_preview; continue; fi
    names=("${DT_NAMES[@]}")
    if [[ $color ]]; then
      [[ ${DT_COLORS[$color]+yes} ]] || { dt_error 'unknown color'; return 1; }
      names=("$color")
    fi
    for name in "${names[@]}"; do
      dt_value "$name" "$format" "${DT_COLORS[$name]}" || return
      if ((array)); then printf '%s=%q\n' "$name" "$REPLY"
      elif ((raw)) || [[ $color ]]; then printf '%s\n' "$REPLY"
      else printf '%-20s %s\n' "$name" "$REPLY"; fi
    done
  done
}
