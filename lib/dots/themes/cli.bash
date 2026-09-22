# shellcheck source-path=SCRIPTDIR
source "$DT_LIB/core.bash"
source "$DT_LIB/../ui.bash"
dt_main() {
  local action=${1:-help} name file flavor shell=zsh
  (($# == 0)) || shift
  if [[ ${1:-} == --help || ${1:-} == -h ]]; then action=help; fi
  case $action in
    help|--help|-h)
      dots::heading 'dots themes — shared palettes for your shell and Neovim'
      dots::row 'list [THEME]' 'List themes or flavors'
      dots::row 'show THEME [FLAVOR]' 'Preview a palette'
      dots::row 'color THEME FLAVOR COLOR [FORMAT]' 'Print a color value (default: hex)'
      dots::row 'current' 'Print the effective theme-flavor identifier'
      dots::row 'set THEME [FLAVOR]' 'Persist a selection (default: theme default flavor)'
      dots::row 'init [--shell SHELL]' 'Emit Bash, Zsh, or Fish initialization'
      ;;
    list)
      (($# <= 1)) || return 2
      if (($#)); then
        dt_load "$1" || return
        for file in "$DT_ROOT/$1/flavors/"*.toml; do [[ -f $file ]] || continue; name=${file##*/}; printf '%s\n' "${name%.toml}"; done
      else
        for file in "$DT_ROOT/"*/theme.toml; do [[ -f $file ]] || continue; name=${file%/theme.toml}; printf '%s\n' "${name##*/}"; done
      fi ;;
    current) (($# == 0)) || return 2; dt_selected selection && printf '%s-%s\n' "$DT_THEME" "$DT_FLAVOR" ;;
    show)
      (($# >= 1 && $# <= 2)) || return 2
      dt_load "$1" "${2:-}" || return
      dots::heading "$DT_THEME — $DT_FLAVOR"
      dots::style
      for name in "${DT_NAMES[@]}"; do
        if [[ $DOTS_UI_RESET ]]; then dt_value "$name" esc "${DT_COLORS[$name]}"; printf '%s██%s ' "$REPLY" "$DOTS_UI_RESET"; fi
        dots::row "$name" "${DT_COLORS[$name]}"
      done ;;
    color)
      (($# >= 3 && $# <= 4)) || return 2
      dt_load "$1" "$2" || return
      [[ ${DT_COLORS[$3]+yes} ]] || { dt_error 'unknown color'; return 1; }
      dt_value "$3" "${4:-hex}" "${DT_COLORS[$3]}" && printf '%s\n' "$REPLY" ;;
    init)
      if (($#)); then [[ $# == 2 && $1 == --shell ]] || return 2; shell=$2; fi
      [[ $shell == bash || $shell == zsh || $shell == fish ]] || return 2
      dt_selected selection || return
      if [[ $DT_GENERATION ]]; then
        file=$DT_STATE/generations/$DT_GENERATION/init.zsh
        [[ $shell != fish ]] || file=$DT_STATE/generations/$DT_GENERATION/init.fish
        [[ -f $file && ! -L $file ]] || { dt_error 'missing generated initialization; run themes set again'; return 1; }
        cat "$file"
      else dt_cached_init "$shell"; fi ;;
    set)
      (($# >= 1 && $# <= 2)) || return 2
      source "$DT_LIB/state.bash"
      dt_set "$@" ;;
    *) dt_error "unknown theme command: $action"; return 2 ;;
  esac
}
if dt_main "$@"; then
  return 0
else
  dt_status=$?
  if (( dt_status == 2 )); then dt_error 'invalid arguments; see dots themes --help'; fi
  return "$dt_status"
fi
