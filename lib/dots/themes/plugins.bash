# The publisher holds FD 9 through this post-commit step. Failures cannot roll it back.
dt_plugins_after_publish() {
  local config=${XDG_CONFIG_HOME:-$HOME/.config}/dots/theme-plugins.json
  [[ -e $config || -L $config ]] || return 0
  local reason=set
  [[ ${DOTS_THEME_REFRESH:-} != 1 ]] || reason=refresh
  dots::progress_stop
  if ! DOTS_THEME_PLUGIN_REASON=$reason python3 -B "$DT_LIB/plugins.py" __automatic; then
    dots::warning 'Theme remains published; retry with dots theme plugins run (or dots theme refresh).'
  fi
  return 0
}
