# Shared theme views and initialization; no command parser or implicit execution.
source "$DT_LIB/../ui.bash"

dt_init() {
  local shell=zsh file
  if (($#)); then [[ $# == 2 && $1 == --shell ]] || return 2; shell=$2; fi
  if [[ $shell == powershell ]]; then python3 -B "$DT_LIB/theme_cli.py" init --shell powershell; return; fi
  [[ $shell == bash || $shell == zsh || $shell == fish ]] || return 2
  dt_selected selection || return
  if [[ $DT_GENERATION ]]; then
    file=$DT_STATE/generations/$DT_GENERATION/init.zsh
    [[ $shell != fish ]] || file=$DT_STATE/generations/$DT_GENERATION/init.fish
    [[ -f $file && ! -L $file ]] || { dt_error 'missing generated initialization; run theme refresh'; return 1; }
    cat "$file"
  else dt_cached_init "$shell"; fi
}

# Shared native palette preview for current and explicit theme queries.
dt_native_preview() {
  local name sep=''
  dots::settings || return
  {
    # Identifiers and hex values have already passed the palette reader's validation.
    printf '{"title":"%s — %s","colors":{' "$DT_THEME" "$DT_FLAVOR"
    for name in "${DT_NAMES[@]}"; do
      printf '%s"%s":"%s"' "$sep" "$name" "${DT_COLORS[$name]}"; sep=,
    done
    printf '}}\n'
  } | DOTS_COLOR="${DOTS_COLOR:-${dots_options[DOTS_COLOR]:-auto}}" python3 -B "$DT_LIB/presentation.py" --theme "${DT_ID:-$DT_THEME-$DT_FLAVOR}" --native-table
}

dt_palette_list() {
  local kind=$1 family=${2:-} name
  local -a names=()
  if [[ $kind == flavors ]]; then
    source "$DT_LIB/families.bash"
    dt_theme_id "$family" && dt_family_index && [[ ${DT_FAMILY_DIRS[$family]:-} ]] || { dt_error 'unknown palette family'; return 1; }
    dt_family_flavors "$family"
    [[ ${#DT_FAMILY_FLAVORS[@]} != 1 || ${DT_FAMILY_FLAVORS[0]} != default ]] || { dt_error 'theme has no named flavors'; return 1; }
  fi
  if [[ $kind == flavors ]]; then names=("${DT_FAMILY_FLAVORS[@]}")
  else
    source "$DT_LIB/families.bash"
    dt_family_index || return
    for name in "${DT_FAMILIES[@]}"; do
      dt_family_flavors "$name"
      [[ ${#DT_FAMILY_FLAVORS[@]} == 1 && ${DT_FAMILY_FLAVORS[0]} == default ]] || names+=("$name")
    done
  fi
  if dots::human; then
    if [[ $kind == flavors ]]; then dots::heading "$family flavors"; else dots::heading 'Palette families'; fi
    for name in "${names[@]}"; do dots::row "$name"; done
    ((${#names[@]})) || dots::info 'No entries available'
  elif ((${#names[@]})); then printf '%s\n' "${names[@]}"; fi
  return 0
}
