# On-demand ZLE capture for the source tmux pane. Never source personal config.
_dots_keys_ipc_close() {
  emulate -L zsh
  (( ZSH_SUBSHELL == 0 )) || return 0
  local fd=${_DOTS_KEYS_IPC_FD:-}
  if [[ -n $fd ]]; then
    zle -F "$fd" 2>/dev/null
    exec {fd}>&-
    unset _DOTS_KEYS_IPC_FD
  fi
  if [[ -n ${_DOTS_KEYS_IPC_DIR:-} && -d $_DOTS_KEYS_IPC_ROOT && ! -L $_DOTS_KEYS_IPC_ROOT && -O $_DOTS_KEYS_IPC_ROOT && -d $_DOTS_KEYS_IPC_DIR && ! -L $_DOTS_KEYS_IPC_DIR && -O $_DOTS_KEYS_IPC_DIR ]]; then
    [[ ! -S $_DOTS_KEYS_IPC_DIR/s ]] || zf_rm -f -- "$_DOTS_KEYS_IPC_DIR/s"
    zf_rmdir -- "$_DOTS_KEYS_IPC_DIR" 2>/dev/null
  fi
  return 0
}

_dots_keys_ipc_request() {
  emulate -L zsh
  local REPLY connection listener=$1 worker=${_DOTS_KEYS_IPC_WORKER:-}
  zsocket -a -t "$listener" 2>/dev/null || return 0
  connection=$REPLY
  # A completed worker's PID can eventually be reused. Its hard two-second
  # lifetime means an older PID must never keep a long-running shell busy.
  local age=$(( SECONDS - ${_DOTS_KEYS_IPC_WORKER_SINCE:-0} ))
  if [[ -n $worker ]] && (( age >= 0 && age < 3 )) && kill -0 "$worker" 2>/dev/null; then
    exec {connection}>&-
    return 0
  fi
  # Inherited maps are inspected in a child. No request text is evaluated and
  # no socket write, Python process or map enumeration blocks the ZLE handler.
  { (
    exec {listener}>&-
    _dots_keys_snapshot | "$_DOTS_KEYS_IPC_PYTHON" -B "$DOTS/lib/dots/keys/zsh_bridge.py" \
      serve "$connection" "$_DOTS_KEYS_IPC_CONTEXT" "$_DOTS_KEYS_IPC_PANE"
    exec {connection}>&-
  ) >/dev/null 2>&1 &! } 2>/dev/null
  _DOTS_KEYS_IPC_WORKER=$!
  _DOTS_KEYS_IPC_WORKER_SINCE=$SECONDS
  exec {connection}>&-
  return 0
}

_dots_keys_ipc_open() {
  local previous_status=$?
  emulate -L zsh
  [[ -z ${_DOTS_KEYS_IPC_FD:-} ]] || return "$previous_status"
  local REPLY old_umask=$(umask)
  local -A info
  {
    umask 077
    if [[ ! -e $_DOTS_KEYS_IPC_ROOT && ! -L $_DOTS_KEYS_IPC_ROOT ]]; then
      zf_mkdir -m 700 -- "$_DOTS_KEYS_IPC_ROOT" 2>/dev/null || return "$previous_status"
    fi
    [[ -d $_DOTS_KEYS_IPC_ROOT && ! -L $_DOTS_KEYS_IPC_ROOT ]] || return "$previous_status"
    zstat -H info "$_DOTS_KEYS_IPC_ROOT" 2>/dev/null || return "$previous_status"
    (( info[uid] == EUID && (info[mode] & 8#777) == 8#700 )) || return "$previous_status"
    # Exclusive creation refuses a replaced or abandoned session directory.
    zf_mkdir -m 700 -- "$_DOTS_KEYS_IPC_DIR" 2>/dev/null || return "$previous_status"
    if zsocket -l "$_DOTS_KEYS_IPC_DIR/s" 2>/dev/null; then
      _DOTS_KEYS_IPC_FD=$REPLY
      zle -F "$REPLY" _dots_keys_ipc_request
    else
      zf_rmdir -- "$_DOTS_KEYS_IPC_DIR" 2>/dev/null
    fi
  } always {
    umask "$old_umask"
  }
  return "$previous_status"
}

_dots_keys_ipc_setup() {
  emulate -L zsh
  [[ -o interactive && -n ${TMUX:-} && ${TMUX_PANE:-} == %<-> ]] || return 0
  local identity=${TMUX%,*} server=${${TMUX%,*}##*,} base=${XDG_RUNTIME_DIR:-${TMPDIR:-/tmp}}
  [[ $identity == /* && $server == <-> && $base == /* ]] || return 0
  (( $+commands[python3] )) || return 0
  if [[ ${_DOTS_KEYS_IPC_CONTEXT:-} == "$identity" && ${_DOTS_KEYS_IPC_PANE:-} == "$TMUX_PANE" ]]; then
    return 0
  fi
  zmodload zsh/net/socket 2>/dev/null || return 0
  zmodload -F zsh/files b:zf_mkdir b:zf_rm b:zf_rmdir 2>/dev/null || return 0
  zmodload -F zsh/stat b:zstat 2>/dev/null || return 0
  _dots_keys_ipc_close
  typeset -g _DOTS_KEYS_IPC_ROOT=${base%/}/dots-k-$EUID
  typeset -g _DOTS_KEYS_IPC_DIR=$_DOTS_KEYS_IPC_ROOT/$server-${TMUX_PANE#%}-$$-$RANDOM$RANDOM
  # Leave room for the Unix socket pathname on hosts with a 104-byte limit.
  local LC_ALL=C
  (( ${#_DOTS_KEYS_IPC_DIR} < 100 )) || { unset _DOTS_KEYS_IPC_DIR; return 0; }
  typeset -g _DOTS_KEYS_IPC_CONTEXT=$identity _DOTS_KEYS_IPC_PANE=$TMUX_PANE
  typeset -g _DOTS_KEYS_IPC_PYTHON=$commands[python3]
  autoload -Uz add-zsh-hook
  add-zsh-hook precmd _dots_keys_ipc_open
  add-zsh-hook preexec _dots_keys_ipc_close
  add-zsh-hook zshexit _dots_keys_ipc_close
  return 0
}
_dots_keys_ipc_setup
