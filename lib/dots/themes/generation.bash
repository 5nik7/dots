# Read-only completeness checks for publication, never shell startup.
# REPLY identifies the first missing/unsafe artifact or publication pointer.
dt_generation_complete() {
  local dir=$1 file template _app _suffix artifact
  local -a required=(id selection fingerprint palette.json shell.tsv init.zsh init.fish)
  REPLY=$dir
  [[ -d $dir && ! -L $dir ]] || return 1
  if [[ -n ${DT_SEMANTIC[background]:-} ]]; then
    required+=(colors.json colors.lua ls_colors file-styles.tsv git-styles.tsv
               yazi/flavor.toml yazi/tmtheme.xml)
    # Use the same effective template roots and connector registry as rendering.
    for template in "$DT_USER_TEMPLATES/"*.tpl "$DT_TEMPLATES/"*.tpl; do
      [[ -f $template && ! -L $template ]] || continue
      file=${template##*/}; required+=("${file%.tpl}")
    done
    while IFS=$'\t' read -r _app _suffix artifact; do
      if [[ $artifact == yazi ]]; then continue; fi
      required+=("$artifact")
    done < "$DT_LIB/connectors.tsv"
    REPLY=$dir/yazi
    [[ -d $REPLY && ! -L $REPLY ]] || return 1
  fi
  for file in "${required[@]}"; do
    REPLY=$dir/$file
    [[ -f $REPLY && -r $REPLY && ! -L $REPLY ]] || return 1
  done
  REPLY=''
}
dt_generation_current() {
  local dir=$1 selected
  dt_generation_complete "$dir" || return
  REPLY=$DT_STATE/current
  [[ -f $REPLY && ! -L $REPLY ]] && IFS= read -r selected < "$REPLY" &&
    [[ $selected == "${dir##*/}" ]] || return 1
  REPLY=${XDG_STATE_HOME:-$HOME/.local/state}/dots/current/theme
  [[ -L $REPLY && $REPLY -ef $dir ]] || return 1
  REPLY=''
}
