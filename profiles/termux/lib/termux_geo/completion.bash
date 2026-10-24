# shellcheck shell=bash disable=SC2154,SC2034
geo_completion_source() {
  local line
  while IFS= read -r line || [[ $line ]]; do
    line=${line//@FIELDS@/$GEO_FIELDS lat lon zip}
    line=${line//@OPTIONS@/$GEO_OPTIONS}
    printf '%s\n' "$line"
  done < "$GEO_ROOT/lib/termux_geo/completions/$1"
}
geo_install_row() {
  local action=$1 path=$2
  if [[ $GEO_UI == 1 ]]; then
    # Files are actual resources; labels are independently styled by Dots.
    if ! declare -F dots::resource_row >/dev/null; then source "$DOTS/lib/dots/resources.bash"; fi
    dots::resource_row "$action" "$path" >&2
  else printf '%s: %s\n' "$action" "${path//[[:cntrl:]]/?}" >&2; fi
}
geo_completion() {
  local shell path parent current backup i=0
  local -a shells=() targets=() existed=() modes=()
  if (( ! GEO_INSTALL )); then geo_completion_source "$GEO_SHELL"; return; fi
  if ((GEO_ALL)); then shells=(bash zsh fish); else shells=("$GEO_SHELL"); fi
  geo_note "Checking ${#shells[@]} completion destinations"
  trap geo_cleanup EXIT
  trap 'exit 130' INT
  trap 'exit 143' TERM HUP
  geo_work
  # Snapshot bytes in private files: Bash variables cannot preserve NUL bytes.
  # No destination is created until the whole target set passes preflight.
  for shell in "${shells[@]}"; do
    parent=${GEO_DIR:-$GEO_ROOT/shells/$shell/completions}
    case $shell in bash) path=$parent/termux-geo.bash ;; zsh) path=$parent/_termux-geo ;; fish) path=$parent/termux-geo.fish ;; esac
    [[ ! -L $path && ( ! -e $path || -f $path ) ]] || geo_fail 1 "refusing nonregular completion target: $path"
    current=$parent
    while [[ ! -e $current ]]; do
      [[ ! -L $current ]] || geo_fail 1 "broken completion directory link: $current"
      if [[ $current != */* ]]; then current=.; else current=${current%/*}; [[ $current ]] || current=/; fi
    done
    [[ -d $current && -w $current ]] || geo_fail 1 "completion directory is not writable: $current"
    geo_completion_source "$shell" > "$GEO_WORK/new.$i" || geo_fail 1 'cannot generate completion'
    if [[ -e $path ]]; then
      [[ -r $path && -w $path ]] || geo_fail 1 "completion file is not writable: $path"
      cp -p -- "$path" "$GEO_WORK/old.$i" || geo_fail 1 'cannot snapshot completion'
      modes+=("$(stat -c '%a' -- "$path")")
      existed+=(1)
    else existed+=(0); modes+=(644); fi
    targets+=("$path"); ((i+=1))
  done
  for ((i=0;i<${#targets[@]};i++)); do
    path=${targets[i]} parent=${targets[i]%/*}
    [[ ! -L $path && ( ! -e $path || -f $path ) ]] || geo_fail 1 "completion target changed: $path; earlier installs/backups are retained"
    if [[ -e $path ]]; then
      [[ ${existed[i]} == 1 ]] || geo_fail 1 "completion target appeared: $path"
      cmp -s -- "$path" "$GEO_WORK/old.$i" || geo_fail 1 "completion target changed: $path"
    else [[ ${existed[i]} == 0 ]] || geo_fail 1 "completion target disappeared: $path"; fi
    if [[ ${existed[i]} == 1 ]] && cmp -s -- "$path" "$GEO_WORK/new.$i"; then geo_install_row Unchanged "$path"; continue; fi
    mkdir -p -- "$parent" || geo_fail 1 'cannot create completion directory; earlier installs/backups are retained'
    if [[ ${existed[i]} == 1 ]]; then
      backup=$(mktemp "$path.bak.XXXXXXXX") || geo_fail 1 'cannot create completion backup'
      cp -p -- "$GEO_WORK/old.$i" "$backup" || geo_fail 1 'cannot preserve completion backup'
      geo_install_row Backup "$backup"
    fi
    GEO_TEMP=$(mktemp "$parent/.termux-geo.XXXXXXXX") || geo_fail 1 'cannot stage completion'
    if ! { cat -- "$GEO_WORK/new.$i" > "$GEO_TEMP" && chmod "${modes[i]}" -- "$GEO_TEMP" && mv -f -- "$GEO_TEMP" "$path"; }; then geo_fail 1 'cannot install completion; earlier installs/backups are retained'; fi
    GEO_TEMP=''
    geo_install_row Installed "$path"
  done
  geo_note 'Completion installation finished; existing differing files were backed up'
  printf '%s\n' 'Start a new configured shell to load the local paths. In an updated Zsh, run rlcs.' \
    'Bash requires bash-completion; Fish discovers its configured completion directories.' >&2
}
