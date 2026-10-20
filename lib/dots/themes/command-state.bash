# Generated family executables are immutable, owned state. Parent transactions
# record both pointer identities before publication and call restore on rollback.
source "$DT_LIB/families.bash"
source "$DT_LIB/../verbose.bash"
DT_COMMANDS=$DT_STATE/commands
dt_commands_record() {
  printf '%s\n' "$2" > "$1/.status.new" && sync -f "$1/.status.new" &&
    mv -f -- "$1/.status.new" "$1/status" && sync -f "$1"
}
dt_commands_valid_target() {
  [[ $1 == "$DT_COMMANDS/generations/c."* && ${1##*/} =~ ^c\.[a-zA-Z0-9]+$ && -d $1 && ! -L $1 ]]
}
dt_commands_verify() {
  local dir=$1 file hash relative count=0
  [[ -d $dir/bin && ! -L $dir/bin ]] || return 1
  [[ -f $dir/manifest && ! -L $dir/manifest && -f $dir/fingerprint && ! -L $dir/fingerprint ]] || return 1
  while IFS=' ' read -r hash relative; do
    relative=${relative# }
    [[ $hash =~ ^[a-f0-9]{64}$ && ( $relative =~ ^bin/[a-z][a-z0-9_-]*$ || $relative == names || $relative == init.bash || $relative == init.zsh || $relative == init.fish ) ]] || return 1
    [[ -f $dir/$relative && ! -L $dir/$relative ]] || return 1
    [[ $relative != bin/* || -x $dir/$relative ]] || return 1
    ((++count))
  done < "$dir/manifest"
  ((count >= 4)) || return 1
  # Refuse extra files as well as modified generated data.
  local actual signature
  signature=$(sha256sum -- "$dir/manifest") || return
  [[ $(<"$dir/fingerprint") == "${signature%% *}" ]] || return 1
  [[ $(find "$dir" -type d | wc -l) == 2 ]] || return 1
  actual=$(find "$dir" -mindepth 1 ! -type d | wc -l) || return
  ((actual == count+2)) || return 1
  (cd -- "$dir" && sha256sum -c --status manifest) || return
}
dt_commands_restore() {
  local journal=$1 old new current='' staged
  [[ -f $journal/commands-new ]] || return 0
  IFS= read -r old < "$journal/commands-old" || return
  IFS= read -r new < "$journal/commands-new" || return
  dt_commands_valid_target "$new" || return 1
  [[ $old == none ]] || dt_commands_valid_target "$old" || return 1
  if [[ -L $DT_COMMANDS/current ]]; then current=$(readlink -- "$DT_COMMANDS/current")
  elif [[ -e $DT_COMMANDS/current ]]; then dt_error 'generated command pointer is not managed'; return 1; fi
  if [[ -e $DT_COMMANDS/.current.new || -L $DT_COMMANDS/.current.new ]]; then
    [[ -L $DT_COMMANDS/.current.new ]] || return 1
    staged=$(readlink -- "$DT_COMMANDS/.current.new")
    [[ $staged == "$new" || $staged == "$old" ]] || return 1
    rm -- "$DT_COMMANDS/.current.new" || return
  fi
  if [[ $current == "$new" ]]; then
    dt_commands_verify "$new" || { dt_error 'generated commands changed; refusing rollback'; return 1; }
    if [[ $old == none ]]; then rm -- "$DT_COMMANDS/current" || return
    else
      dt_commands_verify "$old" || return
      ln -s -- "$old" "$DT_COMMANDS/.current.new" && mv -Tf -- "$DT_COMMANDS/.current.new" "$DT_COMMANDS/current" || return
    fi
    sync -f "$DT_COMMANDS" || return
  elif [[ ${current:-none} != "$old" ]]; then dt_error 'generated command pointer drift'; return 1; fi
  if [[ -L $DT_COMMANDS/.current.new ]]; then
    [[ $(readlink -- "$DT_COMMANDS/.current.new") == "$new" ]] || return 1
    rm -- "$DT_COMMANDS/.current.new" || return
  fi
}
dt_commands_lock() {
  local path=$DT_COMMANDS part base='' journal status
  [[ $path == /* && $path != *$'\n'* ]] || return 1
  local -a parts=()
  IFS=/ read -r -a parts <<< "$path/generations"
  for part in "${parts[@]}"; do
    [[ $part ]] || continue
    [[ $part != . && $part != .. ]] || return 1
    base+=/$part
    [[ ! -L $base && ( ! -e $base || -d $base ) ]] || { dt_error "unsafe command state: $base"; return 1; }
  done
  [[ ! -L $DT_COMMANDS/lock && ( ! -e $DT_COMMANDS/lock || -f $DT_COMMANDS/lock ) ]] || return 1
  mkdir -p -- "$DT_COMMANDS/generations" || return
  exec 8>>"$DT_COMMANDS/lock"
  flock -n 8 || { dt_error 'another theme command publication is running'; return 1; }
  # Standalone command-only publications have their own durable journals.
  for journal in "$DT_COMMANDS"/generations/c.*; do
    [[ -f $journal/status && ! -L $journal/status ]] || continue
    IFS= read -r status < "$journal/status" || return
    [[ $status != prepared ]] || { dt_commands_restore "$journal" && dt_commands_record "$journal" rolled-back || return; }
  done
}
dt_commands_prepare() {
  local journal=$1 dir old=none family file signature existing pending status
  for pending in "$DT_STATE"/generations/g.* "$DT_USER_THEMES"/.transactions/t.*; do
    [[ $pending != "$journal" && -f $pending/status ]] || continue
    IFS= read -r status < "$pending/status" || return
    [[ $status != prepared ]] || { dt_error "unfinished theme transaction; recover it first: $pending"; return 1; }
  done
  [[ ! -e $DT_COMMANDS/.current.new && ! -L $DT_COMMANDS/.current.new ]] || { dt_error 'stale command staging pointer'; return 1; }
  if [[ -e $DT_COMMANDS/current || -L $DT_COMMANDS/current ]]; then
    [[ -L $DT_COMMANDS/current ]] || return 1
    old=$(readlink -- "$DT_COMMANDS/current")
    dt_commands_valid_target "$old" && dt_commands_verify "$old" || { dt_error 'generated commands changed; retained for inspection'; return 1; }
  fi
  dt_family_index || return
  dir=$(mktemp -d "$DT_COMMANDS/generations/c.XXXXXXXX") || return
  mkdir "$dir/bin" || return
  : > "$dir/names"
  printf '# Generated Dots family completions.\n' | tee "$dir/init.bash" "$dir/init.zsh" > "$dir/init.fish"
  while IFS= read -r family; do
    [[ $family ]] || continue
    if dt_family_reserved "$family"; then
      printf 'dots theme: reserved command %s; use explicit full-ID routes\n' "$family" >&2
      continue
    fi
    existing=$(command -v -- "$family" || :)
    case $existing in ''|"$DT_COMMANDS/current/bin/"*|"$DT_ROOT/bin/"*) ;; *) printf 'dots theme: existing command %s keeps PATH precedence\n' "$family" >&2 ;; esac
    printf '%s\n' "$family" >> "$dir/names"
    printf '#!/usr/bin/env bash\nexec %q theme %q "$@"\n' "${DT_LIB%/lib/dots/themes}/bin/dots" "$family" > "$dir/bin/$family" || return
    chmod 700 "$dir/bin/$family" || return
    printf 'complete -F _dots_complete_bash -- %q\n' "$family" >> "$dir/init.bash"
    printf 'compdef _dots %q\n' "$family" >> "$dir/init.zsh"
    printf "complete -c '%s' -f -a '(__dots_complete_fish)'\n" "$family" >> "$dir/init.fish"
  done < <(printf '%s\n' "${DT_FAMILIES[@]}" | LC_ALL=C sort)
  (cd -- "$dir" && find bin -type f -print | LC_ALL=C sort | while IFS= read -r file; do sha256sum -- "$file"; done
   sha256sum -- names init.bash init.zsh init.fish) > "$dir/manifest" || return
  signature=$(sha256sum -- "$dir/manifest") || return
  printf '%s\n' "${signature%% *}" > "$dir/fingerprint"
  if [[ $old != none ]] && cmp -s -- "$old/manifest" "$dir/manifest"; then
    # Unpublished, testable staging only; no user target can live in this directory.
    rm -r -- "$dir" || return
    return 0
  fi
  while IFS= read -r -d '' file; do sync -f "$file" || return; done < <(find "$dir" -type f -print0)
  sync -f "$dir/bin" && sync -f "$dir" && sync -f "$DT_COMMANDS/generations" || return
  printf '%s\n' "$old" > "$journal/commands-old"
  printf '%s\n' "$dir" > "$journal/commands-new"
  sync -f "$journal/commands-old" && sync -f "$journal/commands-new" && sync -f "$journal"
}
dt_commands_publish() {
  local journal=$1 new old current=none
  [[ -f $journal/commands-new ]] || return 0
  IFS= read -r new < "$journal/commands-new"; IFS= read -r old < "$journal/commands-old"
  [[ ! -L $DT_COMMANDS/current ]] || current=$(readlink -- "$DT_COMMANDS/current")
  [[ $current == "$old" && ( ! -e $DT_COMMANDS/current || -L $DT_COMMANDS/current ) ]] || { dt_error 'generated command pointer changed'; return 1; }
  dt_commands_verify "$new" || return
  ln -s -- "$new" "$DT_COMMANDS/.current.new" && mv -Tf -- "$DT_COMMANDS/.current.new" "$DT_COMMANDS/current" && sync -f "$DT_COMMANDS" || return
  dots::operation Linked "$new" "$DT_COMMANDS/current" 'Generated theme commands' dir symlink
}
dt_commands_refresh() (
  umask 077
  # Read by the shared progress helpers.
  # shellcheck disable=SC2034
  local DOTS_PROGRESS_HUMAN=${DOTS_OPERATION_VERBOSE:-0} DOTS_PROGRESS_STARTED=''
  trap 'dots::progress_stop' EXIT
  dots::progress_start 'Refreshing theme commands'
  dt_commands_lock && dt_commands_refresh_locked
)
dt_commands_refresh_locked() (
  umask 077
  # Journal directories are separate from generated payload directories.
  local journal
  journal=$(mktemp -d "$DT_COMMANDS/generations/c.XXXXXXXX") || exit
  dt_commands_prepare "$journal" || exit
  if [[ ! -f $journal/commands-new ]]; then
    rmdir -- "$journal" || exit
    dots::operation Unchanged "$DT_COMMANDS/current" '' 'Generated commands already match'
    exit 0
  fi
  dt_commands_record "$journal" prepared || exit
  trap 'dt_commands_restore "$journal"' EXIT
  trap 'exit 130' INT
  trap 'exit 143' TERM
  dt_commands_publish "$journal" && dt_commands_record "$journal" committed || exit
  dots::operation Published "$DT_COMMANDS/current" '' 'Theme commands'
  trap - EXIT
)
