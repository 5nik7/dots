# Help-only semantic spans. Keep the basic renderer usable without Python.
# Metadata and examples are inert text; no shell expansion or evaluation occurs.
typeset -ga _DOTS_HELP_SPAN_TEXT=() _DOTS_HELP_SPAN_ROLE=() _DOTS_HELP_LINES=() _DOTS_HELP_ROUTES=()
typeset -g _DOTS_HELP_ROUTES_KEY=''
typeset -gA _DOTS_HELP_STYLES

dots::help_style() {
  dots::style "${1:-1}" || return
  local role fallback
  for role in executable:36 command:34 subcommand:35 option:33 argument:32 heading:1\;96 description:39 punctuation:90 tagline:39; do
    fallback=${role#*:}; role=${role%%:*}
    [[ ${_DOTS_HELP_STYLES[$role]+set} ]] || _DOTS_HELP_STYLES[$role]=$fallback
  done
}

dots::help_span() {
  local text=$1 role=$2
  [[ $text ]] || return 0
  local last=$((${#_DOTS_HELP_SPAN_ROLE[@]}-1))
  if (( last >= 0 )) && [[ ${_DOTS_HELP_SPAN_ROLE[last]} == "$role" ]]; then
    _DOTS_HELP_SPAN_TEXT[last]+=$text
  else
    _DOTS_HELP_SPAN_TEXT+=("$text") _DOTS_HELP_SPAN_ROLE+=("$role")
  fi
}

dots::help_routes() {
  local route=$1 item key=$1$'\t'"${DOTS_CATALOG[*]}"
  [[ $key != "$_DOTS_HELP_ROUTES_KEY" ]] || return 0
  _DOTS_HELP_ROUTES=(help commands completion init)
  [[ ! $route ]] || _DOTS_HELP_ROUTES+=("$route")
  for item in "${DOTS_CATALOG[@]}"; do _DOTS_HELP_ROUTES+=("${item//-/ }"); done
  _DOTS_HELP_ROUTES_KEY=$key
}

dots::help_tokens() {
  local text=$1 kind=${2:-syntax} route=${3:-${_DOTS_HELP_ROUTE:-}} word role depth=0 literal=0 reference=0
  local pending='' command_path='' candidate item found long short type _description directory group_index last_role=''
  _DOTS_HELP_SPAN_TEXT=() _DOTS_HELP_SPAN_ROLE=()
  if [[ $kind == heading || $kind == tagline ]]; then dots::help_span "$text" "$kind"; return; fi
  local -a words=() group_paths=() group_depths=() group_pending=() group_references=()
  dots::help_routes "$route"
  # Extract a complete inert token per builtin regex match. Adjacent quoted and
  # unquoted pieces remain one word, including an unterminated quoted suffix.
  # No shell parser or expansion is involved.
  local remaining=$text token_pattern='^(([^][(){}<>|,=;:[:space:]"'"'"']+|"[^"]*("|$)|'"'"'[^'"'"']*('"'"'|$))+|[[:space:]]+|.)'
  while [[ $remaining ]]; do
    [[ $remaining =~ $token_pattern ]] || return 1
    word=${BASH_REMATCH[1]}; words+=("$word")
    remaining=${remaining:${#word}}
  done
  for word in "${words[@]}"; do
    role=description
    if [[ $word != *[![:space:]]* ]]; then dots::help_span "$word" description; continue; fi
    case $word in
      '['|']'|'('|')'|'{'|'}'|'<'|'>'|'|'|','|'='|';'|':')
        dots::help_span "$word" punctuation
        case $word in
          '['|'(' |'{')
            group_paths+=("$command_path"); group_depths+=("$depth")
            group_pending+=("$pending"); group_references+=("$reference") ;;
          ']'|')'|'}')
            group_index=$((${#group_paths[@]}-1))
            if (( group_index >= 0 )); then
              unset 'group_paths[group_index]' 'group_depths[group_index]' 'group_pending[group_index]' 'group_references[group_index]'
              pending=''
            fi ;;
          ','|'|')
            group_index=$((${#group_paths[@]}-1))
            if (( group_index >= 0 )); then
              command_path=${group_paths[group_index]}; depth=${group_depths[group_index]}
              pending=${group_pending[group_index]}; reference=${group_references[group_index]}
            elif [[ $last_role == command || $last_role == subcommand ]] && (( depth )); then
              if [[ $command_path == *' '* ]]; then command_path=${command_path% *}; else command_path=''; fi
              ((depth-=1))
            fi ;;
        esac
        [[ $word != ';' ]] || { reference=0; depth=0; command_path=''; }
        continue ;;
    esac
    if [[ $literal == 1 ]]; then role=argument
    elif [[ $pending && $word != -* ]]; then
      if [[ $kind != prose && $kind != description || $word =~ ^[A-Z][A-Z0-9_.-]*$ ]]; then role=argument; fi
      pending=''
    elif [[ $word == dots || $word == dots-* ]]; then
      role=executable; reference=1; depth=0; command_path=''; literal=0
    elif [[ $word == -- ]]; then role=option; literal=1
    elif [[ $word == -[[:alnum:]]* || $word == --[[:alnum:]]* ]]; then
      role=option; pending=''
      for item in "${DOTS_META_OPTIONS[@]}" "${DOTS_GLOBAL_OPTIONS[@]}"; do
        IFS='|' read -r long short type _description <<< "$item"
        if [[ $word == "$long" || $word == "$short" ]]; then [[ $type == flag ]] || pending=1; break; fi
      done
    elif [[ $kind == argument ]]; then role=argument
    elif [[ $word == OPTIONS || $word == FLAGS || $word == options && $kind != prose && $kind != description ]]; then role=option
    elif [[ $word == COMMAND || $word == COMMAND... || $word == COMMANDS ]]; then role='command'
    elif [[ $word == SUBCOMMAND || $word == SUBCOMMAND... ]]; then role=subcommand
    elif [[ $kind != prose && $kind != description && $word =~ ^[A-Z][A-Z0-9_.-]*$ ]]; then role=argument
    elif [[ $kind == command && $depth == 0 ]]; then
      role='command'; depth=1; command_path=$word; reference=1
    elif (( reference )); then
      candidate=${command_path:+$command_path }$word; found=0
      for item in "${_DOTS_HELP_ROUTES[@]}"; do
        if [[ $item == "$candidate" || $item == "$candidate "* ]]; then found=1; break; fi
      done
      # Direct --help has only the selected header. Recognize referenced routes
      # with targeted file probes; never scan or execute an extension for styling.
      if (( ! found )) && [[ $candidate =~ ^[a-z][a-z0-9]*(\ [a-z][a-z0-9]*)*$ ]]; then
        for directory in "${DOTS_ROOTS[@]}"; do
          if [[ -f $directory/dots-${candidate// /-} && -x $directory/dots-${candidate// /-} ]]; then found=1; break; fi
        done
      fi
      if (( found )); then
        if (( depth == 0 )); then role='command'; else role=subcommand; fi
        ((depth+=1)); command_path=$candidate
      elif [[ $kind == prose || $kind == description ]]; then
        role=description; reference=0
      else role=argument; fi
    elif [[ $kind == syntax || $kind == example || $kind == option ]]; then role=argument
    fi
    last_role=$role
    if [[ $role != description && $word == *... && ${#word} -gt 3 ]]; then
      dots::help_span "${word:0:${#word}-3}" "$role"; dots::help_span '...' punctuation
    else dots::help_span "$word" "$role"; fi
  done
}

# Emit a slice of already classified text, after the existing wrapper has chosen
# display boundaries. This avoids measuring or sanitizing ANSI as content.
dots::help_slice() {
  local start=$1 count=$2 offset=0 index text length take skip role
  for ((index=0;index<${#_DOTS_HELP_SPAN_TEXT[@]};index++)); do
    text=${_DOTS_HELP_SPAN_TEXT[index]}; length=${#text}
    if (( offset+length <= start )); then ((offset+=length)); continue; fi
    skip=$((start-offset)); (( skip >= 0 )) || skip=0
    take=$((length-skip)); (( take <= count )) || take=$count
    role=${_DOTS_HELP_SPAN_ROLE[index]}
    if [[ $DOTS_UI_RESET && ${_DOTS_HELP_STYLES[$role]:-} ]]; then
      printf '\e[%sm%s%s' "${_DOTS_HELP_STYLES[$role]}" "${text:skip:take}" "$DOTS_UI_RESET"
    else printf '%s' "${text:skip:take}"; fi
    ((count-=take, start+=take, offset+=length)); (( count > 0 )) || break
  done
  return 0
}

dots::help_error() {
  local text=$1
  dots::help_style 2 || return
  dots::text "$text"; text=$REPLY
  printf '%s%s%s ' "$DOTS_UI_RED" "$DOTS_UI_ERROR" "$DOTS_UI_RESET" >&2
  if [[ $DOTS_UI_RESET && ${_DOTS_HELP_STYLES[heading]:-} ]]; then
    printf '\e[%smUsage:%s ' "${_DOTS_HELP_STYLES[heading]}" "$DOTS_UI_RESET" >&2
  else printf 'Usage: ' >&2; fi
  dots::help_tokens "$text" syntax
  dots::help_slice 0 "${#text}" >&2
  printf '\n' >&2
}

# Match dots::line's builtin wrapping, returning text chunks instead of capturing
# a child shell's stdout. Token classification and style resolution stay in the
# invoking shell, even for a large command table.
dots::help_wrap() {
  local text=$1 indent=$2 columns=$3 part='' char size used=0 i room
  _DOTS_HELP_LINES=()
  room=$((columns-indent)); (( room >= 8 )) || room=8
  if (( ${#text} <= room )) && [[ $text != *[!\ -~]* ]]; then
    _DOTS_HELP_LINES=("$text"); return
  fi
  for ((i=0;i<${#text};i++)); do
    char=${text:i:1}; size=1; [[ $char == [\ -~] ]] || size=2
    if (( used+size > room && used )); then
      dots::breakline "$part" "$room"
      _DOTS_HELP_LINES+=("$REPLY")
      part=$DOTS_LINE_TAIL used=$DOTS_LINE_CELLS
    fi
    part+=$char; ((used+=size))
  done
  _DOTS_HELP_LINES+=("$part")
}

dots::help_line() {
  local text=$1 kind=${2:-syntax} indent=${3:-0} columns=${4:-${COLUMNS:-80}} first=${5:-} line offset=0 count
  dots::text "$text"; text=$REPLY
  [[ $columns =~ ^[0-9]{1,6}$ ]] || columns=80
  columns=$((10#$columns)); (( columns >= 20 )) || columns=20
  dots::help_style || return
  if ! dots::human && (( $# < 4 )); then
    printf '%*s%s\n' "$indent" '' "$text"; return
  fi
  if [[ ! $DOTS_UI_RESET ]]; then dots::line "$text" '' "$indent" "$columns" "$first"; return; fi
  dots::help_tokens "$text" "$kind"
  dots::help_wrap "$text" "$indent" "$columns"
  for line in "${_DOTS_HELP_LINES[@]}"; do
    [[ $first ]] || printf '%*s' "$indent" ''
    count=${#line}; dots::help_slice "$offset" "$count"; printf '\n'
    ((offset+=count)); first=''
  done
}

dots::help_row() {
  local label=$1 text=${2:-} kind=${3:-syntax} columns=${COLUMNS:-80} width=26 indent=2 gap=1 align=left
  local cells=0 char number i padding left=0 prefix_width configured=0 continuation=6
  dots::help_style || return
  if ! dots::human; then dots::row "$label" "$text"; return; fi
  [[ $columns =~ ^[0-9]{1,6}$ ]] || columns=80
  columns=$((10#$columns)); (( columns >= 20 )) || columns=20
  if dots::human && [[ ${_DOTS_FORMATTING[label_width]+set} ]]; then
    configured=1
    width=${_DOTS_FORMATTING[label_width]}; indent=${_DOTS_FORMATTING[indent]:-4}
    gap=${_DOTS_FORMATTING[label_gap]:-1}; align=${_DOTS_FORMATTING[alignment]:-left}
    indent=$((10#$indent)); gap=$((10#$gap))
    (( indent <= columns-8 )) || indent=$((columns-8))
    (( gap <= columns-indent-8 )) || gap=$((columns-indent-8))
    if [[ $width == *% ]]; then number=${width%\%}; width=$((columns*10#$number/100)); else width=$((10#$width)); fi
    (( width <= columns-indent-gap-8 )) || width=$((columns-indent-gap-8))
  elif (( columns < 60 )); then width=0; fi
  dots::text "$label"; label=$REPLY
  for ((i=0;i<${#label};i++)); do
    char=${label:i:1}; printf -v number '%d' "'$char"
    if (( number>=768 && number<=879 || number>=65024 && number<=65039 )); then :
    elif (( number>=4352 && number<=4447 || number>=11904 && number<=42191 || number>=44032 && number<=55203 || number>=63744 && number<=64255 || number>=65281 && number<=65376 || number>=127744 && number<=129791 )); then ((cells+=2))
    else ((cells+=1)); fi
  done
  padding=$((width-cells)); (( padding >= 0 )) || padding=0
  [[ $align != right ]] || left=$padding
  [[ $align != center ]] || left=$((padding/2))
  prefix_width=$((indent+cells+padding+gap))
  if (( configured )); then continuation=$((indent+width+gap)); fi
  if (( !configured && width == 0 || width && cells>width || prefix_width>columns-8 )); then
    dots::help_line "$label" "$kind" "$indent" "$columns"
    [[ ! $text ]] || dots::help_line "$text" prose "$continuation" "$columns"
  else
    printf '%*s' "$((indent+left))" ''
    dots::help_tokens "$label" "$kind"; dots::help_slice 0 "${#label}"
    printf '%*s' "$((padding-left+gap))" ''
    dots::help_line "$text" prose "$prefix_width" "$columns" first
  fi
}
