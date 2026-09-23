# Narrow, journaled theme connector links. No app is installed or restarted.
DT_ACTIVE=${XDG_STATE_HOME:-$HOME/.local/state}/dots/current/theme
declare -ga DT_CONNECT_TARGETS=() DT_CONNECT_SOURCES=()
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
  local config=${XDG_CONFIG_HOME:-$HOME/.config} path name
  for name in kitty tmux btop yazi; do
    [[ -d $config/$name ]] || continue
    case $name in
      kitty|tmux) path=$config/$name/dots-theme.conf; name=$name.conf ;;
      btop) path=$config/btop/themes/dots.theme; name=btop.theme ;;
      yazi) path=$config/yazi/flavors/dots.yazi; name=yazi ;;
    esac
    [[ -d ${path%/*} && ( ! -e $path || -f $path || -L $path ) ]] || { dt_error "cannot connect theme target: $path"; return 1; }
    DT_CONNECT_TARGETS+=("$path") DT_CONNECT_SOURCES+=("$DT_ACTIVE/$name")
  done
  if [[ -d $HOME/.termux ]]; then
    path=$HOME/.termux/colors.properties
    [[ ! -e $path || -f $path || -L $path ]] || return 1
    DT_CONNECT_TARGETS+=("$path") DT_CONNECT_SOURCES+=("$DT_ACTIVE/termux.properties")
  fi
  for path in "${DT_CONNECT_TARGETS[@]}"; do
    [[ $path != *$'\n'* && -w ${path%/*} ]] || { dt_error 'unsafe or unwritable connector'; return 1; }
    if [[ -e $path.dots-theme-new || -L $path.dots-theme-new ]]; then
      dt_connector_staging_owned "$path" || { dt_error 'unknown connector staging object'; return 1; }
    fi
  done
}
dt_apps_connect() {
  local dir=$1 index target source entry
  mkdir "$dir/connectors" || return
  for ((index=0;index<${#DT_CONNECT_TARGETS[@]};index++)); do
    target=${DT_CONNECT_TARGETS[index]} source=${DT_CONNECT_SOURCES[index]}
    if [[ -L $target && $(readlink -- "$target") == "$source" ]]; then continue; fi
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
    if [[ -L $entry/old ]]; then
      [[ -L $target && $(readlink -- "$target") == "$(readlink -- "$entry/old")" ]] || { dt_error 'connector changed during preparation'; return 1; }
    elif [[ -f $entry/old ]]; then
      [[ -f $target && ! -L $target ]] && cmp -s -- "$target" "$entry/old" || { dt_error 'connector changed during preparation'; return 1; }
    else
      [[ ! -e $target && ! -L $target ]] || { dt_error 'connector appeared during preparation'; return 1; }
    fi
    ln -s -- "$source" "$target.dots-theme-new" || return
    mv -Tf -- "$target.dots-theme-new" "$target" && dt_flush "${target%/*}" || return
  done
}
dt_apps_current() {
  local index
  for ((index=0;index<${#DT_CONNECT_TARGETS[@]};index++)); do
    [[ -L ${DT_CONNECT_TARGETS[index]} && $(readlink -- "${DT_CONNECT_TARGETS[index]}") == "${DT_CONNECT_SOURCES[index]}" ]] || return 1
  done
}
dt_apps_restore() {
  local dir=$1 entry target source prior
  local -a entries=("$dir/connectors/"*)
  local index
  for ((index=${#entries[@]}-1;index>=0;index--)); do
    entry=${entries[index]}; [[ -f $entry/target && -f $entry/prior ]] || continue
    IFS= read -r target < "$entry/target"; IFS= read -r source < "$entry/source"; IFS= read -r prior < "$entry/prior"
    if [[ -L $target.dots-theme-new && $(readlink -- "$target.dots-theme-new") == "$source" ]]; then
      rm -- "$target.dots-theme-new" || return
    fi
    if [[ -L $target && $(readlink -- "$target") == "$source" ]]; then
      if [[ $prior == absent ]]; then rm -- "$target" || return
      else cp -a -- "$entry/old" "$target.dots-theme-new" && mv -Tf -- "$target.dots-theme-new" "$target" || return; fi
      dt_flush "${target%/*}" || return
    elif [[ $prior == present ]]; then
      if [[ -L $entry/old ]]; then [[ -L $target && $(readlink -- "$target") == "$(readlink -- "$entry/old")" ]] || { dt_error "connector drift during rollback: $target"; return 1; }
      else cmp -s -- "$target" "$entry/old" || { dt_error "connector drift during rollback: $target"; return 1; }; fi
    elif [[ -e $target || -L $target ]]; then dt_error "connector drift during rollback: $target"; return 1
    fi
  done
}
dt_apps_reload() {
  local failures=0
  if [[ ${TERMUX_VERSION:-} && ${PREFIX:-} == */usr && -d $HOME/.termux ]] && command -v termux-reload-settings >/dev/null; then
    termux-reload-settings >/dev/null 2>&1 || { dt_error 'Termux reload failed'; failures=1; }
  fi
  if command -v tmux >/dev/null && tmux list-sessions >/dev/null 2>&1; then
    tmux source-file "$DT_ACTIVE/tmux.conf" || { dt_error 'tmux reload failed'; failures=1; }
  fi
  if [[ ${KITTY_LISTEN_ON:-} ]] && command -v kitty >/dev/null; then
    kitty @ --to "$KITTY_LISTEN_ON" set-colors --all --configured "$DT_ACTIVE/kitty.conf" >/dev/null 2>&1 || { dt_error 'Kitty reload failed'; failures=1; }
  fi
  (( ! failures )) || printf 'Theme is published; retry app reloads with dots theme refresh.\n' >&2
  return 0
}
