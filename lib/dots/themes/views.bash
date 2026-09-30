# Shared theme views and initialization; no command parser or implicit execution.
source "$DT_LIB/../ui.bash"

dt_init() {
  local shell=zsh file
  if (($#)); then [[ $# == 2 && $1 == --shell ]] || return 2; shell=$2; fi
  [[ $shell == bash || $shell == zsh || $shell == fish ]] || return 2
  dt_selected selection || return
  if [[ $DT_GENERATION ]]; then
    file=$DT_STATE/generations/$DT_GENERATION/init.zsh
    [[ $shell != fish ]] || file=$DT_STATE/generations/$DT_GENERATION/init.fish
    [[ -f $file && ! -L $file ]] || { dt_error 'missing generated initialization; run theme refresh'; return 1; }
    cat "$file"
  else dt_cached_init "$shell"; fi
}

# Retain the standalone current_theme palette preview format as well.
dt_native_preview() {
  local name
  dots::heading "$DT_THEME — $DT_FLAVOR"
  dots::style
  for name in "${DT_NAMES[@]}"; do
    if [[ $DOTS_UI_RESET ]]; then dt_value "$name" esc "${DT_COLORS[$name]}"; printf '%s██%s ' "$REPLY" "$DOTS_UI_RESET"; fi
    dots::row "$name" "${DT_COLORS[$name]}"
  done
}

dt_palette_list() {
  local kind=$1 family=${2:-} name
  local -a names=()
  if [[ $kind == flavors ]]; then
    dt_theme_id "$family" && [[ -d $DT_ROOT/$family/flavors ]] || { dt_error 'unknown palette family'; return 1; }
    dt_parse "$DT_ROOT/$family/theme.toml" metadata || return
  fi
  dt_discover_ids "$kind" "$family" || return
  names=("${DT_DISCOVERY_IDS[@]}")
  if dots::human; then
    if [[ $kind == flavors ]]; then dots::heading "$family flavors"; else dots::heading 'Palette families'; fi
    for name in "${names[@]}"; do dots::row "$name"; done
    ((${#names[@]})) || dots::info 'No entries available'
  elif ((${#names[@]})); then printf '%s\n' "${names[@]}"; fi
  return 0
}
