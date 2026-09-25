# Wallpaper adapters are explicit post-publication actions, never palette hooks.
dt_bg_files() {
  local dir=$1 file
  for file in "$dir/backgrounds/"* "${XDG_CONFIG_HOME:-$HOME/.config}/dots/backgrounds/$DT_BG_ID/"*; do
    [[ -f $file && ! -L $file ]] || continue
    case ${file,,} in *.png|*.jpg|*.jpeg|*.webp|*.bmp) printf '%s\0' "$file" ;; esac
  done
}
dt_bg_preflight() {
  local file=$1 locked=${2:-0}
  [[ -f $file && $file != *$'\n'* ]] || { dt_error 'background must be an existing image'; return 1; }
  case ${file,,} in *.png|*.jpg|*.jpeg|*.webp|*.bmp) ;; *) dt_error 'unsupported background image'; return 1 ;; esac
  file=$(realpath -- "$file") || return
  local kernel=''
  [[ ! -r /proc/sys/kernel/osrelease ]] || IFS= read -r kernel < /proc/sys/kernel/osrelease
  DT_BG_COMMAND=()
  if [[ ${TERMUX_VERSION:-} && ${PREFIX:-} == */usr ]]; then
    DT_BG_COMMAND=(termux-wallpaper -f "$file"); (( ! locked )) || DT_BG_COMMAND+=(-l)
  elif ((locked)); then dt_error 'lock-screen wallpaper is Android-only'; return 1
  elif [[ ${WSL_DISTRO_NAME:-} || ${WSL_INTEROP:-} || ${kernel,,} == *microsoft* ]]; then dt_error 'WSL wallpaper changes are unavailable'; return 1
  elif [[ ${OS:-} == Windows_NT || ${OSTYPE:-} == msys* || ${OSTYPE:-} == cygwin* ]]; then dt_error 'native Windows wallpaper changes are unavailable'; return 1
  elif [[ ${WAYLAND_DISPLAY:-} ]]; then DT_BG_COMMAND=(swww img "$file")
  elif [[ ${DISPLAY:-} ]]; then DT_BG_COMMAND=(feh --no-fehbg --bg-fill "$file")
  else dt_error 'no supported wallpaper session'; return 1; fi
  command -v "${DT_BG_COMMAND[0]}" >/dev/null && command -v timeout >/dev/null || { dt_error 'wallpaper adapter or timeout unavailable'; return 1; }
  DT_BG_FILE=$file
}
dt_bg() (
  local action=${1:-help} file='' locked=0 previous='' record temp journal
  (($# == 0)) || shift
  if [[ $action == help ]]; then dt_help bg; return; fi
  dt_current_id || return; DT_BG_ID=$REPLY
  dt_find_theme "$DT_BG_ID" || return
  record=$DT_STATE/backgrounds/$DT_BG_ID
  local -a files=()
  mapfile -d '' -t files < <(dt_bg_files "$DT_THEME_DIR" | LC_ALL=C sort -zu)
  case $action in
    list)
      (($# == 0)) || return 2
      if dots::human; then
        dots::heading "Backgrounds / $DT_BG_ID"
        for file in "${files[@]}"; do dots::path "$file"; dots::row "${file##*/}" "$REPLY"; done
        printf '\n  %s backgrounds available\n' "${#files[@]}"
      else ((${#files[@]} == 0)) || printf '%s\n' "${files[@]}"; fi
      return ;;
    current) (($# == 0)) || return 2; [[ -f $DT_STATE/background-current && ! -L $DT_STATE/background-current ]] && cat "$DT_STATE/background-current"; return ;;
    set) (($# >= 1 && $# <= 2)) || return 2; file=$1; shift
      if (($#)); then [[ $1 == --lock-screen ]] || return 2; locked=1; fi ;;
    next|select)
      (($# == 0)) || return 2
      ((${#files[@]})) || { dt_error 'no theme backgrounds'; return 1; }
      [[ ! -f $record || -L $record ]] || IFS= read -r previous < "$record"
      file=${files[0]}
      local i
      for ((i=0;i<${#files[@]};i++)); do
        if [[ ${files[i]} == "$previous" ]]; then
          if [[ $action == select ]]; then file=$previous; else file=${files[(i+1)%${#files[@]}]}; fi
          break
        fi
      done ;;
    switcher)
      (($# == 0)) || return 2
      command -v fzf >/dev/null || { dt_error 'background switcher requires fzf'; return 1; }
      ((${#files[@]})) || { dt_error 'no theme backgrounds'; return 1; }
      file=$(printf '%s\n' "${files[@]}" | fzf --prompt='Background: ') || return ;;
    *) return 2 ;;
  esac
  dt_bg_preflight "$file" "$locked" || return
  file=$DT_BG_FILE
  source "$DT_LIB/state.bash"
  dt_state_preflight || return
  [[ ! -L $DT_STATE/backgrounds && ! -L $record && ! -L $DT_STATE/background-current && ! -L $DT_STATE/background.lock ]] || return 1
  mkdir -p "$DT_STATE/backgrounds" || return
  exec 8>"$DT_STATE/background.lock"; flock -n 8 || return 1
  journal=$(mktemp "$DT_STATE/backgrounds/action.XXXXXXXX") || return
  printf 'prepared\n%s\n' "$file" > "$journal"; dt_flush "$journal" || return
  if ! timeout 15 "${DT_BG_COMMAND[@]}"; then printf 'failed\n%s\n' "$file" > "$journal"; dt_flush "$journal"; dt_error 'wallpaper failed; app theme remains published'; return 1; fi
  if (( ! locked )); then
    temp=$(mktemp "$DT_STATE/backgrounds/.selection.XXXXXXXX") || return
    printf '%s\n' "$file" > "$temp"; dt_flush "$temp" && mv -- "$temp" "$record" || return
    temp=$(mktemp "$DT_STATE/.background.XXXXXXXX") || return
    printf '%s\n' "$file" > "$temp"; dt_flush "$temp" && mv -- "$temp" "$DT_STATE/background-current" || return
  fi
  printf 'committed\n%s\n' "$file" > "$journal"; dt_flush "$journal" && dt_flush "$DT_STATE" || return
  if dots::human; then
    dots::path "$file"
    if ((locked)); then dots::success "Lock-screen background: $REPLY"
    else dots::success "Background: $REPLY"; fi
  fi
)
