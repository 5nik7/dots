# Bounded theme-state publisher and journaled application connector links.
# shellcheck source=apps.bash
source "$DT_LIB/apps.bash"
# flock releases the lock even after SIGKILL. sync -f is a required mutation capability.
dt_flush() { sync -f "$1"; }
dt_record() {
  printf '%s\n' "$2" > "$1/.status.new" && dt_flush "$1/.status.new" &&
    mv -f -- "$1/.status.new" "$1/status" && dt_flush "$1"
}
dt_restore() {
  local dir=$1 previous active=''
  if [[ -L $DT_ACTIVE.new && $(readlink -- "$DT_ACTIVE.new") == "$dir" ]]; then
    rm -- "$DT_ACTIVE.new" || return
  fi
  IFS= read -r previous < "$dir/previous" || return 1
  [[ ! -e $DT_STATE/current ]] || IFS= read -r active < "$DT_STATE/current" || return 1
  if [[ $active == "${dir##*/}" ]]; then
    if [[ $previous == none ]]; then rm -- "$DT_STATE/current" || return
    else printf '%s\n' "$previous" > "$DT_STATE/.current.new" && dt_flush "$DT_STATE/.current.new" && mv -f -- "$DT_STATE/.current.new" "$DT_STATE/current" || return; fi
    dt_flush "$DT_STATE" || return
  elif [[ ${active:-none} != "$previous" ]]; then
    dt_error "selection changed during recovery; retained journal: $dir"; return 1
  fi
  dt_apps_restore "$dir" || return
  if [[ -L $DT_ACTIVE && $(readlink -- "$DT_ACTIVE") == "$dir" ]]; then
    if [[ -s $dir/previous-active ]]; then
      IFS= read -r active < "$dir/previous-active"
      ln -s -- "$active" "$DT_ACTIVE.new" && mv -Tf -- "$DT_ACTIVE.new" "$DT_ACTIVE" || return
    else rm -- "$DT_ACTIVE" || return; fi
    dt_flush "${DT_ACTIVE%/*}" || return
  elif [[ -f $dir/previous-active ]]; then
    IFS= read -r active < "$dir/previous-active" || active=''
    if [[ $active ]]; then
      [[ -L $DT_ACTIVE && $(readlink -- "$DT_ACTIVE") == "$active" ]] || { dt_error 'active theme drift during recovery'; return 1; }
    else
      [[ ! -e $DT_ACTIVE && ! -L $DT_ACTIVE ]] || { dt_error 'active theme appeared during recovery'; return 1; }
    fi
  fi
  dt_record "$dir" rolled-back
}
dt_recover() {
  local dir status
  for dir in "$DT_STATE"/generations/g.*; do
    [[ -d $dir && ! -L $dir ]] || continue
    # A directory without a prepared journal cannot have been activated.
    [[ -f $dir/status && ! -L $dir/status ]] || continue
    IFS= read -r status < "$dir/status" || return
    case $status in
      committed|rolled-back) ;;
      prepared) dt_restore "$dir" || return ;;
      *) dt_error "unknown journal status: $dir"; return 1 ;;
    esac
  done
}
dt_state_preflight() {
  local path=$DT_STATE part base=''
  [[ $path == /* && $path != / && $path != *$'\n'* ]] || { dt_error 'theme state root must be an absolute path'; return 1; }
  # Classify each existing ancestor; never follow a state path through a symlink.
  local -a parts=()
  IFS=/ read -r -a parts <<< "$path/generations"
  for part in "${parts[@]}"; do
    [[ $part ]] || continue
    [[ $part != . && $part != .. ]] || { dt_error 'state path contains dot components'; return 1; }
    base+=/$part
    [[ ! -L $base && ( ! -e $base || -d $base ) ]] || { dt_error "unsafe state directory: $base"; return 1; }
  done
  for part in current lock .current.new; do
    path=$DT_STATE/$part
    [[ ! -L $path && ( ! -e $path || -f $path ) ]] || { dt_error "unsafe state file: $path"; return 1; }
  done
  [[ ! -e $DT_STATE/.current.new ]] || { dt_error 'stale selection staging file requires inspection'; return 1; }
  path=${DT_ACTIVE%/*}
  [[ ! -L $path && ( ! -e $path || -d $path ) ]] || { dt_error 'unsafe active theme parent'; return 1; }
  if [[ -e $DT_ACTIVE || -L $DT_ACTIVE ]]; then
    [[ -L $DT_ACTIVE && $(readlink -- "$DT_ACTIVE") == "$DT_STATE/generations/g."* ]] || { dt_error 'active theme is not a managed link'; return 1; }
  fi
  if [[ -e $DT_ACTIVE.new || -L $DT_ACTIVE.new ]]; then
    local staged status
    [[ -L $DT_ACTIVE.new ]] || { dt_error 'unknown active staging object'; return 1; }
    staged=$(readlink -- "$DT_ACTIVE.new")
    [[ $staged == "$DT_STATE/generations/g."* && -f $staged/status ]] || return 1
    IFS= read -r status < "$staged/status"
    [[ $status == prepared ]] || { dt_error 'unknown active staging journal'; return 1; }
  fi
  dt_apps_plan || return
  for part in flock sync sha256sum mktemp awk cat mkdir mv rm cp ln readlink cmp; do command -v "$part" >/dev/null || { dt_error "theme switching requires $part"; return 1; }; done
}
dt_set() (
  set -o pipefail
  umask 077
  # complete and rc are read by the EXIT trap.
  # shellcheck disable=SC2034
  local theme=$1 flavor=${2:-} dir='' complete=0 rc=0 previous fingerprint stored=''
  dt_load "$theme" "$flavor" || exit 1
  dt_supported || { dt_error 'theme/flavor has no supported Neovim adapter'; exit 1; }
  if [[ $DT_THEME == catppuccin ]]; then
    local target_flavor=$DT_FLAVOR candidate
    for candidate in mocha macchiato frappe latte; do dt_load "$theme" "$candidate" || exit 1; done
    dt_load "$theme" "$target_flavor" || exit 1
  fi
  dt_fingerprint || exit 1; fingerprint=$REPLY
  dt_state_preflight || exit 1
  mkdir -p -- "$DT_STATE/generations" "${DT_ACTIVE%/*}" || exit 1
  dt_flush "$DT_STATE" || { dt_error 'sync -f is required for durable theme switching'; exit 1; }
  exec 9>>"$DT_STATE/lock" || exit 1
  flock -n 9 || { dt_error 'another theme switch is running'; exit 1; }
  dt_recover || exit 1
  dt_generation || exit 1
  previous=${DT_GENERATION:-none}
  if [[ $DT_GENERATION ]]; then
    IFS= read -r stored < "$DT_STATE/generations/$DT_GENERATION/fingerprint" || exit 1
    local selected
    IFS= read -r selected < "$DT_STATE/generations/$DT_GENERATION/selection" || exit 1
    if [[ $stored == "$fingerprint" && $selected == "$DT_THEME-$DT_FLAVOR" ]] && dt_apps_current; then
      if [[ ${DOTS_THEME_REFRESH:-} == 1 ]]; then dt_apps_reload; fi
      dots::success "Already using $selected"; exit 0
    fi
  fi
  dir=$(mktemp -d "$DT_STATE/generations/g.XXXXXXXX") || exit 1
  # Staging files are confined to a newly allocated transaction directory.
  printf '%s\n' "$previous" > "$dir/previous" &&
    printf '%s\n' "$fingerprint" > "$dir/fingerprint" &&
    printf '%s-%s\n' "$DT_THEME" "$DT_FLAVOR" > "$dir/selection" &&
    dt_json > "$dir/palette.json" &&
    dt_emit_init zsh > "$dir/init.zsh" &&
    dt_emit_init fish > "$dir/init.fish" || exit 1
  if [[ -n ${DT_SEMANTIC[background]:-} ]]; then
    dt_render "$dir" || exit 1
  fi
  if [[ -f $dir/bat.tmTheme ]] && command -v bat >/dev/null; then
    mkdir -p "$dir/bat-source/themes" "$dir/bat-cache" || exit 1
    cp -- "$dir/bat.tmTheme" "$dir/bat-source/themes/Dots.tmTheme" || exit 1
    (cd -- "$dir/bat-source" && BAT_CONFIG_PATH=/dev/null BAT_THEME=ansi BAT_CONFIG_DIR="$dir/bat-source" BAT_CACHE_PATH="$dir/bat-cache" bat cache --build --source "$dir/bat-source" --target "$dir/bat-cache" >/dev/null) || { dt_error 'bat theme cache build failed'; exit 1; }
    printf 'export BAT_THEME=Dots BAT_CACHE_PATH=%q\n' "$dir/bat-cache" >> "$dir/init.zsh"
    local fish_cache=$dir/bat-cache
    fish_cache=${fish_cache//\\/\\\\}; fish_cache=${fish_cache//\'/\\\'}
    printf "set -gx BAT_THEME Dots\nset -gx BAT_CACHE_PATH '%s'\n" "$fish_cache" >> "$dir/init.fish"
  fi
  if [[ -L $DT_ACTIVE ]]; then readlink -- "$DT_ACTIVE" > "$dir/previous-active"; else : > "$dir/previous-active"; fi
  dt_fingerprint || exit 1
  [[ $REPLY == "$fingerprint" ]] || { dt_error 'theme inputs changed during preparation; retry'; exit 1; }
  local file
  while IFS= read -r -d '' file; do dt_flush "$file" || exit 1; done < <(find "$dir" -type f -print0)
  dt_flush "$dir" && dt_flush "$DT_STATE/generations" || exit 1
  dt_record "$dir" prepared || exit 1
  trap 'rc=$?; if (( ! complete )); then dt_restore "$dir" || dt_error "recovery required: $dir"; fi; exit "$rc"' EXIT
  trap 'exit 130' INT
  trap 'exit 143' TERM
  printf '%s\n' "${dir##*/}" > "$dir/active.new" && dt_flush "$dir/active.new" &&
    mv -f -- "$dir/active.new" "$DT_STATE/current" && dt_flush "$DT_STATE" || exit 1
  if [[ -f $dir/kitty.conf ]]; then
    ln -s -- "$dir" "$DT_ACTIVE.new" && mv -Tf -- "$DT_ACTIVE.new" "$DT_ACTIVE" && dt_flush "${DT_ACTIVE%/*}" || exit 1
    dt_apps_connect "$dir" || exit 1
  fi
  dt_record "$dir" committed || exit 1
  # shellcheck disable=SC2034
  complete=1
  dt_apps_reload
  dots::success "Selected $DT_THEME-$DT_FLAVOR (Zsh: next prompt; Neovim: next focus)"
)
