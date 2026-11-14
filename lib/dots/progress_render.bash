# Inert progress rows shared by Bash operations and Bash/Zsh compatibility helpers.
# Callers resolve preferences once and own their terminal lifecycle. This file is
# lazy-loaded; rendering uses shell builtins only and never queries configuration.
# Caller-local associative arrays carry the resolved spans.
# shellcheck disable=SC2034,SC2004
_dots_progress_clean() {
  local text=$1 char code i
  REPLY=''
  for ((i=0; i<${#text}; i++)); do
    char=${text:$i:1}
    printf -v code '%d' "'$char"
    if ((code<32 || code>126)); then printf -v char '\\u%04x' "$code"; fi
    REPLY+=$char
  done
}

_dots_progress_init() {
  local name key value fallback code
  _dpr_color=$1
  typeset -gA _DOTS_STYLE_ICONS _DOTS_STYLE_COLORS
  for name in filled empty left right; do
    case $name in filled) fallback='━' ;; empty) fallback='-' ;; left) fallback='[' ;; right) fallback=']' ;; esac
    key=progress.bar.$name
    value=${_DOTS_STYLE_ICONS[$key]-$fallback}
    if [[ -z $value && ( $name == left || $name == right ) ]]; then :
    elif [[ ${#value} != 1 || $value == *[[:cntrl:]]* ]]; then value=$fallback
    else
      # Config validates display cells. Bound direct array overrides as well;
      # reject the usual combining/full-width ranges without external helpers.
      printf -v code '%d' "'$value"
      if (( (code>=768 && code<=879) || (code>=4352 && code<=4607) ||
            (code>=13312 && code<=19903) || (code>=19968 && code<=40959) ||
            (code>=44032 && code<=55203) || (code>=55216 && code<=55295) ||
            (code>=65024 && code<=65039) ||
            (code>=65281 && code<=65376) || (code>=128512 && code<=128591) )); then value=$fallback; fi
    fi
    if [[ $2 != 1 && -n $value ]]; then
      printf -v code '%d' "'$value"
      if ((code>126)); then
        case $name in filled) value='#' ;; empty) value='-' ;; left) value='[' ;; right) value=']' ;; esac
      fi
    fi
    _dpr_symbols[$name]=$value
  done
  for name in filled empty surround percentage marker label; do
    case $name in
      filled|percentage|marker) fallback=${_DOTS_STYLE_COLORS[96]:-96} ;;
      label) fallback=${_DOTS_STYLE_COLORS[94]:-94} ;;
      *) fallback=${_DOTS_STYLE_COLORS[90]:-90} ;;
    esac
    key=progress.$name
    value=${_DOTS_STYLE_COLORS[$key]-$fallback}
    # Empty means an explicitly unstyled span. SGR fields are inert numeric data.
    [[ -z $value || ( ${#value} -le 80 && $value != *[!0-9\;]* ) ]] || value=$fallback
    _dpr_colors[$name]=$value
  done
}

_dots_progress_piece() {
  [[ -n $1 ]] || return 0
  _dpr_plain+=$1
  if [[ $_dpr_color == 1 && -n $2 ]]; then
    _dpr_painted+=$'\e['"$2"m"$1"$'\e[0m'
  else _dpr_painted+=$1; fi
}

_dots_progress_bar() {
  local value=$1 size=$2 frame=$3 denominator=${4:-1000000} filled=0 point=0 before='' middle='' after=''
  ((size>0)) || return 0
  if ((value<0)); then
    if ((size>1)); then
      point=$((frame%(2*(size-1)))); ((point<size)) || point=$((2*(size-1)-point))
    fi
    printf -v before '%*s' "$point" ''
    middle=${_dpr_symbols[filled]}
    printf -v after '%*s' "$((size-point-1))" ''
  else
    filled=$((size*value/denominator))
    printf -v middle '%*s' "$filled" ''
    middle=${middle// /"${_dpr_symbols[filled]}"}
    printf -v after '%*s' "$((size-filled))" ''
  fi
  _dots_progress_piece "${_dpr_symbols[left]}" "${_dpr_colors[surround]}"
  _dots_progress_piece "${before// /"${_dpr_symbols[empty]}"}" "${_dpr_colors[empty]}"
  _dots_progress_piece "$middle" "${_dpr_colors[filled]}"
  _dots_progress_piece "${after// /"${_dpr_symbols[empty]}"}" "${_dpr_colors[empty]}"
  _dots_progress_piece "${_dpr_symbols[right]}" "${_dpr_colors[surround]}"
}

# Arguments: available cells, mode, frame, spinner, overall millionths,
# current completed/total, current step/steps, sanitized activity.
_dots_progress_rows() {
  local width=$1 mode=$2 frame=$3 spinner=$4 overall=$5 completed=$6 total=$7 step=$8 steps=$9
  shift 9
  local label=$1 percent="$((overall/10000))%" size surrounds prefix='' suffix='' current=-1 budget reserve=0 separator='' gap=0 wants_bar=0
  local _dpr_plain='' _dpr_painted=''
  ((width>0)) || width=1
  [[ $_dpr_color != 1 ]] || _dpr_painted=$'\e[0m'
  surrounds=$((${#_dpr_symbols[left]}+${#_dpr_symbols[right]}))
  size=$((width-surrounds-1-${#percent}))
  if [[ $mode != spinner ]] && ((size>0)); then
    _dots_progress_bar "$overall" "$size" "$frame"
    _dots_progress_piece ' ' ''
  fi
  _dots_progress_piece "${percent:0:$width}" "${_dpr_colors[percentage]}"
  _dpr_top=$_dpr_painted _dpr_top_plain=$_dpr_plain
  _dpr_plain='' _dpr_painted=''
  [[ $_dpr_color != 1 ]] || _dpr_painted=$'\e[0m'
  if [[ $mode == spinner || $mode == both ]]; then prefix=$spinner; fi
  if ((steps>0)); then
    [[ -z $prefix ]] || prefix+=' '
    prefix+="$step/$steps"; separator=' · '
  elif [[ -n $prefix ]]; then separator=' '; fi
  ((total<=0)) || { current=$completed; suffix=" $((100*completed/total))%"; }
  prefix=${prefix:0:$width}
  if [[ $mode == bar || ( $mode == both && $total -gt 0 ) ]]; then
    wants_bar=1; reserve=$((8+surrounds+1))
  fi
  budget=$((width-${#prefix}-${#separator}-${#suffix}-reserve)); ((budget>=0)) || budget=0
  label=${label:0:$budget}
  _dots_progress_piece "$prefix" "${_dpr_colors[marker]}"
  if [[ -n $label ]]; then
    _dots_progress_piece "$separator" "${_dpr_colors[marker]}"
    _dots_progress_piece "$label" "${_dpr_colors[label]}"
  fi
  if ((wants_bar)); then
    [[ -z $_dpr_plain ]] || gap=1
    size=$((width-${#_dpr_plain}-gap-${#suffix}-surrounds))
    if ((size>0)); then
      ((gap==0)) || _dots_progress_piece ' ' ''
      _dots_progress_bar "$current" "$size" "$frame" "${total:-1}"
    fi
  fi
  budget=$((width-${#_dpr_plain})); ((budget>=0)) || budget=0
  _dots_progress_piece "${suffix:0:$budget}" "${_dpr_colors[percentage]}"
  _dpr_bottom=$_dpr_painted _dpr_bottom_plain=$_dpr_plain
}
