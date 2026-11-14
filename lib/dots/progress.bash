# Lazy, optional progress. Operations stay in the calling shell; only rendering
# runs in a child. No temp files, stdin reads, cursor hiding, or parent traps.
# shellcheck disable=SC2034
dots::progress_enabled() {
  [[ ${DOTS_PROGRESS_HUMAN:-0} == 1 && -t 1 && -t 2 && ${TERM:-dumb} != dumb ]] || return 1
  DOTS_PROGRESS_MODE=${DOTS_PROGRESS-auto}
  if [[ $DOTS_PROGRESS_MODE == auto ]]; then
    if declare -F dots::settings >/dev/null; then dots::settings || return 1; fi
    DOTS_PROGRESS_MODE=${_DOTS_CLI_PROGRESS:-both}
  fi
  case $DOTS_PROGRESS_MODE in spinner|bar|both) return 0 ;; *) return 1 ;; esac
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

# The worker consumes immutable frame snapshots. Sequence arithmetic stays in
# the operation shell, so presentation cannot reorder or complete work.
dots::progress_worker() {
  local parent=$1 line='' width=${COLUMNS:-80} old_width=0 drawn=0 ticks=0 frame=0 status geometry_dirty=0
  local label='' completed=0 total=0 overall=0 unit=step group=1 groups=1 step=0 steps=0
  local glyphs="|/-\\" spinner top bottom color=0 icons=0
  local _dpr_color _dpr_top _dpr_bottom _dpr_top_plain _dpr_bottom_plain
  local -A _dpr_symbols _dpr_colors
  # shellcheck source=lib/dots/progress_render.bash
  source "${BASH_SOURCE[0]%/*}/progress_render.bash" || exit 0
  exec 8>&- 9>&-
  dots::_progress_width() {
    local candidate=${COLUMNS:-80}
    if command -v stty >/dev/null 2>&1; then
      read -r _ candidate < <(stty size <&2 2>/dev/null) || candidate=${COLUMNS:-80}
    fi
    [[ $candidate =~ ^[0-9]{1,4}$ ]] || candidate=80
    width=$((10#$candidate)); ((width > 0 && width < 10000)) || width=80
    ((width-=1)); ((width>0)) || width=1
  }
  dots::_progress_clear() {
    ((drawn)) || return 0
    if ((geometry_dirty)); then dots::_progress_width; geometry_dirty=0; fi
    local rows=2 i columns=$((width+1))
    if ((old_width > width && width > 0)); then
      rows=$((((${#top}+columns-1)/columns)+ ((${#bottom}+columns-1)/columns)))
      ((rows >= 2)) || rows=2
    fi
    # Work back from the current row. Saved absolute cursor coordinates become
    # stale when terminal reflow moves the indicator toward scrollback.
    printf '\r\033[2K' >&2
    for ((i=1;i<rows;i++)); do printf '\033[1A\r\033[2K' >&2; done
    printf '\r' >&2
    drawn=0
  }
  dots::_progress_width
  if [[ ${DOTS_COLOR:-auto} == always || ( ${DOTS_COLOR:-auto} == auto && -z ${NO_COLOR:-} ) ]]; then color=1; fi
  if [[ ${DOTS_ICONS:-auto} == auto || ${DOTS_ICONS:-auto} == always ]]; then glyphs='⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'; icons=1; fi
  _dots_progress_init "$color" "$icons"
  trap 'dots::_progress_clear' EXIT
  trap 'exit 0' TERM HUP
  trap 'geometry_dirty=1' WINCH
  while kill -0 "$parent" 2>/dev/null; do
    status=0
    IFS= read -r -t 0.1 line || status=$?
    if ((status == 0)); then
      [[ $line != stop ]] || break
      IFS=$'\t' read -r overall unit group groups step steps completed total label <<< "$line"
    elif ((status <= 128)); then break
    fi
    [[ $overall =~ ^[0-9]{1,7}$ && $group =~ ^[0-9]{1,9}$ && $groups =~ ^[0-9]{1,9}$ && $step =~ ^[0-9]{1,9}$ && $steps =~ ^[0-9]{1,9}$ ]] || continue
    [[ $completed =~ ^[0-9]{1,9}$ && $total =~ ^[0-9]{1,9}$ ]] || { completed=0; total=0; }
    completed=$((10#$completed)); total=$((10#$total)); ((completed<=total)) || completed=$total
    ((status <= 128)) || ((ticks+=1))
    if [[ -n ${DOTS_PROGRESS_STARTED:-} && -n ${EPOCHREALTIME:-} ]]; then
      local now=${EPOCHREALTIME/./} start=${DOTS_PROGRESS_STARTED/./}
      ((now-start >= 500000)) || continue
    else ((ticks>=5)) || continue; fi
    # Read geometry on actual frames, not from command output. SIGWINCH merely
    # marks the next frame dirty; it never interrupts operation control flow.
    if ((geometry_dirty)); then dots::_progress_width; geometry_dirty=0; fi
    dots::_progress_clear
    spinner=${glyphs:frame%${#glyphs}:1}
    _dots_progress_rows "$width" "$DOTS_PROGRESS_MODE" "$frame" "$spinner" "$overall" "$completed" "$total" "$step" "$steps" "$label"
    top=$_dpr_top_plain bottom=$_dpr_bottom_plain
    # Reserve the second row before painting, including at the screen bottom.
    printf '\r\n\r\033[1A\r' >&2
    printf '\r%s\n\r%s' "$_dpr_top" "$_dpr_bottom" >&2
    drawn=1 old_width=$width; ((frame+=1))
  done
}

dots::progress_start() {
  local parent=$BASHPID
  DOTS_PROGRESS_LABEL=$1 DOTS_PROGRESS_COMPLETED=${2:-0} DOTS_PROGRESS_TOTAL=${3:-0}
  dots::progress_enabled || return 0
  # A nested shell owns its worker, not an inherited descriptor into its parent.
  if [[ ${DOTS_PROGRESS_RENDER_OWNER:-$parent} != "$parent" && -n ${DOTS_PROGRESS_FD:-} ]]; then
    exec {DOTS_PROGRESS_FD}>&-
    DOTS_PROGRESS_FD='' DOTS_PROGRESS_PID=''
  fi
  if [[ -z ${DOTS_PROGRESS_FD:-} ]]; then
    if ((${DOTS_PROGRESS_DEPTH:-0}==0)); then
      DOTS_PROGRESS_OVERALL=0 DOTS_PROGRESS_GROUP=1 DOTS_PROGRESS_GROUPS=1 DOTS_PROGRESS_UNIT=step
      DOTS_PROGRESS_STEP=0 DOTS_PROGRESS_STEPS=0
    fi
    DOTS_PROGRESS_STARTED=${DOTS_PROGRESS_STARTED:-${EPOCHREALTIME:-}}
    DOTS_PROGRESS_RENDER_OWNER=$parent
    if exec {DOTS_PROGRESS_FD}> >(dots::progress_worker "$parent"); then DOTS_PROGRESS_PID=$!
    else DOTS_PROGRESS_FD=''; fi
  fi
  dots::progress_update "$@"
  return 0
}

dots::progress_update() {
  DOTS_PROGRESS_LABEL=$1 DOTS_PROGRESS_COMPLETED=${2:-0} DOTS_PROGRESS_TOTAL=${3:-0}
  [[ -n ${DOTS_PROGRESS_FD:-} ]] || return 0
  dots::progress_clean "$1"
  # A failed renderer cannot SIGPIPE the operation's shell.
  (printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
    "${DOTS_PROGRESS_OVERALL:-0}" "${DOTS_PROGRESS_UNIT:-step}" \
    "${DOTS_PROGRESS_GROUP:-1}" "${DOTS_PROGRESS_GROUPS:-1}" \
    "${DOTS_PROGRESS_STEP:-0}" "${DOTS_PROGRESS_STEPS:-0}" \
    "${2:-0}" "${3:-0}" "$DOTS_PROGRESS_TEXT" >&"$DOTS_PROGRESS_FD") 2>/dev/null || dots::progress_stop
  return 0
}

# Integer millionths give bounded, monotonic arithmetic without subprocesses.
# A sequence freezes its denominator before any child progress is credited.
dots::progress_sequence_start() {
  local label=$1 total=$2 unit=${3:-step} depth=${DOTS_PROGRESS_DEPTH:-0}
  [[ $total =~ ^[0-9]{1,9}$ ]] || total=0
  total=$((10#$total))
  [[ $unit =~ ^[a-zA-Z][a-zA-Z_-]*$ ]] || unit=step
  if ((depth==0)); then
    DOTS_PROGRESS_OVERALL=0 DOTS_PROGRESS_GROUP=1 DOTS_PROGRESS_GROUPS=$total DOTS_PROGRESS_UNIT=$unit
    DOTS_PROGRESS_BASE=0 DOTS_PROGRESS_SPAN=1000000 DOTS_PROGRESS_CANCELLED=0
  fi
  _DOTS_PROGRESS_BASES[depth]=${DOTS_PROGRESS_BASE:-0}
  _DOTS_PROGRESS_SPANS[depth]=${DOTS_PROGRESS_SPAN:-1000000}
  _DOTS_PROGRESS_TOTALS[depth]=$total _DOTS_PROGRESS_INDEXES[depth]=0
  _DOTS_PROGRESS_PREV_STEP[depth]=${DOTS_PROGRESS_STEP:-1}
  _DOTS_PROGRESS_PREV_STEPS[depth]=${DOTS_PROGRESS_STEPS:-1}
  DOTS_PROGRESS_DEPTH=$((depth+1))
  DOTS_PROGRESS_STEP=1 DOTS_PROGRESS_STEPS=$total
  dots::progress_start "$label"
}

dots::progress_step_start() {
  local label=$1 depth=$((${DOTS_PROGRESS_DEPTH:-0}-1)) index=${2:-}
  ((depth>=0)) || { dots::progress_start "$label"; return 0; }
  local total=${_DOTS_PROGRESS_TOTALS[depth]} base=${_DOTS_PROGRESS_BASES[depth]} span=${_DOTS_PROGRESS_SPANS[depth]}
  [[ $index =~ ^[0-9]{1,9}$ ]] || index=$((_DOTS_PROGRESS_INDEXES[depth]+1))
  index=$((10#$index)); ((index>=1)) || index=1
  ((total>0 && index<=total)) || { dots::progress_update "$label"; return 0; }
  _DOTS_PROGRESS_INDEXES[depth]=$index
  DOTS_PROGRESS_BASE=$((base+span*(index-1)/total))
  DOTS_PROGRESS_SPAN=$((base+span*index/total-DOTS_PROGRESS_BASE))
  ((${DOTS_PROGRESS_FROZEN:-0} || ${DOTS_PROGRESS_CANCELLED:-0} || DOTS_PROGRESS_OVERALL>=DOTS_PROGRESS_BASE)) || DOTS_PROGRESS_OVERALL=$DOTS_PROGRESS_BASE
  ((depth!=0)) || DOTS_PROGRESS_GROUP=$index
  DOTS_PROGRESS_STEP=$index DOTS_PROGRESS_STEPS=$total
  dots::progress_start "$label"
}

dots::progress_measure() {
  local completed=${2:-0} total=${3:-0} value
  if [[ $completed =~ ^[0-9]{1,9}$ && $total =~ ^[0-9]{1,9}$ ]] && ((10#$total>0)); then
    completed=$((10#$completed)); total=$((10#$total)); ((completed<=total)) || completed=$total
    value=$((${DOTS_PROGRESS_BASE:-0}+${DOTS_PROGRESS_SPAN:-1000000}*completed/total))
    ((${DOTS_PROGRESS_FROZEN:-0} || ${DOTS_PROGRESS_CANCELLED:-0} || ${DOTS_PROGRESS_OVERALL:-0}>=value)) || DOTS_PROGRESS_OVERALL=$value
  fi
  dots::progress_update "$1" "${2:-0}" "${3:-0}"
}

dots::progress_step_end() {
  local depth=$((${DOTS_PROGRESS_DEPTH:-0}-1)) value
  ((depth>=0)) || return 0
  if ((${1:-0}==0 && ! ${DOTS_PROGRESS_CANCELLED:-0} && ! ${DOTS_PROGRESS_FROZEN:-0})); then
    value=$((${DOTS_PROGRESS_BASE:-0}+${DOTS_PROGRESS_SPAN:-1000000}))
    ((DOTS_PROGRESS_OVERALL>=value)) || DOTS_PROGRESS_OVERALL=$value
  fi
  DOTS_PROGRESS_BASE=${_DOTS_PROGRESS_BASES[depth]} DOTS_PROGRESS_SPAN=${_DOTS_PROGRESS_SPANS[depth]}
  dots::progress_start "${DOTS_PROGRESS_LABEL:-Working}"
}

dots::progress_sequence_end() {
  local depth=$((${DOTS_PROGRESS_DEPTH:-0}-1)) value
  ((depth>=0)) || return 0
  if ((${1:-0}==0 && ! ${DOTS_PROGRESS_CANCELLED:-0} && ! ${DOTS_PROGRESS_FROZEN:-0})); then
    value=$((_DOTS_PROGRESS_BASES[depth]+_DOTS_PROGRESS_SPANS[depth]))
    ((DOTS_PROGRESS_OVERALL>=value)) || DOTS_PROGRESS_OVERALL=$value
  fi
  DOTS_PROGRESS_BASE=${_DOTS_PROGRESS_BASES[depth]} DOTS_PROGRESS_SPAN=${_DOTS_PROGRESS_SPANS[depth]}
  DOTS_PROGRESS_STEP=${_DOTS_PROGRESS_PREV_STEP[depth]} DOTS_PROGRESS_STEPS=${_DOTS_PROGRESS_PREV_STEPS[depth]}
  unset '_DOTS_PROGRESS_BASES[depth]' '_DOTS_PROGRESS_SPANS[depth]' '_DOTS_PROGRESS_TOTALS[depth]' '_DOTS_PROGRESS_INDEXES[depth]' '_DOTS_PROGRESS_PREV_STEP[depth]' '_DOTS_PROGRESS_PREV_STEPS[depth]'
  DOTS_PROGRESS_DEPTH=$depth
  dots::progress_update "${DOTS_PROGRESS_LABEL:-Working}"
  ((depth!=0)) || dots::progress_stop
  return 0
}

dots::progress_cancel() {
  DOTS_PROGRESS_CANCELLED=1
  dots::progress_stop
}

# Wrap early-returning workflows without installing traps in their caller.
dots::progress_sequence_run() {
  local label=$1 total=$2 unit=$3 depth=${DOTS_PROGRESS_DEPTH:-0} rc=0
  shift 3
  dots::progress_sequence_start "$label" "$total" "$unit"
  "$@" || rc=$?
  while ((${DOTS_PROGRESS_DEPTH:-0}>depth)); do dots::progress_sequence_end "$rc"; done
  return "$rc"
}

dots::progress_recovery_run() {
  local DOTS_PROGRESS_FROZEN=0
  ((${DOTS_PROGRESS_DEPTH:-0}==0)) || DOTS_PROGRESS_FROZEN=1
  dots::progress_sequence_run "$@"
}

dots::progress_stop() {
  [[ -n ${DOTS_PROGRESS_FD:-} ]] || return 0
  (printf 'stop\n' >&"$DOTS_PROGRESS_FD") 2>/dev/null || :
  exec {DOTS_PROGRESS_FD}>&-
  wait "${DOTS_PROGRESS_PID:-}" 2>/dev/null || :
  DOTS_PROGRESS_FD='' DOTS_PROGRESS_PID=''
  return 0
}

# Permanent rows share the terminal with the worker, never race its output.
dots::progress_print() {
  local active=${DOTS_PROGRESS_FD:-} label=${DOTS_PROGRESS_LABEL:-} completed=${DOTS_PROGRESS_COMPLETED:-0} total=${DOTS_PROGRESS_TOTAL:-0}
  local status=0
  dots::progress_stop
  "$@" >&2 || status=$?
  [[ ! $active ]] || dots::progress_start "$label" "$completed" "$total"
  return "$status"
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
