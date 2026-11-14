# Interactive display only. Completion records and inserted words stay literal.
# Input checks and warm refresh use Zsh builtins; no style query per candidate.
_dots_completion_fingerprint() {
  local item
  local -A info
  reply=()
  for item in "${_DOTS_COMPLETION_WATCH[@]}"; do
    if zstat -H info -- "$item" 2>/dev/null; then
      reply+=("$info[device]:$info[inode]:$info[mode]:$info[size]:$info[mtime]:$info[ctime]")
    else reply+=(missing)
    fi
  done
}

_dots_completion_preferences() {
  emulate -L zsh -o extendedglob
  local line key value enabled='' role escaped
  local -i i
  local -A styles
  local -a watch
  for line in "$@"; do
    key=${line%%$'\t'*}; value=${line#*$'\t'}; value=${value%%$'\t'*}
    case $key in
      __completion.enabled) [[ $value == [01] ]] || return 1; enabled=$value ;;
      __completion.color.*)
        role=${key#__completion.color.}
        [[ $role == (candidate|command|option|value|branch|tag|remote|description|heading|separator) &&
           $value == <->(\;<->)# ]] || return 1
        styles[$role]=$value ;;
      __completion.watch) [[ $value == /* && $value != *[[:cntrl:]]* ]] || return 1; watch+=("$value") ;;
      __completion.watch.hex)
        [[ $value == ([0-9a-f][0-9a-f])## ]] || return 1
        escaped=''
        for (( i=1; i<=${#value}; i+=2 )); do escaped+=$'\\x'${value[i,i+1]}; done
        printf -v value '%b' "$escaped"
        [[ $value == /* && $value != *$'\0'* ]] || return 1
        watch+=("$value") ;;
      *) return 1 ;;
    esac
  done
  [[ -n $enabled && ${#styles} == 10 && ${#watch} -gt 0 ]] || return 1
  typeset -g _DOTS_COMPLETION_ENABLED=$enabled
  typeset -gA _DOTS_COMPLETION_STYLES=("${(@kv)styles}")
  typeset -ga _DOTS_COMPLETION_WATCH=("${watch[@]}")
}

_dots_completion_refresh() {
  local previous_status=$? data
  local -a reply
  _dots_completion_fingerprint
  if [[ ${(j:\n:)reply} != ${_DOTS_COMPLETION_STAMP:-} ]]; then
    # Cache failures against their inputs too. A later change retries, while
    # unchanged prompts keep the last-good projection without a subprocess.
    _DOTS_COMPLETION_STAMP=${(j:\n:)reply}
    data=$(command python3 -B "$DOTS/lib/dots/completion_preferences.py" 2>/dev/null)
    if (( $? == 0 )) && _dots_completion_preferences "${(@f)data}"; then
      _dots_completion_fingerprint
      _DOTS_COMPLETION_STAMP=${(j:\n:)reply}
    fi
  fi
  return $previous_status
}

_dots_completion_use_color() {
  local mode=${DOTS_COLOR:-${dots_options[DOTS_COLOR]:-auto}}
  [[ $mode == always || $mode != never && -z ${NO_COLOR:-} && ${TERM:-dumb} != dumb && -o interactive && -t 2 ]]
}

_dots_completion_role() {
  case $1 in
    command|commands|*-commands|builtins|aliases|functions|reserved-words) REPLY=command ;;
    option|options) REPLY=option ;;
    branch|*branch*|heads|*-heads) REPLY=branch ;;
    tag|tags|*-tags) REPLY=tag ;;
    remote|remotes|remote-names|*-remotes) REPLY=remote ;;
    value|values|*-values|option-*|argument-*) REPLY=value ;;
    *) REPLY=candidate ;;
  esac
}

_dots_completion_list_colors() {
  local role pattern base separator description
  _dots_completion_refresh
  reply=()
  _dots_completion_use_color || return 0
  reply=("${(@s.:.)LS_COLORS}")
  [[ ${_DOTS_COMPLETION_ENABLED:-1} == 1 ]] || return 0
  # fzf-tab's file parser only understands LS_COLORS. Nonfile spans are
  # projected by the guarded adapter, not passed to its filename parser.
  (( ${IN_FZF_TAB:-0} )) && return 0
  separator=${_DOTS_COMPLETION_STYLES[separator]:-90}
  description=${_DOTS_COMPLETION_STYLES[description]:-90}
  for role pattern in candidate '(candidates)' command '(commands|*-commands|builtins|aliases|functions|reserved-words)' \
                      option '(options)' value '(values|*-values|option-*|argument-*)' branch '(*branch*|heads|*-heads)' \
                      tag '(tags|*-tags)' remote '(remotes|remote-names|*-remotes)'; do
    base=${_DOTS_COMPLETION_STYLES[$role]:-39}
    reply+=("$pattern=(#b)(*)( -- )(*)=0=$base=$separator=$description" "$pattern=*=0;$base")
  done
}

_dots_completion_heading() {
  reply=('%d')
  if [[ ${_DOTS_COMPLETION_ENABLED:-1} == 1 ]] && ! (( ${IN_FZF_TAB:-0} )) && _dots_completion_use_color; then
    reply=($'\e[0;'${_DOTS_COMPLETION_STYLES[heading]:-36}$'m%d\e[0m')
  fi
}

# Escape display controls without evaluating provider text. Insertion continues
# using fzf-tab's original middle field, including when labels look identical.
_dots_completion_safe_text() {
  local value=$1 char replacement
  REPLY=$value
  [[ $value == *[[:cntrl:]]* ]] || return 0
  REPLY=''
  for char in "${(@s::)value}"; do
    case $char in
      $'\e') replacement='\e' ;;
      $'\t') replacement='\t' ;;
      $'\r') replacement='\r' ;;
      $'\n') replacement='\n' ;;
      [[:cntrl:]]) printf -v replacement '\\x%02x' "'$char" ;;
      *) replacement=$char ;;
    esac
    REPLY+=$replacement
  done
}

_dots_completion_label() {
  local label=$1 word=$2 role=$3 file=$4 color=$5 name tail separator='' description=''
  local REPLY
  # Match the actual word before considering the description delimiter. A file
  # named "x -- y" must not be mistaken for a filename plus description.
  name=$label
  for word in "$word" "${(Q)word}"; do
    [[ -n $word && $label == "$word"* ]] || continue
    tail=${label#"$word"}
    if [[ $tail == [[:space:]]##--[[:space:]]* ]]; then
      name=$word
      separator=${tail%%--*}'-- '
      description=${tail#*-- }
      break
    fi
  done
  _dots_completion_safe_text "$name"; name=$REPLY
  _dots_completion_safe_text "$description"; description=$REPLY
  if (( color )); then
    [[ $file == 1 ]] || name=$'\e[0;'${_DOTS_COMPLETION_STYLES[$role]:-39}m$name
    [[ -z $separator ]] || name+=$'\e[0;'${_DOTS_COMPLETION_STYLES[separator]:-90}m$separator$'\e[0;'${_DOTS_COMPLETION_STYLES[description]:-90}m$description
    REPLY=$name$'\e[0m'
  else REPLY=$name$separator$description
  fi
  # REPLY in the caller, without exporting or evaluating display data.
  _dots_completion_label_result=$REPLY
}

_dots_completion_ftb_capture() {
  local -a expl
  local REPLY tag=${_DOTS_COMPLETION_TYPE:-${curtag:-}}
  if (( ${IN_FZF_TAB:-0} )) && (( ${+_dots_completion_groups} )); then
    zparseopts -E X+:=expl
    if [[ -n ${expl[2]:-} ]]; then
      _dots_completion_role "$tag"
      if [[ -n ${_dots_completion_groups[${expl[2]}]:-} && ${_dots_completion_groups[${expl[2]}]} != $REPLY ]]; then
        REPLY=candidate
      fi
      _dots_completion_groups[${expl[2]}]=$REPLY
    fi
  fi
  _dots_completion_original_capture "$@"
}

_dots_completion_ftb_complete() {
  _dots_completion_refresh
  local -A _dots_completion_groups
  local _dots_completion_display=0
  _dots_completion_original_complete "$@"
}

_dots_completion_ftb_generate() {
  if [[ ${_DOTS_COMPLETION_ENABLED:-1} != 1 ]]; then
    _dots_completion_original_generate "$@"
    return
  fi
  local row key metadata prefix suffix role file REPLY _dots_completion_label_result
  local -i color=0 index=0
  _dots_completion_use_color && color=1
  local -A descriptions captured_words files v labels
  # fzf-tab replaces labels with __hide__ markers for brief/hidden headings.
  # Keep semantic identity before generation; visibility must not change types.
  local -a rendered captures fields groups=("${_ftb_groups[@]}")
  # fzf --ansi strips SGR even in hidden fields. Give control-bearing labels
  # an inert display ID, while preserving word/args and all insertion metadata.
  # Previews and selection use the same captured ID; no text is evaluated.
  for row in "${_ftb_compcap[@]}"; do
    key=${row%%$'\2'*}; metadata=${row#*$'\2'}
    if [[ $key == *[[:cntrl:]]* ]]; then
      (( ++index ))
      prefix="__dots_completion_${index}__"
      while [[ -n ${_ftb_compcap[(r)$prefix$'\2'*]} ]]; do prefix+=_; done
      labels[$prefix]=$key
      key=$prefix
    fi
    captures+=("$key"$'\2'"$metadata")
  done
  _ftb_compcap=("${captures[@]}")
  _dots_completion_original_generate "$@" || return
  for row in "${_ftb_compcap[@]}"; do
    [[ $row == *$'\2'* ]] || return 0
    key=${row%%$'\2'*}; metadata=${row#*$'\2'}
    fields=("${(@0)metadata}")
    (( ${#fields} % 2 == 0 )) || return 0
    v=("${fields[@]}")
    [[ -n ${v[word]+present} ]] || return 0
    descriptions[$key]=${_dots_completion_groups[${groups[${v[group]:-0}]:-}]:-candidate}
    captured_words[$key]=${v[word]}
    files[$key]=${+v[realdir]}
  done
  for row in "${_ftb_complist[@]}"; do
    # Validate the complete list before committing any rewritten row.
    [[ $row == *$'\0'*$'\0'* ]] || return 0
    prefix=${row%%$'\0'*}; key=${${row#*$'\0'}%%$'\0'*}; suffix=${row##*$'\0'}
    [[ -n ${captured_words[$key]+present} ]] || return 0
    role=${descriptions[$key]:-candidate}; file=${files[$key]:-0}
    _dots_completion_label "${labels[$key]-$key}" "${captured_words[$key]}" "$role" "$file" "$color"
    if (( ! color )); then
      # Retain the leading group marker for fzf-tab group switching; reset
      # before any visible glyph. Strip file-style escapes from the suffix.
      prefix=${(M)prefix##$'\e['[0-9\;]#m}$'\e[0m'
      suffix=${suffix//$'\e['[0-9\;]#m/}
    fi
    rendered+=("$prefix$_dots_completion_label_result"$'\0'"$key"$'\0'"$suffix")
  done
  _ftb_complist=("${rendered[@]}")
  _dots_completion_display=1
}

_dots_completion_ftb_style() {
  _dots_completion_original_style "$@"
  local result=$?
  if [[ ${_dots_completion_display:-0} == 1 && $1 == -a && $2 == fzf-flags ]]; then
    local -a flags=("${(@P)3}")
    flags+=(--with-nth=1,3 --nth=..)
    if _dots_completion_use_color; then flags+=(--color=fg+:-1:regular)
    else flags+=(--color=bw)
    fi
    set -A "$3" "${flags[@]}"
    return 0
  fi
  return $result
}

_dots_completion_ftb_header() {
  _dots_completion_original_header "$@" || return
  [[ ${_dots_completion_display:-0} == 1 ]] || return 0
  local code=$'\e['${_DOTS_COMPLETION_STYLES[heading]:-36}m marker
  local -a group_colors
  _dots_completion_use_color || code=$'\e[0m'
  -ftb-zstyle -a group-colors group_colors || group_colors=("${_ftb_group_colors[@]}")
  for marker in "${group_colors[@]}"; do
    [[ -n $marker ]] || continue
    _ftb_headers=("${(@)_ftb_headers//$marker/$marker$code}")
  done
}

_dots_completion_install_fzf() {
  emulate -L zsh -o extendedglob
  (( ${+functions[-ftb-compadd]} && ${+functions[-ftb-complete]} )) || return 0
  [[ ${functions[-ftb-complete]} != *'_dots_completion_original_complete'* ]] || return 0
  local fn
  local -A lazy
  local -a helpers=(-ftb-generate-complist -ftb-generate-header -ftb-fzf)
  local -a fpath=("${fpath[@]}")
  [[ -z ${FZF_TAB_HOME:-} ]] || fpath=("$FZF_TAB_HOME/lib" "${fpath[@]}")
  # Zinit replaces autoload declarations with FPATH-restoring shims. +X leaves
  # those already-defined functions intact, hiding the implementation from our
  # interface checks. Materialize only this known lazy form, without calling it
  # (calling -ftb-fzf would open a picker). Keep unknown/custom wrappers intact.
  for fn in "${helpers[@]}"; do
    if [[ ${functions[$fn]:-} == [[:space:]]#local\ -a\ fpath[[:space:]]#fpath=\(*\)[[:space:]]#builtin\ autoload\ -X\ -U\ -z[[:space:]]# &&
          -r ${FZF_TAB_HOME}/lib/$fn ]]; then
      lazy[$fn]=$functions[$fn]
      unfunction -- "$fn"
    fi
  done
  # Recognize the fields we preserve, not a plugin version string. Unknown
  # interfaces keep the plugin's native renderer and completion behavior.
  if ! builtin autoload +X -Uz -- "${helpers[@]}" 2>/dev/null ||
     ! [[ ${functions[-ftb-compadd]} == *'_ftb_compcap'* &&
     ${functions[-ftb-complete]} == *'_ftb_complist'* &&
     ${functions[-ftb-fzf]} == *"--delimiter='\x00'"* &&
     ${functions[-ftb-generate-complist]} == *'_ftb_complist'* ]]; then
    for fn in "${(@k)lazy}"; do functions[$fn]=$lazy[$fn]; done
    return 0
  fi
  functions[_dots_completion_original_capture]=$functions[-ftb-compadd]
  functions[_dots_completion_original_complete]=$functions[-ftb-complete]
  functions[_dots_completion_original_generate]=$functions[-ftb-generate-complist]
  functions[_dots_completion_original_header]=$functions[-ftb-generate-header]
  functions[_dots_completion_original_style]=$functions[-ftb-zstyle]
  functions[-ftb-compadd]=$functions[_dots_completion_ftb_capture]
  functions[-ftb-complete]=$functions[_dots_completion_ftb_complete]
  functions[-ftb-generate-complist]=$functions[_dots_completion_ftb_generate]
  functions[-ftb-generate-header]=$functions[_dots_completion_ftb_header]
  functions[-ftb-zstyle]=$functions[_dots_completion_ftb_style]
  (( ! ${+_ftb_orig_widget} )) || functions[compadd]=$functions[-ftb-compadd]
}

if [[ -o interactive ]]; then
  zmodload zsh/stat
  # Extended patterns are scoped to helper functions, not the user's editor.
  for _dots_completion_fn in _dots_completion_preferences _dots_completion_list_colors \
      _dots_completion_label _dots_completion_ftb_generate; do
    functions[$_dots_completion_fn]=$'emulate -L zsh -o extendedglob\n'${functions[$_dots_completion_fn]}
  done
  unset _dots_completion_fn
  if _dots_completion_preferences "${_DOTS_COMPLETION_SETTING_ROWS[@]}"; then
    _dots_completion_fingerprint
    typeset -g _DOTS_COMPLETION_STAMP=${(j:\n:)reply}
  else
    typeset -ga _DOTS_COMPLETION_WATCH=("$DOTS/default/config.json" "$DOTS/default/colors.toml")
    _DOTS_COMPLETION_STAMP=''
    _dots_completion_refresh
  fi
  zstyle -e ':completion:*' list-colors '_dots_completion_list_colors'
  zstyle -e ':completion:*:descriptions' format '_dots_completion_heading'
  zstyle ':completion:*' group-name ''
  _dots_completion_install_fzf
fi
