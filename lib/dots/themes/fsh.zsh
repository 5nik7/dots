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
  (( ${+functions[fast-theme]} && ${+FAST_HIGHLIGHT_STYLES} )) || return 0
  local file=${_DOTS_THEME_FSH_FILE:-} saved=${FAST_WORK_DIR:-}/current_theme.zsh first=''
  if [[ -z $file || ! -r $file ]]; then
    # Session-only selections and unavailable artifacts keep the last published
    # Dots colors, without rewriting the saved startup selection.
    if [[ -f $saved ]]; then
      IFS= read -r first < "$saved"
      if [[ $first == '# dots-fsh-cache-v2 '* ]]; then
        _dots_fsh_load "$saved"
        return $?
      fi
    fi
    [[ -z $file ]]
    return $?
  fi
  zmodload zsh/stat || return
  zmodload -F zsh/files b:zf_mkdir b:zf_mv b:zf_rm || return
  local candidate signature='' temporary key
  local -A info
  for candidate in "$file" "$FAST_BASE_DIR/fast-theme" "$FAST_BASE_DIR/.fast-read-ini-file"; do
    candidate=${candidate:A}
    zstat -H info -- "$candidate" 2>/dev/null || return 1
    signature+="${(q)candidate}:${info[device]}:${info[inode]}:${info[size]}:${info[mtime]}:${info[ctime]}:"
  done
  local directory="${XDG_CACHE_HOME:-$HOME/.cache}/dots/zsh/${DOTS_PLATFORM:-linux}-$ZSH_VERSION/fsh"
  local target=$directory/theme.zsh
  [[ ! -r $target ]] || IFS= read -r first < "$target"
  if [[ $first != "# dots-fsh-cache-v2 $signature" ]]; then
    zf_mkdir -p -- "$directory" || return
    temporary=$directory/build.$$.${RANDOM}
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
  _dots_fsh_save "$target" || return
  _dots_fsh_load "$target"
}
