# Native FSH INI loading and last-good startup theme persistence.
_dots_fsh_save() (
  emulate -L zsh
  umask 077
  local input=$1 saved=${FAST_WORK_DIR:-}/current_theme.zsh object first='' backup='' staged=''
  [[ -n ${FAST_WORK_DIR:-} && -d $FAST_WORK_DIR && -w $FAST_WORK_DIR ]] || return 1
  for object in "$saved" "$saved.zwc"; do
    [[ -L $object || ! -e $object || -f $object ]] || return 1
  done
  if [[ -f $saved && ! -L $saved ]] && command cmp -s -- "$input" "$saved"; then
    # FSH may have compiled a prior selection at this same path.
    [[ ! -e $saved.zwc && ! -L $saved.zwc ]] || zf_rm -f -- "$saved.zwc" || return
    return 0
  fi
  staged=$(command mktemp "$FAST_WORK_DIR/.dots-theme-current.XXXXXXXX") || return
  trap '[[ -z $staged ]] || zf_rm -f -- "$staged"' EXIT
  command cp -- "$input" "$staged" || return
  # Back up foreign selections, including link identity, before replacing them.
  [[ ! -f $saved || -L $saved ]] || IFS= read -r first < "$saved"
  if [[ $first != '# dots-fsh-cache-v2 '* ]] &&
      [[ -e $saved || -L $saved || -e $saved.zwc || -L $saved.zwc ]]; then
    backup=$(command mktemp -d "$FAST_WORK_DIR/.dots-theme-backup.XXXXXXXX") || return
    for object in "$saved" "$saved.zwc"; do
      [[ ! -e $object && ! -L $object ]] || command cp -a -- "$object" "$backup/" || return
    done
  fi
  # Invalidate compiled code before publishing, so startup cannot prefer njen
  # (or another older selection) over the newly saved source.
  [[ ! -e $saved.zwc && ! -L $saved.zwc ]] || zf_rm -f -- "$saved.zwc" || return
  zf_mv -f -- "$staged" "$saved" || return
  staged=''
)

_dots_fsh_load() {
  local key
  for key in ${(k)FAST_HIGHLIGHT_STYLES}; do
    [[ $key != dots* ]] || unset "FAST_HIGHLIGHT_STYLES[$key]"
  done
  source "$1" || return
  [[ ! -r $FAST_WORK_DIR/theme_overlay.zsh ]] || source "$FAST_WORK_DIR/theme_overlay.zsh" || return
  return 0
}

