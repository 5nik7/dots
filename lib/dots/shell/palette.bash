# Portable data artifact for native adapters. Values contain no tabs/newlines;
# escape colors contain literal SGR bytes and are never evaluated as code.
dt_emit_shell_data() (
  local name format role
  local -A DT_SHELL_COLORS=()
  dt_shell_colors || exit
  printf '@theme\tid\t%s\n@theme\tfamily\t%s\n@theme\tflavor\t%s\n' "$DT_ID" "$DT_THEME" "$DT_FLAVOR"
  for name in "${DT_NAMES[@]}"; do printf '@palette\t%s\t%s\n' "$name" "${DT_COLORS[$name]}"; done
  for role in background foreground muted accent selection error warning info hint; do
    printf '@role\t%s\t%s\n' "$role" "${DT_SHELL_COLORS[$role]}"
  done
  DT_COLORS=() DT_NAMES=("${!DT_SHELL_COLORS[@]}")
  for name in "${DT_NAMES[@]}"; do DT_COLORS[$name]=${DT_SHELL_COLORS[$name]}; done
  dt_metrics || exit
  for name in "${DT_NAMES[@]}"; do
    for format in "${DT_FORMATS[@]}"; do
      dt_value "$name" "$format" "${DT_COLORS[$name]}" || exit
      printf '%s\t%s\t%s\n' "$name" "$format" "$REPLY"
    done
  done
)
