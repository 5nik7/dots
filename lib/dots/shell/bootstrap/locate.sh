# Called only on the cold path. Stdout is the selected checkout.
set -eu
fail() { printf 'dots bootstrap: %s\n' "$1" >&2; exit 1; }
case ${2:-} in
    bash|zsh|fish) native="shells/$2/init.$2" ;;
    nu) native=shells/nushell/init.nu ;;
    xonsh) native=shells/xonsh/init.xsh ;;
    '') native=lib/dots/shell/startup.bash ;;
    *) fail 'Unsupported shell.' ;;
esac
valid() { [ -f "$1/bin/dots" ] && [ -x "$1/bin/dots" ] && [ -f "$1/lib/dots/shell/startup.bash" ] && [ -r "$1/$native" ]; }
target=${DOTS_BOOTSTRAP_DIR:-"$HOME/dots"}
case $target in /*) ;; *) fail 'DOTS_BOOTSTRAP_DIR must be absolute.';; esac
if [ -z "${DOTS_BOOTSTRAP_DIR:-}" ]; then
    if exe=$(command -v dots) && [ -x "$exe" ]; then
        # Resolve ordinary checkout launchers before asking a wrapper.
        physical=$(realpath -- "$exe" 2>/dev/null) || physical=
        root=${physical%/bin/dots}
        if ! valid "$root"; then root=$(DOTS='' "$exe" env DOTS 2>/dev/null) || root=; fi
        if [ -n "$root" ] && valid "$root"; then printf '%s\n' "$root"; exit 0; fi
    fi
    if [ -r "$HOME/.local/share/dots/bootstrap/checkout" ]; then
        IFS= read -r root < "$HOME/.local/share/dots/bootstrap/checkout" || :
        case $root in /*) if valid "$root"; then printf '%s\n' "$root"; exit 0; fi ;; esac
    fi
fi
if valid "$target"; then printf '%s\n' "$target"; exit 0; fi
[ "${1:-}" = interactive ] || exit 1
command -v git >/dev/null 2>&1 || fail 'Install Git or set DOTS_BOOTSTRAP_DIR to an existing checkout.'
[ ! -e "$target" ] && [ ! -L "$target" ] || fail 'Checkout destination is occupied. Set DOTS_BOOTSTRAP_DIR to select another path.'
source=${DOTS_BOOTSTRAP_SOURCE:-https://github.com/5nik7/dots.git}
ref=${DOTS_BOOTSTRAP_REF:-main}
case $source in
    https://*) authority=${source#https://}; authority=${authority%%/*}
        case $authority in ''|*@*) fail 'Invalid HTTPS source.';; esac
        case $source in *'?'*|*'#'*) fail 'URL parameters are unsupported.';; esac ;;
    file:///*)
        case $source in *'?'*|*'#'*) fail 'URL parameters are unsupported.';; esac ;;
    /*) ;;
    -*) fail 'Invalid local source.' ;;
    *)
        [ -d "$source" ] || fail 'Use an HTTPS or existing local source.'
        source=$(CDPATH='' cd -- "$source" && pwd -P) || fail 'Cannot resolve local source.' ;;
esac
case $ref in ''|-*|*[[:space:][:cntrl:]]*) fail 'Invalid bootstrap ref.';; esac
case $source$target in *[[:cntrl:]]*) fail 'Control characters in bootstrap paths.';; esac
# GNU/Coreutils -Tn is the no-replace directory publication primitive on
# Termux/Linux/WSL. Refuse before acquisition on a host without it.
mv --help 2>/dev/null | grep -q -- '--no-target-directory' || fail 'No safe directory publication tool. Clone Dots manually.'
umask 077
parent=${target%/*}
parent=${parent:-/}
mkdir -p -- "$parent"
# flock releases automatically on interruption. Limit the wait for a first
# shell already acquiring this checkout, then reuse its completed result.
if command -v flock >/dev/null 2>&1; then
    lock="$parent/.${target##*/}.bootstrap.lock"
    if [ -L "$lock" ] || { [ -e "$lock" ] && [ ! -f "$lock" ]; }; then fail 'Invalid acquisition lock.'; fi
    exec 9>> "$lock"
    flock -w 95 9 || fail 'Acquisition is busy; try again after the other shell finishes.'
    if valid "$target"; then printf '%s\n' "$target"; exit 0; fi
    [ ! -e "$target" ] && [ ! -L "$target" ] || fail 'Checkout destination became occupied.'
fi
stage=$(mktemp -d -- "${target%/*}/.${target##*/}.bootstrap-XXXXXXXX") || fail 'Cannot stage checkout.'
# Path and ref validation has already excluded control characters.
json_string() { printf '%s' "$1" | sed 's/\\/\\\\/g;s/"/\\"/g'; }
journal_target=$(json_string "$target")
journal_ref=$(json_string "$ref")
record() {
    printf '{"version":1,"status":"%s","destination":"%s","ref":"%s"}\n' "$1" "$journal_target" "$journal_ref" > "$stage/journal.next"
    sync -d "$stage/journal.next" && mv -f -- "$stage/journal.next" "$stage/journal.json" && sync -d "$stage"
}
record preparing
trap 'record failed' EXIT
child=''
on_interrupt() {
    if [ -n "$child" ]; then kill "$child" 2>/dev/null || :; wait "$child" 2>/dev/null || :; fi
    exit 1
}
trap on_interrupt HUP INT TERM
unset GIT_DIR GIT_WORK_TREE GIT_COMMON_DIR GIT_INDEX_FILE GIT_OBJECT_DIRECTORY GIT_ALTERNATE_OBJECT_DIRECTORIES
unset GIT_CONFIG GIT_CONFIG_PARAMETERS GIT_CONFIG_COUNT GIT_ASKPASS SSH_ASKPASS GIT_TEMPLATE_DIR
unset GIT_EXEC_PATH GIT_SSL_NO_VERIFY GIT_TRACE GIT_TRACE_CURL GIT_CURL_VERBOSE
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null
case $source in https://*) GIT_ALLOW_PROTOCOL=https ;; *) GIT_ALLOW_PROTOCOL=file ;; esac
export GIT_ALLOW_PROTOCOL
export GIT_TERMINAL_PROMPT=0 GCM_INTERACTIVE=Never
command -v timeout >/dev/null 2>&1 || fail 'The timeout utility is required for bounded checkout acquisition.'
(
    cd -- "$stage" || exit
    export HOME="$stage" XDG_CONFIG_HOME="$stage" GIT_LFS_SKIP_SMUDGE=1
    exec timeout -k 2 90 git -c credential.helper= -c core.askPass= -c protocol.ext.allow=never -c http.lowSpeedLimit=1 -c http.lowSpeedTime=30 \
    clone --quiet --no-recurse-submodules --single-branch --branch "$ref" -- "$source" "$stage/checkout"
) </dev/null >/dev/null 2>&1 &
child=$!
wait "$child" || fail 'Git clone failed. Check the source/ref and retry.'
child=''
valid "$stage/checkout" && [ -f "$stage/checkout/bin/dots.ps1" ] || fail 'Source lacks Dots startup files.'
record prepared
mv -Tn -- "$stage/checkout" "$target" || fail 'Could not publish checkout.'
if [ -d "$stage/checkout" ]; then
    valid "$target" || fail 'Checkout destination became occupied.'
    record superseded
else
    sync -d "$parent"
    record committed
fi
trap - EXIT
printf '%s\n' "$target"
