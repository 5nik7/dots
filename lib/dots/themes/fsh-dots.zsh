# Dots route words in the editor, using FSH's native region-highlight protocol.
# Exact executable checks only: no catalog scan, command execution or BUFFER edit.
_dots_fsh_chroma() {
  emulate -L zsh -o extendedglob
  local first=$1 word=$2 begin=$3 end=$4
  # Nested FSH parsing (for example a command substitution) owns separate state.
  local scope=${#funcstack} prefix directory target style
  local active_key=dots-route-active-$scope prefix_key=dots-route-prefix-$scope
  local pending_key=dots-route-pending-$scope
  local -a roots ranges
  local -i index
  if (( first )); then
    FAST_HIGHLIGHT[$active_key]=1
    FAST_HIGHLIGHT[$prefix_key]=''
    FAST_HIGHLIGHT[$pending_key]=''
    # The native parser carries case-arm state across every ordinary word.
    (( next_word = 2 | 8192 | (this_word & BIT_case_code) ))
    return 1
  fi
  [[ ${__arg_type:-0} != 3 ]] || { (( next_word &= ~8192 )); return 2; }
  (( in_redirection > 0 || this_word & 128 )) && return 1
  [[ $word != '<<<' ]] || return 1
  [[ ${FAST_HIGHLIGHT[$active_key]:-0} == 1 ]] || return 1
  (( next_word = 2 | 8192 | (this_word & BIT_case_code) ))
  prefix=${FAST_HIGHLIGHT[$prefix_key]}
  # Root presentation flags may precede a command; their native FSH handling
  # retains option/value syntax. Other options and operands end route matching.
  if [[ -z $prefix ]]; then
    case $word in --color=*|--icons=*|--raw|-r) return 1 ;; esac
  fi
  # Filename hyphens delimit route words. Only this explicit dispatcher alias
  # accepts a hyphen inside one word; arbitrary `git-status` is not a route.
  if [[ ( $word != [a-z][a-z0-9]# && ! ( $prefix == files && $word == migrate-apps ) ) || -z ${DOTS:-} ]]; then
    FAST_HIGHLIGHT[$active_key]=0
    return 1
  fi
  target=${prefix:+$prefix-}$word
  style=''
  if [[ -z $prefix && $word == (help|commands|completion|init) ]]; then
    style=${FAST_THEME_NAME}subcommand
  else
    [[ ${DOTS_PROFILE_CHECKOUT:-} != "$DOTS" ]] || roots=("${(@s.:.)DOTS_PROFILE_BIN_PATHS}")
    roots+=("$DOTS/bin" "$DOTS/local/bin")
    for directory in "${roots[@]}"; do
      [[ $directory == /* ]] || continue
      if [[ -f $directory/dots-$target && -x $directory/dots-$target ]]; then
        style=${FAST_THEME_NAME}subcommand
        break
      fi
    done
  fi
  if [[ -z $style ]]; then
    # A namespace need not have its own executable (files migrate apps). Keep
    # native coloring until a later literal word resolves the complete path.
    # Only that exact match may color earlier deferred words retroactively.
    FAST_HIGHLIGHT[$prefix_key]=$target
    FAST_HIGHLIGHT[$pending_key]+=" $begin $end"
    return 1
  fi
  # `dots help git status` has the same command path as `dots git status`.
  [[ -z $prefix && $word == help ]] || FAST_HIGHLIGHT[$prefix_key]=$target
  if [[ -n ${FAST_HIGHLIGHT_STYLES[$style]:-} && ${FAST_HIGHLIGHT_STYLES[$style]} != none ]]; then
    ranges=( ${=FAST_HIGHLIGHT[$pending_key]} $begin $end )
    for (( index=1; index<=${#ranges}; index+=2 )); do
      (( begin=ranges[index]-${#PREBUFFER}, end=ranges[index+1]-${#PREBUFFER}, begin >= 0 )) &&
        reply+=("$begin $end ${FAST_HIGHLIGHT_STYLES[$style]}")
    done
  fi
  FAST_HIGHLIGHT[$pending_key]=''
  (( this_word = next_word ))
  _start_pos=$_end_pos
  return 0
}

_dots_fsh_install_chroma() {
  (( ${+functions[-fast-highlight-process]} && ${+FAST_HIGHLIGHT} && ${+FAST_HIGHLIGHT_STYLES} )) || return 0
  [[ ${functions[-fast-highlight-process]} == *'chroma-'* &&
     ${functions[-fast-highlight-process]} == *'8192'* ]] || return 0
  # An explicit existing entry, including an empty disabling entry, belongs to
  # the user or plugin. Repeated initialization must not replace it.
  (( ${+FAST_HIGHLIGHT[chroma-dots]} )) || FAST_HIGHLIGHT[chroma-dots]=_dots_fsh_chroma
  return 0
}
