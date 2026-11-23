# Interactive display only. Completion records and inserted words stay literal.
# Input checks and warm refresh use Zsh builtins; no style query per candidate.
typeset -g _DOTS_COMPLETION_PROVIDERS='(_dots|_git-it|_anodize|_patina|_blastoff|_pkgs|_wttr)'

_dots_completion_owned_context() {
  local name=${service:-${words[1]:-}}
  [[ -n $name && ${_comps[$name]:-} == ${~_DOTS_COMPLETION_PROVIDERS} ]]
}

_dots_completion_native_styles() {
  # compinit/compdef own the command inventory, including aliases and generated
  # theme shortcuts. Inspect only that in-memory registry, once per completion.
  # Requeue this one-shot native hook; it also observes replaced registrations.
  (( ${compprefuncs[(Ie)_dots_completion_native_styles]} )) || compprefuncs+=(_dots_completion_native_styles)
  local name pattern
  local -a names=("${(@k)_comps[(R)${~_DOTS_COMPLETION_PROVIDERS}]}") safe
  for name in "${names[@]}"; do
    [[ -n $name && $name != *[[:cntrl:]:]* ]] && safe+=("${(b)name}")
  done
  safe=("${(@o)safe}")
  (( ${#safe} )) && pattern=":completion:*:*:(${(j:|:)safe}):*"
  if (( ${+_DOTS_COMPLETION_NATIVE_PATTERN} )) && [[ $pattern == $_DOTS_COMPLETION_NATIVE_PATTERN ]]; then
    return 0
  fi
  if [[ -n ${_DOTS_COMPLETION_NATIVE_PATTERN:-} ]]; then
    zstyle -d "$_DOTS_COMPLETION_NATIVE_PATTERN" list-colors group-name
    zstyle -d "${_DOTS_COMPLETION_NATIVE_PATTERN}descriptions" format
  fi
  typeset -g _DOTS_COMPLETION_NATIVE_PATTERN=$pattern
  [[ -n $pattern ]] || return 0
  zstyle -e "$pattern" list-colors '_dots_completion_list_colors'
  zstyle -e "${pattern}descriptions" format '_dots_completion_heading'
  zstyle "$pattern" group-name ''
}

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
  local REPLY
  reply=('%d')
  if [[ ${_DOTS_COMPLETION_ENABLED:-1} == 1 ]] && ! (( ${IN_FZF_TAB:-0} )) && _dots_completion_use_color; then
    _dots_completion_role "${curtag:-}"
    reply=($'\e[0;'${_DOTS_COMPLETION_STYLES[$REPLY]:-39}$'m%d\e[0m')
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
  _dots_completion_label_tail=$separator$description
  if (( color )); then
    [[ $file == 1 ]] || name=$'\e[0;'${_DOTS_COMPLETION_STYLES[$role]:-39}m$name
    [[ -z $separator ]] || _dots_completion_label_tail=$'\e[0;'${_DOTS_COMPLETION_STYLES[separator]:-90}m$separator$'\e[0;'${_DOTS_COMPLETION_STYLES[description]:-90}m$description$'\e[0m'
    REPLY=$name$'\e[0m'
  else REPLY=$name
  fi
  # REPLY in the caller, without exporting or evaluating display data.
  _dots_completion_label_result=$REPLY
}

_dots_completion_ftb_capture() {
  local -a expl
  local REPLY tag=${_DOTS_COMPLETION_TYPE:-${curtag:-}}
  if (( ${IN_FZF_TAB:-0} )) && (( ${+_dots_completion_groups} )) && _dots_completion_owned_context; then
    _dots_completion_owned=1
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
  if [[ ${PREFIX:-} == nf && ${IN_FZF_TAB:-0} == 1 && ${_comps[nf]:-} == _dots &&
        -z ${SUFFIX:-}${IPREFIX:-}${ISUFFIX:-}${compstate[quote]:-} &&
        ${words[CURRENT]:-} == nf && ${compstate[context]:-} == command && ${LBUFFER:-} == *[[:space:]]nf &&
        ( -z ${RBUFFER:-} || ${RBUFFER[1]} == [[:space:]\;\&\|\<\>\)] ) ]] &&
     (( CURRENT > 1 )); then
    setopt localoptions extendedglob
    source "$DOTS/lib/dots/completion/nf.zsh"
    return
  fi
  # The glyph frontend also works with a stock fzf-tab display.
  if (( ! ${+functions[_dots_completion_original_capture]} )); then
    _dots_completion_original_complete "$@"
    return
  fi
  _dots_completion_refresh
  local -A _dots_completion_groups
  local _dots_completion_display=0 _dots_completion_owned=0
  _dots_completion_original_complete "$@"
}

_dots_completion_ftb_generate() {
  if [[ ${_dots_completion_owned:-0} != 1 ]]; then
    _dots_completion_original_generate "$@"
    return
  fi
  local row key metadata prefix suffix role file REPLY _dots_completion_label_result _dots_completion_label_tail
  local -i color=0 color_policy=0 index=0
  _dots_completion_use_color && color_policy=1
  [[ ${_DOTS_COMPLETION_ENABLED:-1} == 1 ]] && color=$color_policy
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
    if (( ! color_policy )); then
      # Retain the leading group marker for fzf-tab group switching; reset
      # before any visible glyph. Strip file-style escapes from the suffix.
      prefix=${(M)prefix##$'\e['[0-9\;]#m}$'\e[0m'
      suffix=${suffix//$'\e['[0-9\;]#m/}
    fi
    # Keep fzf-tab's middle lookup field intact. Only the first display field
    # is searchable; suffixes and descriptions stay visible in the last field.
    rendered+=("$prefix$_dots_completion_label_result"$'\0'"$key"$'\0'"$suffix$_dots_completion_label_tail")
  done
  _ftb_complist=("${rendered[@]}")
  _dots_completion_display=1
}

_dots_completion_ftb_style() {
  _dots_completion_original_style "$@"
  local result=$?
  if [[ ${_dots_completion_display:-0} == 1 && $1 == -a && $2 == fzf-flags ]]; then
    local -a flags=("${(@P)3}")
    flags+=(--with-nth=1,3 --nth=1)
    if _dots_completion_use_color; then
      [[ ${_DOTS_COMPLETION_ENABLED:-1} != 1 ]] || flags+=(--color=fg+:-1:regular)
    else flags+=(--color=bw)
    fi
    set -A "$3" "${flags[@]}"
    return 0
  fi
  if [[ ${_dots_completion_display:-0} == 1 && ${_DOTS_COMPLETION_ENABLED:-1} == 1 && $1 == -a && $2 == active-group-style ]]; then
    # The scoped reload wrapper supplies the complete style after the type
    # color. Native bold before that color would be cleared by its reset.
    set -A "$3" none
    return 0
  fi
  return $result
}

_dots_completion_ftb_header() {
  _dots_completion_original_header "$@" || return
  [[ ${_dots_completion_display:-0} == 1 && ${_DOTS_COMPLETION_ENABLED:-1} == 1 ]] || return 0
  local code marker role
  local -i i color=0
  local -a group_colors
  [[ ${_DOTS_COMPLETION_ENABLED:-1} == 1 ]] && _dots_completion_use_color && color=1
  -ftb-zstyle -a group-colors group_colors || group_colors=("${_ftb_group_colors[@]}")
  for (( i=1; i<=${#_ftb_groups}; i++ )); do
    marker=${group_colors[i]}
    [[ -n $marker ]] || continue
    role=${_dots_completion_groups[${_ftb_groups[i]}]:-candidate}
    code=$'\e[0m'
    (( ! color )) || code=$'\e[0;'${_DOTS_COMPLETION_STYLES[$role]:-39}m
    _ftb_headers=("${(@)_ftb_headers//$marker/$marker$code}")
  done
}

_dots_completion_ftb_fzf() {
  if [[ ${_dots_completion_display:-0} != 1 || ${_DOTS_COMPLETION_ENABLED:-1} != 1 ]]; then
    _dots_completion_original_fzf "$@"
    return
  fi
  local helper="$DOTS/lib/dots/completion/switch-group.zsh"
  local upstream="$FZF_TAB_HOME/lib/ftb-switch-group" heading=''
  if [[ ${_DOTS_COMPLETION_ENABLED:-1} == 1 ]] && _dots_completion_use_color; then
    heading=${_DOTS_COMPLETION_STYLES[heading]:-1;36}
  fi
  # fzf executes reload as shell code. Quote each trusted path/style argument;
  # no candidate, description or provider text is part of this command.
  local _dots_completion_group_helper="${(q)helper} ${(q)upstream} ${(q)heading}"
  _dots_completion_scoped_fzf "$@"
}

_dots_completion_bind_fzf() {
  functions[-ftb-compadd]=$functions[_dots_completion_ftb_capture]
  functions[-ftb-complete]=$functions[_dots_completion_ftb_complete]
  functions[-ftb-generate-complist]=$functions[_dots_completion_ftb_generate]
  functions[-ftb-generate-header]=$functions[_dots_completion_ftb_header]
  functions[-ftb-zstyle]=$functions[_dots_completion_ftb_style]
  functions[-ftb-fzf]=$functions[_dots_completion_ftb_fzf]
  (( ! ${+_ftb_orig_widget} )) || functions[compadd]=$functions[-ftb-compadd]
}

_dots_completion_install_fzf() {
  emulate -L zsh -o extendedglob
  (( ${+functions[-ftb-compadd]} && ${+functions[-ftb-complete]} )) || return 0
  if [[ ${functions[-ftb-complete]} == *'_dots_completion_original_complete'* ]]; then
    if (( ${+functions[_dots_completion_original_fzf]} )); then
      # Function assignments copy bodies. Rebind after source reload without
      # replacing the saved native implementations with our old wrappers.
      _dots_completion_bind_fzf
      return 0
    fi
    functions[-ftb-complete]=$functions[_dots_completion_original_complete]
    if (( ${+functions[_dots_completion_original_capture]} )); then
      # Restore older display adapters before rechecking their interface.
      functions[-ftb-compadd]=$functions[_dots_completion_original_capture]
      functions[-ftb-generate-complist]=$functions[_dots_completion_original_generate]
      functions[-ftb-generate-header]=$functions[_dots_completion_original_header]
      functions[-ftb-zstyle]=$functions[_dots_completion_original_style]
      (( ! ${+_ftb_orig_widget} )) || functions[compadd]=$functions[-ftb-compadd]
    fi
  fi
  local fn original_reload='$FZF_TAB_HOME/lib/ftb-switch-group' scoped_reload='$_dots_completion_group_helper'
  local -i load_failed=0
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
  # +X returns failure for an already materialized ordinary function (including
  # a restored native copy during upgrade). Only load actual autoload stubs.
  for fn in "${helpers[@]}"; do
    if [[ -z ${functions[$fn]:-} || ${functions[$fn]} == *'builtin autoload -X'* ]]; then
      builtin autoload +X -Uz -- "$fn" 2>/dev/null || load_failed=1
    fi
  done
  if (( load_failed )) || ! [[ ${functions[-ftb-compadd]} == *'_ftb_compcap'* &&
     ${functions[-ftb-complete]} == *'_ftb_complist'* &&
     ${functions[-ftb-fzf]} == *"--delimiter='\x00'"* &&
     ${functions[-ftb-fzf]} == *'$FZF_TAB_HOME/lib/ftb-switch-group'* &&
     ${functions[-ftb-fzf]} == *'normalized_active_group_style'* &&
     ${functions[-ftb-generate-complist]} == *'_ftb_complist'* ]]; then
    # Glyph rows use the native frontend directly. They do not require
    # the custom group styling interface used for ordinary completions.
    if (( ! load_failed )) && [[ ${functions[-ftb-complete]} == *'_ftb_finish'* &&
        ${functions[-ftb-fzf]} == *'--print-query'* && ${functions[-ftb-fzf]} == *'--expect='* ]]; then
      functions[_dots_completion_original_complete]=$functions[-ftb-complete]
      functions[-ftb-complete]=$functions[_dots_completion_ftb_complete]
    fi
    for fn in "${(@k)lazy}"; do functions[$fn]=$lazy[$fn]; done
    return 0
  fi
  functions[_dots_completion_original_capture]=$functions[-ftb-compadd]
  functions[_dots_completion_original_complete]=$functions[-ftb-complete]
  functions[_dots_completion_original_generate]=$functions[-ftb-generate-complist]
  functions[_dots_completion_original_header]=$functions[-ftb-generate-header]
  functions[_dots_completion_original_style]=$functions[-ftb-zstyle]
  functions[_dots_completion_original_fzf]=$functions[-ftb-fzf]
  functions[_dots_completion_scoped_fzf]=${functions[-ftb-fzf]//$original_reload/$scoped_reload}
  _dots_completion_bind_fzf
}

if [[ -o interactive ]]; then
  zmodload zsh/stat
  if (( ${+functions[_dots_completion_original_capture]} && ! ${+functions[_dots_completion_original_fzf]} && ! ${+_DOTS_COMPLETION_NATIVE_PATTERN} )); then
    # Retire only the previous adapter's recognizable global styles on reload.
    # The personal loader may already have restored its baseline; keep that and
    # any differently configured user styles intact.
    local -a _dots_old_style
    if zstyle -g _dots_old_style ':completion:*' list-colors &&
        [[ ${#_dots_old_style} == 1 && $_dots_old_style[1] == _dots_completion_list_colors ]]; then
      zstyle -e ':completion:*' list-colors 'reply=("${(@s.:.)LS_COLORS}")'
    fi
    if zstyle -g _dots_old_style ':completion:*:descriptions' format &&
        [[ ${#_dots_old_style} == 1 && $_dots_old_style[1] == _dots_completion_heading ]]; then
      zstyle ':completion:*:descriptions' format '%d'
    fi
    if zstyle -g _dots_old_style ':completion:*' group-name &&
        [[ ${#_dots_old_style} == 1 && -z $_dots_old_style[1] ]]; then
      zstyle -d ':completion:*' group-name
    fi
    unset _dots_old_style
  fi
  # Extended patterns are scoped to helper functions, not the user's editor.
  for _dots_completion_fn in _dots_completion_native_styles _dots_completion_owned_context \
      _dots_completion_preferences _dots_completion_list_colors \
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
  _dots_completion_native_styles
  _dots_completion_install_fzf
fi
