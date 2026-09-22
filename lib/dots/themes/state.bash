# Bounded theme-state publisher. It never installs or replaces application configs.
# flock releases the lock even after SIGKILL. sync -f is a required mutation capability.
dt_flush() { sync -f "$1"; }
dt_record() {
  printf '%s\n' "$2" > "$1/.status.new" && dt_flush "$1/.status.new" &&
    mv -f -- "$1/.status.new" "$1/status" && dt_flush "$1"
}
dt_restore() {
  local dir=$1 previous active=''
  IFS= read -r previous < "$dir/previous" || return 1
  [[ ! -e $DT_STATE/current ]] || IFS= read -r active < "$DT_STATE/current" || return 1
  if [[ $active == "${dir##*/}" ]]; then
    if [[ $previous == none ]]; then rm -- "$DT_STATE/current" || return
    else printf '%s\n' "$previous" > "$DT_STATE/.current.new" && dt_flush "$DT_STATE/.current.new" && mv -f -- "$DT_STATE/.current.new" "$DT_STATE/current" || return; fi
    dt_flush "$DT_STATE" || return
  elif [[ ${active:-none} != "$previous" ]]; then
    dt_error "selection changed during recovery; retained journal: $dir"; return 1
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
  for part in flock sync sha256sum mktemp awk cat mkdir mv rm; do command -v "$part" >/dev/null || { dt_error "theme switching requires $part"; return 1; }; done
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
  mkdir -p -- "$DT_STATE/generations" || exit 1
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
    if [[ $stored == "$fingerprint" && $selected == "$DT_THEME-$DT_FLAVOR" ]]; then
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
  dt_fingerprint || exit 1
  [[ $REPLY == "$fingerprint" ]] || { dt_error 'theme inputs changed during preparation; retry'; exit 1; }
  local file
  for file in "$dir"/*; do dt_flush "$file" || exit 1; done
  dt_flush "$dir" && dt_flush "$DT_STATE/generations" || exit 1
  dt_record "$dir" prepared || exit 1
  trap 'rc=$?; if (( ! complete )); then dt_restore "$dir" || dt_error "recovery required: $dir"; fi; exit "$rc"' EXIT
  trap 'exit 130' INT
  trap 'exit 143' TERM
  printf '%s\n' "${dir##*/}" > "$dir/active.new" && dt_flush "$dir/active.new" &&
    mv -f -- "$dir/active.new" "$DT_STATE/current" && dt_flush "$DT_STATE" || exit 1
  dt_record "$dir" committed || exit 1
  # shellcheck disable=SC2034
  complete=1
  dots::success "Selected $DT_THEME-$DT_FLAVOR (Zsh: next prompt; Neovim: next focus)"
)
