# Narrow, journaled theme connector links. No app is installed or restarted.
DT_ACTIVE=${XDG_STATE_HOME:-$HOME/.local/state}/dots/current/theme
declare -ga DT_CONNECT_TARGETS=() DT_CONNECT_SOURCES=()
declare -gA DT_CONNECT_CREATE_DIRS=()
dt_connector_staging_owned() {
  local target=$1 entry recorded source status
  [[ -L $target.dots-theme-new ]] || return 1
  for entry in "$DT_STATE"/generations/g.*/connectors/*; do
    [[ -f $entry/target && -f $entry/source && -f $entry/../../status ]] || continue
    IFS= read -r status < "$entry/../../status"
    [[ $status == prepared ]] || continue
    IFS= read -r recorded < "$entry/target"; IFS= read -r source < "$entry/source"
    [[ $target == "$recorded" && $(readlink -- "$target.dots-theme-new") == "$source" ]] && return 0
  done
  return 1
}
dt_apps_plan() {
  DT_CONNECT_TARGETS=() DT_CONNECT_SOURCES=()
  DT_CONNECT_CREATE_DIRS=()
  local config=${XDG_CONFIG_HOME:-$HOME/.config} path name
  local codex_home=${CODEX_HOME:-$HOME/.codex}
  [[ $codex_home == /* && ! $codex_home =~ [[:cntrl:]] && /$codex_home/ != */../* && /$codex_home/ != */./* ]] || {
    dt_error 'Codex home must be an absolute path without control characters or dot components'; return 1;
  }
  local pi_agent=${PI_CODING_AGENT_DIR:-$HOME/.pi/agent}
  case $pi_agent in
    \~) pi_agent=$HOME ;;
    \~/*) pi_agent=$HOME/${pi_agent#\~/} ;;
  esac
  [[ $pi_agent == /* && $pi_agent != *$'\n'* && /$pi_agent/ != */../* && /$pi_agent/ != */./* ]] || {
    dt_error 'Pi agent directory must be an absolute path without dot components'; return 1;
  }
  local eza_config television_config leaf_config app_config parent
  eza_config=$(python3 -B "$DT_LIB/../files/app_paths.py" eza) || return
  television_config=$(python3 -B "$DT_LIB/../files/app_paths.py" television) || return
  leaf_config=$(python3 -B "$DT_LIB/../files/app_paths.py" leaf) || return
  local suffix artifact
  while IFS=$'\t' read -r name suffix artifact; do
    path=$config/$name/$suffix
    [[ $name != eza ]] || path=$eza_config/$suffix
    if [[ $name == television || $name == leaf ]]; then
      app_config=$television_config
      [[ $name != leaf ]] || app_config=$leaf_config
      [[ -n $app_config && -d $app_config ]] || continue
      path=$app_config/$suffix
      parent=${path%/*}
      [[ ! -L $parent && ( ! -e $parent || -d $parent ) ]] || { dt_error "unsafe $name themes directory"; return 1; }
      if [[ ! -d $parent ]]; then DT_CONNECT_CREATE_DIRS[$parent]=1; fi
    fi
    [[ -d ${path%/*} || ${DT_CONNECT_CREATE_DIRS[${path%/*}]:-} ]] || continue
    [[ ! -e $path || -f $path || -L $path ]] || { dt_error "cannot connect theme target: $path"; return 1; }
    DT_CONNECT_TARGETS+=("$path") DT_CONNECT_SOURCES+=("$DT_ACTIVE/$artifact")
  done < "$DT_LIB/connectors.tsv"
  if [[ -d $HOME/.termux ]]; then
    path=$HOME/.termux/colors.properties
    [[ ! -e $path || -f $path || -L $path ]] || return 1
    DT_CONNECT_TARGETS+=("$path") DT_CONNECT_SOURCES+=("$DT_ACTIVE/termux.properties")
  fi
  if [[ -d $pi_agent/themes ]]; then
    path=$pi_agent/themes/dots.json
    [[ ! -e $path || -f $path || -L $path ]] || { dt_error "cannot connect theme target: $path"; return 1; }
    DT_CONNECT_TARGETS+=("$path") DT_CONNECT_SOURCES+=("$DT_ACTIVE/pi.json")
  fi
  if [[ -d $codex_home/themes ]]; then
    path=$codex_home/themes/dots.tmTheme
    [[ ! -e $path || -f $path || -L $path ]] || { dt_error "cannot connect theme target: $path"; return 1; }
    DT_CONNECT_TARGETS+=("$path") DT_CONNECT_SOURCES+=("$DT_ACTIVE/bat.tmTheme")
  fi
  for path in "${DT_CONNECT_TARGETS[@]}"; do
    parent=${path%/*}
    [[ ! ${DT_CONNECT_CREATE_DIRS[$parent]:-} ]] || parent=${parent%/*}
    [[ $path != *$'\n'* && -w $parent ]] || { dt_error 'unsafe or unwritable connector'; return 1; }
    if [[ -e $path.dots-theme-new || -L $path.dots-theme-new ]]; then
      dt_connector_staging_owned "$path" || { dt_error 'unknown connector staging object'; return 1; }
    fi
  done
}
dt_apps_connect() {
  local dir=$1 index target source entry parent
  mkdir "$dir/connectors" || return
  for ((index=0;index<${#DT_CONNECT_TARGETS[@]};index++)); do
    target=${DT_CONNECT_TARGETS[index]} source=${DT_CONNECT_SOURCES[index]}
    # Pi watches its themes directory, not the active generation link. Renew its
    # connector on publication to notify that watcher, using the same journal.
    if [[ $source != "$DT_ACTIVE/pi.json" && -L $target && $(readlink -- "$target") == "$source" ]]; then
      dots::operation Unchanged "$target" '' 'Already linked'
      continue
    fi
    entry=$dir/connectors/$index; mkdir "$entry" || return
    printf '%s\n' "$target" > "$entry/target"
    printf '%s\n' "$source" > "$entry/source"
    if [[ -L $target || -e $target ]]; then
      cp -a -- "$target" "$entry/old" || return
      printf 'present\n' > "$entry/prior"
    else printf 'absent\n' > "$entry/prior"; fi
    local saved
    for saved in target source prior; do dt_flush "$entry/$saved" || return; done
    [[ ! -f $entry/old || -L $entry/old ]] || dt_flush "$entry/old" || return
    dt_flush "$entry" && dt_flush "$dir" || return
    parent=${target%/*}
    if [[ ${DT_CONNECT_CREATE_DIRS[$parent]:-} ]]; then
      [[ ! -e $parent && ! -L $parent ]] || { dt_error 'connector parent appeared during preparation'; return 1; }
      printf '%s\n' "$parent" > "$entry/parent-intent"
      dt_flush "$entry/parent-intent" && dt_flush "$entry" || return
      mkdir -- "$parent" || return
      stat -c '%d:%i' -- "$parent" > "$entry/parent-identity" || return
      dt_flush "$entry/parent-identity" && dt_flush "$entry" && dt_flush "${parent%/*}" || return
      # Several artifacts may share this newly created application directory.
      unset 'DT_CONNECT_CREATE_DIRS[$parent]'
    fi
    if [[ -L $entry/old ]]; then
      [[ -L $target && $(readlink -- "$target") == "$(readlink -- "$entry/old")" ]] || { dt_error 'connector changed during preparation'; return 1; }
    elif [[ -f $entry/old ]]; then
      [[ -f $target && ! -L $target ]] && cmp -s -- "$target" "$entry/old" || { dt_error 'connector changed during preparation'; return 1; }
    else
      [[ ! -e $target && ! -L $target ]] || { dt_error 'connector appeared during preparation'; return 1; }
    fi
    if [[ -e $entry/old || -L $entry/old ]]; then
      dots::operation 'Recovery copy' "$target" "$entry/old" 'Retained in the theme generation journal'
    fi
    ln -s -- "$source" "$target.dots-theme-new" || return
    mv -Tf -- "$target.dots-theme-new" "$target" && dt_flush "${target%/*}" || return
    dots::operation Linked "$source" "$target" '' file symlink
  done
}
dt_apps_current() {
  local index
  for ((index=0;index<${#DT_CONNECT_TARGETS[@]};index++)); do
    [[ -L ${DT_CONNECT_TARGETS[index]} && $(readlink -- "${DT_CONNECT_TARGETS[index]}") == "${DT_CONNECT_SOURCES[index]}" ]] || return 1
  done
}
dt_apps_restore() {
  local dir=$1 entry target source prior parent identity
  local -a entries=("$dir/connectors/"*)
  local index
  for ((index=${#entries[@]}-1;index>=0;index--)); do
    entry=${entries[index]}; [[ -f $entry/target && -f $entry/prior ]] || continue
    IFS= read -r target < "$entry/target"; IFS= read -r source < "$entry/source"; IFS= read -r prior < "$entry/prior"
    if [[ -f $entry/parent-intent ]]; then
      IFS= read -r parent < "$entry/parent-intent"
      if [[ -e $parent || -L $parent ]]; then
        [[ ! -L $parent && -d $parent && -s $entry/parent-identity ]] || { dt_error 'connector parent requires manual recovery'; return 1; }
        IFS= read -r identity < "$entry/parent-identity"
        [[ $(stat -c '%d:%i' -- "$parent") == "$identity" ]] || { dt_error 'connector parent drift during rollback'; return 1; }
      fi
    fi
    if [[ -L $target.dots-theme-new && $(readlink -- "$target.dots-theme-new") == "$source" ]]; then
      rm -- "$target.dots-theme-new" || return
    fi
    if [[ -L $target && $(readlink -- "$target") == "$source" ]]; then
      if [[ $prior == absent ]]; then rm -- "$target" || return
      else cp -a -- "$entry/old" "$target.dots-theme-new" && mv -Tf -- "$target.dots-theme-new" "$target" || return; fi
      dt_flush "${target%/*}" || return
      dots::operation 'Rolled back' "$target" '' 'Original connector state restored'
    elif [[ $prior == present ]]; then
      if [[ -L $entry/old ]]; then [[ -L $target && $(readlink -- "$target") == "$(readlink -- "$entry/old")" ]] || { dt_error "connector drift during rollback: $target"; return 1; }
      else cmp -s -- "$target" "$entry/old" || { dt_error "connector drift during rollback: $target"; return 1; }; fi
    elif [[ -e $target || -L $target ]]; then dt_error "connector drift during rollback: $target"; return 1
    fi
    if [[ -f $entry/parent-intent ]]; then
      IFS= read -r parent < "$entry/parent-intent"
      if [[ -e $parent || -L $parent ]]; then
        [[ ! -L $parent && -d $parent && -s $entry/parent-identity ]] || { dt_error 'connector parent requires manual recovery'; return 1; }
        IFS= read -r identity < "$entry/parent-identity"
        [[ $(stat -c '%d:%i' -- "$parent") == "$identity" ]] || { dt_error 'connector parent drift during rollback'; return 1; }
        # rmdir preserves new user content; never recursively remove a parent.
        rmdir -- "$parent" 2>/dev/null || {
          dt_error "connector parent is not empty; retained: $parent"; return 1;
        }
        dt_flush "${parent%/*}" || return
      fi
    fi
  done
}
dt_apps_reload() {
  dots::progress_start 'Checking application reloads'
  local failures=0
  if [[ ${TERMUX_VERSION:-} && ${PREFIX:-} == */usr && -d $HOME/.termux ]] && command -v termux-reload-settings >/dev/null; then
    dots::progress_update 'Reloading Termux settings'
    if termux-reload-settings >/dev/null 2>&1; then dots::operation Reloaded '' '' 'Termux settings'
    else dt_error 'Termux reload failed'; failures=1; fi
  else
    dots::operation Skipped '' '' 'Termux reload: adapter unavailable'
  fi
  if command -v tmux >/dev/null && tmux list-sessions >/dev/null 2>&1; then
    dots::progress_external 'Reloading tmux configuration'
    if tmux source-file "$DT_ACTIVE/tmux.conf"; then dots::operation Reloaded '' '' 'tmux configuration'
    else dt_error 'tmux reload failed'; failures=1; fi
  else
    dots::operation Skipped '' '' 'tmux reload: no executable or running server'
  fi
  if [[ ${KITTY_LISTEN_ON:-} ]] && command -v kitty >/dev/null; then
    dots::progress_start 'Reloading Kitty colors'
    if kitty @ --to "$KITTY_LISTEN_ON" set-colors --all --configured "$DT_ACTIVE/kitty.conf" >/dev/null 2>&1; then dots::operation Reloaded '' '' 'Kitty colors'
    else dt_error 'Kitty reload failed'; failures=1; fi
  else
    dots::operation Skipped '' '' 'Kitty reload: executable or listening address unavailable'
  fi
  if command -v ya >/dev/null && command -v timeout >/dev/null; then
    if timeout 2 ya pub-to 0 dots-theme-changed --str "${XDG_STATE_HOME:-$HOME/.local/state}/dots" >/dev/null 2>&1; then
      dots::operation Notified '' '' 'Yazi theme event sent'
    else dots::operation Skipped '' '' 'Yazi theme notification unavailable'; fi
  else
    dots::operation Skipped '' '' 'Yazi notification: ya or timeout unavailable'
  fi
  dots::progress_stop
  (( ! failures )) || printf 'Theme is published; retry app reloads with dots theme refresh.\n' >&2
  return 0
}
