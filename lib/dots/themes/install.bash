# Git themes are data imports. No hooks, submodules, or downloaded configs execute.
dt_git() {
  GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null GIT_TERMINAL_PROMPT=0 git \
    -c core.hooksPath=/dev/null -c protocol.allow=never -c protocol.https.allow=always \
    -c protocol.ssh.allow=always -c protocol.file.allow="${DOTS_TEST_LOCAL_GIT:-never}" "$@"
}
dt_git_record() {
  printf '%s\n' "$2" > "$1/.status.new" && sync -f "$1/.status.new" &&
    mv -f -- "$1/.status.new" "$1/status" && sync -f "$1"
}
dt_git_validate() {
  local path=$1
  [[ -f $path/colors.toml && ! -L $path/colors.toml ]] || { dt_error 'installed themes require colors.toml'; return 1; }
  # Retain downloaded sources for Git updates, but the renderer only reads colors.
  # Background and palette symlinks must not smuggle external files into the import.
  while IFS= read -r -d '' _; do
    dt_error 'installed theme contains symlinks'; return 1
  done < <(find "$path" -path "$path/.git" -prune -o -type l -print0)
  # shellcheck disable=SC2034
  local DT_THEME=import DT_FLAVOR=default
  dt_colors "$path/colors.toml"
}
dt_git_recover() {
  local journal status target stage backup action
  for journal in "$DT_USER_THEMES/.transactions/"*; do
    [[ -d $journal && ! -L $journal && -f $journal/status ]] || continue
    IFS= read -r status < "$journal/status"
    case $status in committed|rolled-back) continue ;; prepared) ;; *) dt_error 'invalid theme transaction status'; return 1 ;; esac
    IFS= read -r target < "$journal/target"; IFS= read -r stage < "$journal/stage"
    IFS= read -r backup < "$journal/backup"; IFS= read -r action < "$journal/action"
    [[ ${target%/*} == "$DT_USER_THEMES" && $backup == "$DT_USER_THEMES/.archives/"* && $stage == "$DT_USER_THEMES/.stage."* ]] || { dt_error 'invalid theme transaction'; return 1; }
    if [[ -d $backup && ! -L $backup ]]; then
      if [[ -e $target || -L $target ]]; then
        [[ ! -e $stage && ! -L $stage ]] || { dt_error 'ambiguous interrupted update'; return 1; }
        mv -- "$target" "$stage" || return
      fi
      mv -- "$backup" "$target" || return
    elif [[ $action == install && -d $target && ! -e $stage ]]; then
      mv -- "$target" "$stage" || return
    fi
    dt_git_record "$journal" rolled-back || return
  done
}
dt_git_theme() (
  umask 077
  local action=$1 name='' url='' target stage backup journal branch old status=0
  shift
  command -v git >/dev/null && command -v flock >/dev/null && command -v sync >/dev/null || { dt_error 'Git themes require git, flock and sync'; return 1; }
  case $action in
    install)
      (($# == 1 || $# == 3)) || return 2
      url=$1
      [[ $url =~ ^https://[^[:space:]]+$ || $url =~ ^ssh://[^[:space:]]+$ || $url =~ ^[a-zA-Z0-9_.-]+@[a-zA-Z0-9_.-]+:[^[:space:]]+$ || ( ${DOTS_TEST_LOCAL_GIT:-} == always && $url == /* ) ]] || { dt_error 'expected an HTTPS or SSH Git URL'; return 1; }
      name=${url##*/}; name=${name##*:}; name=${name%.git}; name=${name#omarchy-}; name=${name#dots-}; name=${name%-theme}; name=${name,,}
      if (($# == 3)); then [[ $2 == --name ]] || return 2; name=$3; fi ;;
    update|remove) (($# == 1)) || return 2; name=$1 ;;
  esac
  if [[ $name == --all && $action == update ]]; then
    for target in "$DT_USER_THEMES/"*/.git; do
      [[ -d $target && ! -L $target ]] || continue
      name=${target%/.git}; name=${name##*/}
      dt_git_theme update "$name" || status=1
    done
    return "$status"
  fi
  dt_theme_id "$name" || { dt_error 'invalid theme identifier'; return 1; }
  [[ ! -d $DT_ROOT/$name ]] || { dt_error 'bundled theme identifiers cannot be replaced'; return 1; }
  [[ $DT_USER_THEMES == /* && $DT_USER_THEMES != *$'\n'* && $DT_USER_THEMES != */../* && $DT_USER_THEMES != */./* ]] || { dt_error 'installed-theme root must be absolute without dot components'; return 1; }
  local parent=$DT_USER_THEMES
  while [[ $parent != / ]]; do
    [[ ! -L $parent && ( ! -e $parent || -d $parent ) ]] || { dt_error 'unsafe installed-theme root'; return 1; }
    parent=${parent%/*}; [[ $parent ]] || parent=/
  done
  for parent in .archives .transactions; do [[ ! -L $DT_USER_THEMES/$parent && ( ! -e $DT_USER_THEMES/$parent || -d $DT_USER_THEMES/$parent ) ]] || return 1; done
  [[ ! -L $DT_USER_THEMES/.lock ]] || return 1
  mkdir -p "$DT_USER_THEMES/.archives" "$DT_USER_THEMES/.transactions" || return
  exec 9>"$DT_USER_THEMES/.lock"; flock -n 9 || { dt_error 'another theme installation is running'; return 1; }
  dt_git_recover || return
  target=$DT_USER_THEMES/$name
  if [[ $action == install ]]; then
    [[ ! -e $target && ! -L $target ]] || { dt_error 'theme identifier already exists'; return 1; }
  else
    [[ -d $target/.git && ! -L $target/.git && ! -L $target && -f $target/.git/dots-managed ]] || { dt_error 'not a dots-managed Git theme'; return 1; }
    local changes
    changes=$(dt_git -C "$target" status --porcelain --untracked-files=all) || return
    [[ -z $changes ]] || { dt_error 'installed theme has local changes'; return 1; }
    if [[ $action == remove ]]; then
      dt_current_id || return
      [[ $REPLY != "$name" ]] || { dt_error 'cannot remove the active theme'; return 1; }
    else
      url=$(dt_git -C "$target" remote get-url origin) || return
      branch=$(dt_git -C "$target" symbolic-ref --short HEAD) || return
      old=$(dt_git -C "$target" rev-parse HEAD) || return
    fi
  fi
  stage=$(mktemp -d "$DT_USER_THEMES/.stage.XXXXXXXX") || return
  if [[ $action != remove ]]; then
    local -a args=(clone --quiet --no-recurse-submodules --template=)
    [[ ! ${branch:-} ]] || args+=(--branch "$branch")
    dt_git "${args[@]}" -- "$url" "$stage" || { dt_error "clone failed; retained staging directory: $stage"; return 1; }
    dt_git_validate "$stage" || return
    if [[ $action == update ]]; then
      dt_git -C "$stage" merge-base --is-ancestor "$old" HEAD || { dt_error 'update is not a fast-forward'; return 1; }
    fi
    printf 'schema=1\n' > "$stage/.git/dots-managed"
    sync -f "$stage" || return
  fi
  journal=$(mktemp -d "$DT_USER_THEMES/.transactions/t.XXXXXXXX") || return
  backup=$DT_USER_THEMES/.archives/$name-${journal##*/}
  printf '%s\n' "$target" > "$journal/target"
  printf '%s\n' "$stage" > "$journal/stage"
  printf '%s\n' "$backup" > "$journal/backup"
  printf '%s\n' "$action" > "$journal/action"
  dt_git_record "$journal" prepared || return
  trap 'dt_git_recover' EXIT
  if [[ $action != install ]]; then mv -- "$target" "$backup" || return; fi
  if [[ $action != remove ]]; then mv -- "$stage" "$target" || return; fi
  sync -f "$DT_USER_THEMES" || return
  dt_git_record "$journal" committed || return
  trap - EXIT
  [[ $action != remove ]] || rmdir -- "$stage" || return
  dots::success "$action: $name (selection unchanged)"
  [[ $action == install ]] || printf 'Recovery copy: %s\n' "$backup"
)
