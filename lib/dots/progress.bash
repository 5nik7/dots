# Lazy, optional progress. Operations stay in the calling shell; only rendering
# runs in a child. No temp files, stdin reads, cursor hiding, or parent traps.
# shellcheck disable=SC2034
dots::progress_enabled() {
  [[ ${DOTS_PROGRESS-auto} == auto && ${DOTS_PROGRESS_HUMAN:-0} == 1 &&
     -t 1 && -t 2 && ${TERM:-dumb} != dumb ]]
}

dots::progress_clean() {
  local text=$1 char code i
  DOTS_PROGRESS_TEXT=''
  for ((i=0; i<${#text}; i++)); do
    char=${text:i:1}
    printf -v code '%d' "'$char"
    # ASCII display labels make terminal width predictable, even for wide names.
    if ((code < 32 || code > 126)); then printf -v char '\\u%04x' "$code"; fi
    DOTS_PROGRESS_TEXT+=$char
  done
}

dots::progress_worker() (
  local parent=$1 label=$2 completed=${3:-0} total=${4:-0}
  local line='' width=${COLUMNS:-80} drawn=0 ticks=0 frame=0 status marker suffix size filled text
  local cyan='' blue='' reset='' glyphs="|/-\\" bar='#'
  # Workers must not retain transaction locks held by their parent.
  exec 8>&- 9>&-
  # Noninteractive Bash does not populate COLUMNS from its terminal.
  if command -v stty >/dev/null 2>&1; then
    read -r _ width < <(stty size <&2 2>/dev/null) || width=${COLUMNS:-80}
  fi
  [[ $width =~ ^[0-9]{1,4}$ ]] || width=80
  width=$((10#$width))
  ((width > 1 && width < 10000)) || width=80
  ((width-=1))
  if [[ ${DOTS_COLOR:-auto} == always || ( ${DOTS_COLOR:-auto} == auto && -z ${NO_COLOR:-} ) ]]; then
    cyan=$'\e[96m' blue=$'\e[94m' reset=$'\e[0m'
  fi
  if [[ ${DOTS_ICONS:-auto} == auto || ${DOTS_ICONS:-auto} == always ]]; then glyphs='⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'; bar='━'; fi
  trap 'if ((drawn)); then printf "\r%*s\r" "$drawn" "" >&2; fi' EXIT
  trap 'exit 0' TERM HUP
  while kill -0 "$parent" 2>/dev/null; do
    status=0
    IFS= read -r -t 0.1 line || status=$?
    if ((status == 0)); then
      [[ $line != stop ]] || break
      IFS=$'\t' read -r completed total label <<< "$line"
    elif ((status <= 128)); then break
    fi
    [[ $completed =~ ^[0-9]{1,9}$ && $total =~ ^[0-9]{1,9}$ ]] || { completed=0; total=0; }
    completed=$((10#$completed)); total=$((10#$total))
    ((completed <= total)) || completed=$total
    ((status <= 128)) || ((ticks+=1))
    if [[ -n ${DOTS_PROGRESS_STARTED:-} && -n ${EPOCHREALTIME:-} ]]; then
      local now=${EPOCHREALTIME/./} start=${DOTS_PROGRESS_STARTED/./}
      ((now - start >= 500000)) || continue
    else ((ticks >= 5)) || continue; fi
    suffix=''
    if ((total > 0)); then
      size=$((width / 5)); ((size <= 16)) || size=16; ((size >= 3)) || size=3
      filled=$((size * completed / total))
      printf -v marker '%*s' "$filled" ''; marker=${marker// /$bar}
      printf -v text '%*s' "$((size-filled))" ''; marker="[$marker${text// /-}]"
      suffix=" $completed/$total"
    else marker=${glyphs:frame%${#glyphs}:1}; fi
    text="$marker$suffix $label"; text=${text:0:width}
    printf '\r%s%s%s' "$cyan" "${text:0:${#marker}+${#suffix}}" "$blue" >&2
    printf '%s%s' "${text:${#marker}+${#suffix}}" "$reset" >&2
    if ((${#text} < drawn)); then printf '%*s' "$((drawn-${#text}))" '' >&2; fi
    drawn=${#text}; ((frame+=1))
  done
)

dots::progress_start() {
  local parent=$BASHPID
  dots::progress_enabled || return 0
  if [[ -n ${DOTS_PROGRESS_FD:-} ]]; then dots::progress_update "$@"; return 0; fi
  dots::progress_clean "$1"
  DOTS_PROGRESS_STARTED=${DOTS_PROGRESS_STARTED:-${EPOCHREALTIME:-}}
  # A process substitution gives the worker a private control pipe, never stdin.
  if exec {DOTS_PROGRESS_FD}> >(dots::progress_worker "$parent" "$DOTS_PROGRESS_TEXT" "${2:-0}" "${3:-0}"); then
    DOTS_PROGRESS_PID=$!
  else DOTS_PROGRESS_FD=''; fi
  return 0
}

dots::progress_update() {
  [[ -n ${DOTS_PROGRESS_FD:-} ]] || return 0
  dots::progress_clean "$1"
  # A failed renderer cannot SIGPIPE the operation's shell.
  (printf '%s\t%s\t%s\n' "${2:-0}" "${3:-0}" "$DOTS_PROGRESS_TEXT" >&"$DOTS_PROGRESS_FD") 2>/dev/null || dots::progress_stop
  return 0
}

dots::progress_stop() {
  [[ -n ${DOTS_PROGRESS_FD:-} ]] || return 0
  (printf 'stop\n' >&"$DOTS_PROGRESS_FD") 2>/dev/null || :
  exec {DOTS_PROGRESS_FD}>&-
  wait "${DOTS_PROGRESS_PID:-}" 2>/dev/null || :
  DOTS_PROGRESS_FD='' DOTS_PROGRESS_PID=''
  return 0
}

dots::progress_run() {
  local label=$1 rc=0 owned=0
  shift
  [[ -n ${DOTS_PROGRESS_FD:-} ]] || owned=1
  dots::progress_start "$label"
  "$@" || rc=$?
  (( ! owned )) || dots::progress_stop
  return "$rc"
}

# Prompt-capable children retain foreground access; a static phase line cannot
# race a credential/signing prompt. Called before the child's own redirections.
dots::progress_external() {
  dots::progress_stop
  if dots::progress_enabled; then
    dots::progress_clean "$1"
    dots::style 2
    printf '%s%s%s\n' "$DOTS_UI_BLUE" "$DOTS_PROGRESS_TEXT" "$DOTS_UI_RESET" >&2
  fi
}
