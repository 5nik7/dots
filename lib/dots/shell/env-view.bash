# Human diagnostics only. Values and origins are resolved by bin/dots-env.
# shellcheck shell=bash disable=SC2034,SC2154

_dots_env_text() {
  local text=$1 character code i probe='ü'
  REPLY=''
  # In byte-oriented locales, escape non-ASCII as well to avoid splitting UTF-8.
  if (( ${#probe} != 1 )) && [[ $text == *[!\ -~]* ]]; then
    printf -v REPLY '%q' "$text"
    return
  fi
  for ((i=0; i<${#text}; i++)); do
    character=${text:i:1}
    printf -v code '%d' "'$character"
    if (( code < 32 || (code >= 127 && code < 160) )); then
      printf -v character '\\u%04x' "$code"
    fi
    REPLY+=$character
  done
}

_dots_env_size() {
  local text=$1 character code i
  REPLY=0
  for ((i=0; i<${#text}; i++)); do
    character=${text:i:1}
    printf -v code '%d' "'$character"
    # Conservatively allow two cells for non-ASCII without a wcwidth dependency.
    (( REPLY += code < 128 ? 1 : 2 ))
  done
}

_dots_env_line() {
  local text=$1 color=$2 indent=${3:-4} part='' character code size cells=0 i head
  local room=$((_dots_env_columns - indent))
  for ((i=0; i<${#text}; i++)); do
    character=${text:i:1}
    printf -v code '%d' "'$character"
    size=1; (( code < 128 )) || size=2
    if (( cells + size > room )); then
      head=$part
      if [[ $part == */* && ${part%/*} ]]; then
        head=${part%/*}/
        part=${part##*/}
      else part=''; fi
      printf '%*s%s%s%s\n' "$indent" '' "$color" "$head" "$DOTS_UI_RESET"
      _dots_env_size "$part"; cells=$REPLY
    fi
    part+=$character; (( cells += size ))
  done
  printf '%*s%s%s%s\n' "$indent" '' "$color" "$part" "$DOTS_UI_RESET"
}

_dots_env_row() {
  local key=$1 kind=$2 value source color=$DOTS_UI_RESET length resource_kind=''
  _dots_env_text "${values[$key]}"; value=$REPLY
  _dots_env_text "${origins[$key]}"; source=$REPLY
  if [[ $kind == bool ]]; then
    if [[ $value == 1 ]]; then value+=' (enabled)'; else value+=' (disabled)'; fi
  elif [[ $kind == path ]]; then
    if [[ ! -e ${values[$key]} && ! -L ${values[$key]} ]]; then
      resource_kind=dir; [[ $key != DOTS_CONFIG_FILE ]] || resource_kind=file
    fi
    dots::resource "${values[$key]}" "$value" "$resource_kind"
    value=$DOTS_RESOURCE_TEXT; color=$DOTS_RESOURCE_STYLE
  fi
  _dots_env_size "$value"; length=$REPLY
  if (( 2 + 26 + 2 + length + 2 + ${#source} + 2 <= _dots_env_columns )); then
    printf '  %s%-26s%s  %s%s%s  %s[%s]%s\n' "$DOTS_UI_BLUE" "$key" "$DOTS_UI_RESET" \
      "$color" "$value" "$DOTS_UI_RESET" "$DOTS_UI_DIM" "$source" "$DOTS_UI_RESET"
  else
    _dots_env_line "$key" "$DOTS_UI_BLUE" 2
    _dots_env_line "$value" "$color"
    _dots_env_line "Source: $source" "$DOTS_UI_DIM"
  fi
}

_dots_env_render() {
  local key kind value description field relative rows _dots_env_columns=${COLUMNS:-}
  if [[ ! $_dots_env_columns =~ ^[0-9]+$ ]] || (( 10#${_dots_env_columns:-0} == 0 )); then
    _dots_env_columns=80
    if [[ -t 1 ]] && command -v stty >/dev/null 2>&1; then
      { read -r rows _dots_env_columns < <(stty size <&3 2>/dev/null); } 3<&1
    fi
  fi
  [[ $_dots_env_columns =~ ^[0-9]+$ ]] || _dots_env_columns=80
  _dots_env_columns=$((10#$_dots_env_columns))
  (( _dots_env_columns >= 20 )) || _dots_env_columns=20
  dots::heading 'Dots environment'
  printf '\n'; dots::heading 'Current theme'
  _dots_env_row DOTS_THEME_ID id
  printf '\n'; dots::heading 'Settings'
  while IFS=$'\t' read -r key kind value description; do
    _dots_env_row "$key" "$kind"
  done < "$DOTS/lib/dots/shell/settings.tsv"
  printf '\n'; dots::heading 'Paths'
  while IFS=$'\t' read -r key field relative; do
    [[ $key == - ]] || _dots_env_row "$key" path
  done < "$DOTS/lib/dots/shell/paths.tsv"
  _dots_env_row DOTS_CONFIG_FILE path
  _dots_env_row DOTS_STATE_DIR path
}
