# The publisher holds FD 9 through this post-commit step. Failures cannot roll it back.
dt_plugins_after_publish() {
  local config
  config=$(python3 -B "${DT_LIB%/themes}/profile_config.py" __path theme-plugins.json) || return
  if [[ ! -e $config && ! -L $config ]]; then
    dots::operation Skipped '' '' 'No theme plugins configured'
    return 0
  fi
  local reason=set
  [[ ${DOTS_THEME_REFRESH:-} != 1 ]] || reason=refresh
  dots::progress_stop
  if ! DOTS_THEME_PLUGIN_REASON=$reason python3 -B "$DT_LIB/plugins.py" __automatic; then
    dots::operation Failed '' '' 'Theme plugin step; theme remains published'
    dots::warning 'Theme remains published; retry with dots theme plugins run (or dots theme refresh).'
  else
    dots::operation Completed '' '' 'Theme plugin step'
  fi
  return 0
}