_dots_fsh_theme() {
  emulate -L zsh
  _DOTS_FSH_FAILURE='' _DOTS_FSH_FAILURE_PATH='' _DOTS_FSH_REPAIR=''
  (( ${+functions[fast-theme]} && ${+FAST_HIGHLIGHT_STYLES} )) || return 0
  local file=${_DOTS_THEME_FSH_FILE:-} saved=${FAST_WORK_DIR:-}/current_theme.zsh first=''
  if [[ -z $file || ! -f $file || ! -r $file ]]; then
    # Session-only selections and unavailable artifacts keep the last published
    # Dots colors, without rewriting the saved startup selection.
    if [[ -f $saved ]]; then
      IFS= read -r first < "$saved"
      if [[ $first == '# dots-fsh-cache-v2 '* ]]; then
        _DOTS_FSH_FAILURE='could not load the saved FSH theme or overlay'
        _DOTS_FSH_FAILURE_PATH=$saved
        _DOTS_FSH_REPAIR='Check the saved theme and theme_overlay.zsh in FAST_WORK_DIR, then reload the shell.'
        _dots_fsh_load "$saved" || return
      fi
    fi
    [[ -n $file ]] || return 0
    _DOTS_FSH_FAILURE='generated FSH theme is unavailable; retaining existing syntax colors'
    _DOTS_FSH_FAILURE_PATH=$file
    _DOTS_FSH_REPAIR='Run dots init --setup to prepare the theme and links, then open a new shell.'
    return 1
  fi
  _DOTS_FSH_FAILURE='could not initialize the native FSH loader'
  _DOTS_FSH_REPAIR='Check the Zsh/FSH installation, then reload the shell.'
  zmodload zsh/stat || return
  zmodload -F zsh/files b:zf_mkdir b:zf_mv b:zf_rm || return
  local candidate signature='' temporary key
  local -A info
  for candidate in "$file" "$FAST_BASE_DIR/fast-theme" "$FAST_BASE_DIR/.fast-read-ini-file"; do
    candidate=${candidate:A}
    _DOTS_FSH_FAILURE_PATH=$candidate
    zstat -H info -- "$candidate" 2>/dev/null || return 1
    signature+="${(q)candidate}:${info[device]}:${info[inode]}:${info[size]}:${info[mtime]}:${info[ctime]}:"
  done
  local directory="${XDG_CACHE_HOME:-$HOME/.cache}/dots/zsh/${DOTS_PLATFORM:-linux}-$ZSH_VERSION/fsh"
  local target=$directory/theme.zsh
  [[ ! -r $target ]] || IFS= read -r first < "$target"
  if [[ $first != "# dots-fsh-cache-v2 $signature" ]]; then
    _DOTS_FSH_FAILURE='could not create the FSH theme cache'
    _DOTS_FSH_FAILURE_PATH=$directory
    _DOTS_FSH_REPAIR='Check the cache directory permissions and free space, then reload the shell.'
    zf_mkdir -p -- "$directory" || return
    temporary=$directory/build.$$.${RANDOM}
    _DOTS_FSH_FAILURE='could not compile the FSH theme into its cache; retaining existing syntax colors'
    _DOTS_FSH_FAILURE_PATH=$file
    _DOTS_FSH_REPAIR='Check the FSH template and cache permissions; run dots theme refresh after correcting the template, then reload the shell.'
    # The upstream loader writes/compiles current_theme.zsh. Its work directory
    # and input basename belong to this build, never to the plugin or config.
    if ! (
      umask 077
      zf_mkdir -- "$temporary" || exit 1
      trap 'zf_rm -rf -- "$temporary"' EXIT
      print -r -- "$(<"$file")" > "$temporary/dots.ini" || exit 1
      typeset -g FAST_WORK_DIR=$temporary
      FAST_HIGHLIGHT_STYLES=()
      fast-theme -q "$temporary/dots.ini" > "$temporary/messages" || exit 1
      # FSH reports malformed styles on stdout without consistently failing.
      [[ ! -s $temporary/messages && -s $temporary/current_theme.zsh ]] || exit 1
      # Serialize only the loader's new styles, including a custom secondary
      # theme. Explicit assignments replace stale secondary colors on refresh.
      {
        print -r -- "# dots-fsh-cache-v2 $signature"
        printf 'typeset -g FAST_THEME_NAME=%q\n' "$FAST_THEME_NAME"
        printf 'zstyle :plugin:fast-syntax-highlighting theme %q\n' "$FAST_THEME_NAME"
        for key in ${(ok)FAST_HIGHLIGHT_STYLES}; do
          printf 'FAST_HIGHLIGHT_STYLES[%q]=%q\n' "$key" "${FAST_HIGHLIGHT_STYLES[$key]}"
        done
        printf 'FAST_HIGHLIGHT_STYLES[dots-path]=%q\n' "$file"
      } > "$temporary/theme.zsh" || exit 1
      command zsh -dfn "$temporary/theme.zsh" || exit 1
      zf_mv -f -- "$temporary/theme.zsh" "$target"
    ); then return 1; fi
  fi
  _DOTS_FSH_FAILURE='could not save the FSH startup theme; retaining existing syntax colors'
  _DOTS_FSH_FAILURE_PATH=$saved
  _DOTS_FSH_REPAIR='Check FAST_WORK_DIR for conflicting paths or write failures, then reload the shell.'
  _dots_fsh_save "$target" || return
  _DOTS_FSH_FAILURE='could not load the FSH theme or overlay'
  _DOTS_FSH_FAILURE_PATH=$target
  _DOTS_FSH_REPAIR='Check the saved theme and theme_overlay.zsh in FAST_WORK_DIR, then reload the shell.'
  _dots_fsh_load "$target"
}

# Only failures start a renderer. Healthy shell startup remains native and quiet.
_dots_fsh_apply() {
  if _dots_fsh_theme; then
    _DOTS_FSH_WARNING_KEY=''
    return 0
  fi
  local key="${_DOTS_THEME_GENERATION:-}:${_DOTS_FSH_FAILURE}:${_DOTS_FSH_FAILURE_PATH}"
  [[ ${_DOTS_FSH_WARNING_KEY:-} != "$key" ]] || return 1
  _DOTS_FSH_WARNING_KEY=$key
  command bash -c '
    source "$1/ui.bash"
    dots::warning "dots theme: $2"
    dots::resource_row Path "$3"
    dots::info "$4"
  ' -- "$DOTS/lib/dots" "$_DOTS_FSH_FAILURE" "$_DOTS_FSH_FAILURE_PATH" "$_DOTS_FSH_REPAIR" >&2
  return 1
}
