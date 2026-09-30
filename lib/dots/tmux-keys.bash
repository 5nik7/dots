# Read-only tmux key reference. No shell configuration or returned code is sourced.
# shellcheck source-path=SCRIPTDIR
# shellcheck source=ui.bash
source "${BASH_SOURCE[0]%/*}/ui.bash"

# Decode exactly one tmux q|a token, never shell expansions. Control escapes stay
# visible (\n, \033, etc.); ordinary quoted/escaped punctuation becomes literal.
dots_tmux::decode() {
  local value=$1 quote='' char next i
  REPLY=''
  for ((i=0; i<${#value}; i++)); do
    char=${value:i:1}
    if [[ $char == $'\\' && $quote != "'" ]]; then
      ((i+=1))
      (( i < ${#value} )) || return 1
      next=${value:i:1}
      case $next in
        [abefnrtv0-7]) REPLY+="\\$next" ;;
        *) REPLY+=$next ;;
      esac
    elif [[ $quote && $char == "$quote" ]]; then
      quote=''
    elif [[ ! $quote && ( $char == '"' || $char == "'" ) ]]; then
      quote=$char
    elif [[ ! $quote && $char == [[:space:]] ]]; then
      return 1
    else
      REPLY+=$char
    fi
  done
  [[ ! $quote ]]
}

dots_tmux::safe() {
  local value=$1 char code escaped i j count next second valid
  local LC_ALL=C probe='→' bytes=0
  # Conventional libc uses bytes in C; Android may still iterate codepoints.
  # Preserve valid UTF-8 as a unit rather than escaping continuation bytes.
  (( ${#probe} == 1 )) || bytes=1
  REPLY=''
  for ((i=0; i<${#value}; i++)); do
    char=${value:i:1}
    printf -v code '%d' "'$char"
    if (( bytes && code >= 194 && code <= 244 )); then
      count=2
      (( code < 224 )) || count=3
      (( code < 240 )) || count=4
      valid=1 second=0
      for ((j=1; j<count; j++)); do
        if (( i+j >= ${#value} )); then valid=0; break; fi
        printf -v next '%d' "'${value:i+j:1}"
        (( j != 1 )) || second=$next
        (( next >= 128 && next <= 191 )) || valid=0
      done
      # Reject overlong encodings, surrogates, and values above U+10FFFF.
      if (( (code == 224 && second < 160) || (code == 237 && second > 159) ||
            (code == 240 && second < 144) || (code == 244 && second > 143) )); then valid=0; fi
      if (( valid )); then
        if (( code == 194 && second <= 159 )); then
          printf -v escaped '\\x%02x' "$second"
          REPLY+=$escaped
        else
          REPLY+=${value:i:count}
        fi
        ((i+=count-1))
        continue
      fi
    fi
    if (( code < 32 || (code >= 127 && code <= 159) || (bytes && code >= 128) )); then
      printf -v escaped '\\x%02x' "$code"
      REPLY+=$escaped
    else
      REPLY+=$char
    fi
  done
}

dots_tmux::help() {
  dots::heading 'dots menu tmux keys'
  printf '%s\n' 'Browse described live tmux bindings (including defaults and plugins).' '' \
    'Usage: dots-menu-tmux-keys [--print]' '       dots menu tmux keys [--print]' ''
  dots::row '--print' 'Print without a pager; redirected output is plain by default.'
  dots::row '-h, --help' 'Show help without contacting tmux.'
  printf '\n%s\n' 'Requires tmux with list-keys -F and q|a formats; less is optional.' \
    'Pager: / search, n next, q close. Bindings are never executed.' \
    'Use DOTS_COLOR/DOTS_ICONS=auto|always|never, or dots prefix flags.'
}

# All records are collected and validated before any stdout is produced.
dots_tmux::collect() {
  local data line table key note rest value option i j found item
  local format=$'dots-tmux-keys-v1\t#{q|a:key_table}\t#{q|a:key_string}\t#{q|a:key_note}'
  local -a target=(-g) unordered=()
  DT_KEYS_TABLES=() DT_KEYS_ROW_TABLE=() DT_KEYS_KEYS=() DT_KEYS_NOTES=() DT_KEYS_PREFIXES=()
  command -v tmux >/dev/null 2>&1 || { DT_KEYS_ERROR='tmux is required to list keybindings.'; return 1; }
  # -N never starts a server; -u preserves UTF-8 and field separators even in
  # an ASCII client locale. q|a escapes embedded tabs/newlines in field values.
  if ! data=$(tmux -N -u list-keys -F "$format" 2>/dev/null); then
    DT_KEYS_ERROR='Cannot read tmux bindings. Use a running server and tmux with list-keys -F support.'
    return 1
  fi
  while IFS= read -r line; do
    [[ $line ]] || continue
    [[ $line == $'dots-tmux-keys-v1\t'* ]] || return 1
    rest=${line#*$'\t'}
    [[ $rest == *$'\t'* ]] || return 1
    table=${rest%%$'\t'*}; rest=${rest#*$'\t'}
    [[ $rest == *$'\t'* ]] || return 1
    key=${rest%%$'\t'*}; note=${rest#*$'\t'}
    [[ $note != *$'\t'* && $table && $key && $note ]] || return 1
    dots_tmux::decode "$table" || return 1; table=$REPLY
    dots_tmux::decode "$key" || return 1; key=$REPLY
    dots_tmux::decode "$note" || return 1; note=$REPLY
    [[ $table && $key ]] || return 1
    [[ $note ]] || continue
    dots_tmux::safe "$table"; table=$REPLY
    dots_tmux::safe "$key"; key=$REPLY
    dots_tmux::safe "$note"; note=$REPLY
    DT_KEYS_ROW_TABLE+=("$table") DT_KEYS_KEYS+=("$key") DT_KEYS_NOTES+=("$note")
    found=0
    for item in "${unordered[@]}"; do [[ $item != "$table" ]] || found=1; done
    (( found )) || unordered+=("$table")
  done <<< "$data"
  # Stable table ordering without invoking sort or indexing associative arrays
  # with user-controlled strings. Preserve tmux's order inside each table.
  for item in prefix root copy-mode-vi copy-mode; do
    for table in "${unordered[@]}"; do
      [[ $table != "$item" ]] || DT_KEYS_TABLES+=("$table")
    done
  done
  for ((i=1; i<${#unordered[@]}; i++)); do
    value=${unordered[i]}; j=$i
    while (( j > 0 )) && [[ ${unordered[j-1]} > "$value" ]]; do
      unordered[j]=${unordered[j-1]}; ((j-=1))
    done
    unordered[j]=$value
  done
  for table in "${unordered[@]}"; do
    case $table in prefix|root|copy-mode-vi|copy-mode) continue ;; esac
    DT_KEYS_TABLES+=("$table")
  done
  [[ ! ${TMUX_PANE:-} ]] || target=(-t "$TMUX_PANE")
  for option in prefix prefix2; do
    if ! value=$(tmux -N -u show-options -v "${target[@]}" "$option" 2>/dev/null); then
      DT_KEYS_ERROR='Cannot read tmux prefixes. Check the current pane/server context.'
      return 1
    fi
    [[ $value && $value != None ]] || continue
    dots_tmux::safe "$value"; value=$REPLY
    [[ ${DT_KEYS_PREFIXES[0]:-} != "$value" ]] || continue
    DT_KEYS_PREFIXES+=("$value")
  done
}

# Compact reference rows deliberately do not use dots::row's narrow-screen
# stacked layout. Keep the description adjacent to its key at every width.
dots_tmux::row() {
  dots::style
  printf '  %s%-*s%s  %s\n' "$DOTS_UI_BLUE" "$3" "$1" "$DOTS_UI_RESET" "$2"
}

dots_tmux::render() {
  local table label prefix='' value i width length
  dots::heading "Tmux keybindings (${#DT_KEYS_KEYS[@]})"
  for value in "${DT_KEYS_PREFIXES[@]}"; do prefix+="${prefix:+ or }$value"; done
  dots_tmux::row 'Prefix' "${prefix:-None (disabled)}" 6
  if (( ${#DT_KEYS_KEYS[@]} == 0 )); then
    printf '\n%s\n' 'No described tmux keybindings found.' 'Add descriptions with bind -N "Description" ...'
    return
  fi
  if (( DT_KEYS_PAGER )); then
    printf '\n%s\n' '/ search | n next | q close'
  fi
  for table in "${DT_KEYS_TABLES[@]}"; do
    case $table in
      prefix) label='prefix (Prefix + key)' ;;
      root) label='root (no prefix)' ;;
      *) label=$table ;;
    esac
    printf '\n'; dots::heading "$label"
    width=1
    for ((i=0; i<${#DT_KEYS_KEYS[@]}; i++)); do
      [[ ${DT_KEYS_ROW_TABLE[i]} == "$table" ]] || continue
      length=${#DT_KEYS_KEYS[i]}
      (( length <= width )) || width=$length
    done
    # Avoid making every row wide just because one mouse/chord key is long.
    (( width <= 12 )) || width=12
    for ((i=0; i<${#DT_KEYS_KEYS[@]}; i++)); do
      [[ ${DT_KEYS_ROW_TABLE[i]} != "$table" ]] || dots_tmux::row "${DT_KEYS_KEYS[i]}" "${DT_KEYS_NOTES[i]}" "$width"
    done
  done
}

dots_tmux::main() {
  local print_only=0 arg body status render_color render_icons
  local -a DT_KEYS_TABLES DT_KEYS_ROW_TABLE DT_KEYS_KEYS DT_KEYS_NOTES DT_KEYS_PREFIXES
  local DT_KEYS_PAGER=0
  local DT_KEYS_ERROR='Cannot decode tmux bindings. Verify tmux supports list-keys -F and q|a formats; no view was produced.'
  # Presentation overrides below are scoped to this invocation and its children.
  local DOTS_COLOR=${DOTS_COLOR:-auto} DOTS_ICONS=${DOTS_ICONS:-auto}
  for arg in "$@"; do
    case $arg in
      --print) print_only=1 ;;
      -h|--help) dots_tmux::help; return 0 ;;
      *) dots_tmux::safe "$arg"; dots::error "Unknown argument: $REPLY. Use --help."; return 2 ;;
    esac
  done
  if ! dots_tmux::collect; then
    dots::error "$DT_KEYS_ERROR"
    return 1
  fi
  if [[ -t 0 && -t 1 && ${TERM:-dumb} != dumb ]] && (( ! print_only && ${#DT_KEYS_KEYS[@]} )); then
    if command -v less >/dev/null 2>&1; then DT_KEYS_PAGER=1
    else dots::warning 'less is unavailable; printing bindings without a pager.'
    fi
  fi
  # Resolve TTY policy before command substitution / pager pipes hide the TTY.
  dots::style
  if [[ $DOTS_UI_RESET ]]; then render_color=always; else render_color=never; fi
  if [[ $DOTS_UI_INFO == '[i]' ]]; then render_icons=never; else render_icons=always; fi
  body=$(DOTS_COLOR=$render_color DOTS_ICONS=$render_icons dots_tmux::render) || return 1
  if (( ! DT_KEYS_PAGER )); then printf '%s\n' "$body"; return; fi
  # A here-string avoids a producer SIGPIPE when the user quits early. No file,
  # shell hooks, inherited option string or second backend is used.
  LESS='' LESSOPEN='' LESSCLOSE='' LESSSECURE=1 less -R <<< "$body"
  status=$?
  if (( status != 0 && status != 130 )); then
    dots::error 'The tmux keybinding pager failed.'
    return 1
  fi
  return "$status"
}
