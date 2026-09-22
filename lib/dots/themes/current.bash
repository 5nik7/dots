# Query the selected non-Catppuccin family with familiar color/flavor/format flags.
dt_current() {
  local color='' format=hex raw=0 array=0 token name file flavor=$DT_FLAVOR
  if (($# == 0)); then
    set -- show "$DT_THEME" "$DT_FLAVOR"
    source "$DT_LIB/cli.bash"
    return
  fi
  while (($#)); do
    token=$1; shift
    case $token in
      -h|--help) printf '%s\n' 'current_theme [FLAVOR] [COLOR] [FORMAT] [-r|--raw] [-a|--array]' 'Flags: -f/--flavor, -c/--color, -F/--format; init/--init emits shell data.'; return ;;
      -r|--raw) raw=1 ;; -a|--array) raw=1 array=1 ;;
      -f|--flavor)
        if (($#)); then flavor=$1; shift
        else for file in "$DT_ROOT/$DT_THEME/flavors/"*.toml; do name=${file##*/}; printf '%s\n' "${name%.toml}"; done; return; fi ;;
      -c|--color)
        if (($#)); then color=$1; shift
        else dt_load "$DT_THEME" "$flavor" && printf '%s\n' "${DT_NAMES[@]}"; return; fi ;;
      -F|--format)
        if (($#)); then format=$1; shift
        else printf '%s\n' "${DT_FORMATS[@]}"; return; fi ;;
      init|--init) dt_load "$DT_THEME" "$flavor" && dt_cached_init bash; return ;;
      -e) format=esc ;;
      *)
        if dt_id "$token" && [[ -f $DT_ROOT/$DT_THEME/flavors/$token.toml ]]; then flavor=$token
        else
          local found=0
          for name in "${DT_FORMATS[@]}"; do [[ $token != "$name" ]] || { format=$token; found=1; break; }; done
          if (( ! found )); then
            dt_key "$token" || { dt_error 'unknown color, flavor or format; see current_theme --help'; return 2; }
            color=$token
          fi
        fi ;;
    esac
  done
  dt_load "$DT_THEME" "$flavor" || return
  local -a names=("${DT_NAMES[@]}")
  if [[ $color ]]; then
    dt_key "$color" && [[ ${DT_COLORS[$color]+yes} ]] || { dt_error 'unknown color'; return 1; }
    names=("$color")
  fi
  for name in "${names[@]}"; do
    dt_value "$name" "$format" "${DT_COLORS[$name]}" || return
    if (( array )); then printf '%s=%q\n' "$name" "$REPLY"
    elif (( raw )) || [[ $color ]]; then printf '%s\n' "$REPLY"
    else printf '%-20s %s\n' "$name" "$REPLY"; fi
  done
}
dt_current "$@"
