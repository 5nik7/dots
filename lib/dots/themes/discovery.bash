# Data-only theme discovery. Sourcing defines helpers; enumeration is on demand.
# Callers supply roots; core.bash supplies validation and selection loading.
dt_current_id() {
  dt_selected selection || return
  REPLY=$DT_THEME-$DT_FLAVOR
  [[ -d $DT_ROOT/$REPLY || -d $DT_USER_THEMES/$REPLY ]] || REPLY=$DT_THEME
}
# Keep enumeration in the calling shell: completion must not fork to read IDs.
# Results are replaced on every request, including empty/invalid requests.
dt_discover_ids() {
  local kind=$1 value=${2:-} path name
  declare -ga DT_DISCOVERY_IDS=()
  case $kind in
    theme-id)
      local mode=${value:-selectable}
      local -A seen=()
      [[ $mode == selectable || $mode == completion ]] || return 2
      for path in "$DT_ROOT/"*/colors.toml "$DT_USER_THEMES/"*/colors.toml; do
        [[ -f $path && ! -L $path ]] || continue
        name=${path%/colors.toml}; name=${name##*/}
        # Preserve literal completion hints, including invalid names and
        # repeated roots. Selection remains validated by the theme loader.
        if [[ $mode == selectable ]]; then
          dt_theme_id "$name" || continue
          [[ ! ${seen[$name]:-} ]] || continue
          seen[$name]=1
        fi
        DT_DISCOVERY_IDS+=("$name")
      done
      [[ ! -d $DT_ROOT/pywal16-current ]] || DT_DISCOVERY_IDS+=(pywal16-current) ;;
    families)
      for path in "$DT_ROOT/"*/theme.toml; do
        [[ -f $path && -d ${path%/theme.toml}/flavors ]] || continue
        name=${path%/theme.toml}; DT_DISCOVERY_IDS+=("${name##*/}")
      done ;;
    flavors)
      dt_theme_id "$value" || return 0
      for path in "$DT_ROOT/$value/flavors/"*.toml; do
        [[ -f $path ]] || continue
        name=${path##*/}; DT_DISCOVERY_IDS+=("${name%.toml}")
      done ;;
    *) return 2 ;;
  esac
  return 0
}
# Existing list/switcher callers consume lines; completion consumes the array.
dt_theme_ids() {
  dt_discover_ids theme-id "${1:-selectable}" || return
  ((${#DT_DISCOVERY_IDS[@]} == 0)) || printf '%s\n' "${DT_DISCOVERY_IDS[@]}"
}
