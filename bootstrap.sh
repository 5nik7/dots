#!/bin/sh
# Standalone first stage: reviewed prerequisites, checkout acquisition, shared setup.
set -eu
bootstrap_source=https://github.com/5nik7/dots.git
bootstrap_ref=main
bootstrap_destination=
bootstrap_yes=0
bootstrap_dry=0
bootstrap_offline=0
bootstrap_noninteractive=0
bootstrap_json=0
bootstrap_here=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd -P)

bootstrap_error() { printf 'dots bootstrap: %s\n' "$*" >&2; exit 1; }
bootstrap_confirm() {
    [ "$bootstrap_yes" = 1 ] && return 0
    [ "$bootstrap_noninteractive" = 0 ] && [ -t 0 ] || bootstrap_error 'preparation requires --yes when noninteractive; use --dry-run first'
    printf '%s [y/N] ' "$1" >&2
    IFS= read -r bootstrap_answer || return 1
    case $bootstrap_answer in y|Y|yes|YES) return 0 ;; *) return 1 ;; esac
}
bootstrap_python() { command -v python3 >/dev/null 2>&1 && python3 -B -c 'import sys;sys.exit(sys.version_info < (3,11))' >/dev/null 2>&1; }
bootstrap_valid() { [ -f "$1/install.sh" ] && [ -f "$1/bin/dots" ] && [ -f "$1/lib/dots/files/install.py" ]; }

# Rotate unknown arguments without eval or lossy string accumulation.
set -- "$@" --dots-bootstrap-end
while [ "$1" != --dots-bootstrap-end ]; do
    case $1 in
        --destination|--source|--ref)
            bootstrap_option=$1; shift
            [ "$#" -gt 1 ] && [ "$1" != --dots-bootstrap-end ] || bootstrap_error "missing value for $bootstrap_option"
            case $bootstrap_option in --destination) bootstrap_destination=$1 ;; --source) bootstrap_source=$1 ;; --ref) bootstrap_ref=$1 ;; esac
            shift ;;
        --yes|-y) bootstrap_yes=1; shift ;;
        --dry-run) bootstrap_dry=1; shift ;;
        --offline) bootstrap_offline=1; shift ;;
        --non-interactive) bootstrap_noninteractive=1; shift ;;
        --json) bootstrap_json=1; shift ;;
        --help|-h)
            printf '%s\n' 'Usage: bootstrap.sh [--destination PATH] [--source HTTPS_OR_LOCAL_REPO] [--ref REF]' \
                '                    [--dry-run] [--yes] [--offline] [INSTALLER OPTIONS...]' \
                'Defaults: current checkout when available, otherwise ~/dots; public Dots main.' \
                'Prerequisites and acquisition are reviewed before the shared installer starts.'
            exit 0 ;;
        *) set -- "$@" "$1"; shift ;;
    esac
done
shift
if [ -z "$bootstrap_destination" ]; then
    if bootstrap_valid "$bootstrap_here"; then bootstrap_destination=$bootstrap_here
    else bootstrap_destination=$HOME/dots; fi
fi
case $bootstrap_destination in '~/'*) bootstrap_destination=$HOME/${bootstrap_destination#\~/} ;; /*) ;; *) bootstrap_destination=$PWD/$bootstrap_destination ;; esac
case $bootstrap_source in
    https://*)
        bootstrap_authority=${bootstrap_source#https://}; bootstrap_authority=${bootstrap_authority%%/*}
        case $bootstrap_authority in ''|*@*) bootstrap_error 'source must not contain credentials' ;; esac
        case $bootstrap_source in *\?*|*\#*) bootstrap_error 'source must not contain URL parameters' ;; esac ;;
    /*) ;;
    *) bootstrap_error 'source must be an HTTPS URL or absolute local repository path' ;;
esac
case $bootstrap_ref in ''|-*|*[[:space:][:cntrl:]]*) bootstrap_error 'invalid bootstrap ref' ;; esac
case $bootstrap_source$bootstrap_destination in *[[:cntrl:]]*) bootstrap_error 'bootstrap paths must not contain control characters' ;; esac
bootstrap_existing=0
if [ -e "$bootstrap_destination" ] || [ -L "$bootstrap_destination" ]; then
    bootstrap_valid "$bootstrap_destination" || bootstrap_error 'destination is occupied by something other than a Dots checkout'
    bootstrap_existing=1
fi
bootstrap_missing=
bootstrap_python || bootstrap_missing="$bootstrap_missing python3"
if [ "$bootstrap_existing" = 0 ] && ! command -v git >/dev/null 2>&1; then bootstrap_missing="$bootstrap_missing git"; fi
if ! command -v bash >/dev/null 2>&1 || ! bash -c '((BASH_VERSINFO[0] > 4 || BASH_VERSINFO[0] == 4 && BASH_VERSINFO[1] >= 4))' >/dev/null 2>&1; then
    bootstrap_missing="$bootstrap_missing bash"
fi
bootstrap_manager=
case ${PREFIX:-} in */com.termux/*) command -v pkg >/dev/null 2>&1 && bootstrap_manager=pkg ;; esac
if [ -z "$bootstrap_manager" ]; then
    for bootstrap_candidate in apt-get dnf pacman xbps-install; do
        if command -v "$bootstrap_candidate" >/dev/null 2>&1; then bootstrap_manager=$bootstrap_candidate; break; fi
    done
fi
if [ "$bootstrap_dry" = 1 ]; then
    if [ "$bootstrap_existing" = 1 ] && bootstrap_python && [ -z "$bootstrap_missing" ]; then
        set -- --dry-run --with-dependencies "$@"
        [ "$bootstrap_offline" = 0 ] || set -- --offline "$@"
        [ "$bootstrap_json" = 0 ] || set -- --json "$@"
        exec sh "$bootstrap_destination/install.sh" "$@"
    fi
    if [ "$bootstrap_json" = 1 ]; then
        bootstrap_python || bootstrap_error 'JSON bootstrap preview needs Python 3.11+; plain --dry-run is available without it'
        python3 -B -c 'import json,sys;print(json.dumps(dict(schema=1,status="planned",destination=sys.argv[1],source=sys.argv[2],ref=sys.argv[3],missing=sys.argv[4].split(),manager=sys.argv[5] or None)))' \
            "$bootstrap_destination" "$bootstrap_source" "$bootstrap_ref" "$bootstrap_missing" "$bootstrap_manager"
    else
        printf 'Dots bootstrap\n  Checkout: %s\n  Source: %s\n  Ref: %s\n  Missing:%s\n  Manager: %s\n  No changes made.\n' \
            "$bootstrap_destination" "$bootstrap_source" "$bootstrap_ref" "$bootstrap_missing" "${bootstrap_manager:-manual prerequisites}"
    fi
    exit 0
fi
if [ -n "$bootstrap_missing" ]; then
    [ "$bootstrap_offline" = 0 ] || bootstrap_error "offline setup needs preinstalled prerequisites:$bootstrap_missing"
    [ -n "$bootstrap_manager" ] || bootstrap_error "install Git, Python 3.11+ and Bash 4.4+ explicitly, then retry; missing:$bootstrap_missing"
    bootstrap_privilege=
    if [ "$bootstrap_manager" != pkg ] && [ "$(id -u)" != 0 ]; then
        command -v sudo >/dev/null 2>&1 || bootstrap_error 'package preparation needs an administrator; install the listed prerequisites and retry'
        bootstrap_privilege=sudo
    fi
    printf 'Prepare prerequisites using %s%s:%s\n' "${bootstrap_privilege:+sudo }" "$bootstrap_manager" "$bootstrap_missing" >&2
    bootstrap_confirm 'Install these prerequisites? Package changes remain if later setup fails.' || exit 130
    bootstrap_packages=
    for bootstrap_tool in $bootstrap_missing; do
        bootstrap_package=$bootstrap_tool
        case $bootstrap_manager:$bootstrap_tool in pkg:python3|pacman:python3) bootstrap_package=python ;; esac
        bootstrap_packages="$bootstrap_packages $bootstrap_package"
    done
    # These lists contain only the fixed prerequisite names above.
    case $bootstrap_manager in
        pkg) pkg install -y $bootstrap_packages >&2 ;;
        apt-get) $bootstrap_privilege apt-get update >&2; $bootstrap_privilege apt-get install --no-install-recommends -y $bootstrap_packages >&2 ;;
        dnf) $bootstrap_privilege dnf install -y $bootstrap_packages >&2 ;;
        pacman) $bootstrap_privilege pacman -S --needed --noconfirm $bootstrap_packages >&2 ;;
        xbps-install) $bootstrap_privilege xbps-install -S -y $bootstrap_packages >&2 ;;
    esac
    bootstrap_python || bootstrap_error 'the package manager did not provide Python 3.11+; install a compatible runtime and resume'
    command -v bash >/dev/null 2>&1 || bootstrap_error 'Bash is still missing; prerequisite changes have been retained'
fi
if [ "$bootstrap_existing" = 0 ]; then
    [ "$bootstrap_offline" = 0 ] || bootstrap_error 'offline bootstrap requires an existing checkout'
    printf 'Acquire %s at %s into %s\n' "$bootstrap_source" "$bootstrap_ref" "$bootstrap_destination" >&2
    bootstrap_confirm 'Fetch this checkout and continue into setup?' || exit 130
    command -v git >/dev/null 2>&1 || bootstrap_error 'Git is required for checkout acquisition'
    # Python is now present. Reuse the existing acquisition algorithm shape:
    # owned staging, explicit ref, no-replace publication and a retained journal.
    python3 -B - "$bootstrap_destination" "$bootstrap_source" "$bootstrap_ref" <<'PY'
import ctypes,json,os,pathlib,subprocess,sys,tempfile
destination=pathlib.Path(sys.argv[1]).absolute(); source,ref=sys.argv[2:]
if any(ord(c)<32 for c in ref) or ref.startswith('-'): raise SystemExit('dots bootstrap: invalid ref')
destination.parent.mkdir(parents=True,exist_ok=True)
if destination.exists() or destination.is_symlink(): raise SystemExit('dots bootstrap: destination became occupied')
stage=pathlib.Path(tempfile.mkdtemp(prefix='.'+destination.name+'.bootstrap-',dir=destination.parent))
journal=stage/'journal.json'
def record(status,**extra):
    with journal.open('w') as stream:
        json.dump(dict(schema=1,status=status,destination=str(destination),source=source,ref=ref,**extra),stream)
        stream.flush();os.fsync(stream.fileno())
env={k:v for k,v in os.environ.items() if k not in ('GIT_DIR','GIT_WORK_TREE','GIT_COMMON_DIR','GIT_INDEX_FILE','GIT_OBJECT_DIRECTORY','GIT_ALTERNATE_OBJECT_DIRECTORIES')}
env.update(GIT_TERMINAL_PROMPT='0',GCM_INTERACTIVE='Never',GIT_CONFIG_NOSYSTEM='1')
def git(*args):
    result=subprocess.run(['git','-c','submodule.recurse=false','-c','protocol.ext.allow=never',*args],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=180)
    if result.returncode: raise ValueError('Git acquisition failed; retained preparation journal: '+str(journal))
    return result.stdout.decode().strip()
record('preparing')
try:
    checkout=stage/'checkout'
    git('init','--',str(checkout));git('-C',str(checkout),'remote','add','origin',source)
    git('-C',str(checkout),'fetch','--depth=1','--no-recurse-submodules','origin',ref)
    git('-C',str(checkout),'checkout','--detach','FETCH_HEAD')
    commit=git('-C',str(checkout),'rev-parse','HEAD')
    for name in ('install.sh','bin/dots','bin/dots.ps1','lib/dots/files/install.py'):
        path=checkout/name
        if path.is_symlink() or not path.is_file(): raise ValueError('acquired source lacks the Dots setup layout')
    record('prepared',commit=commit)
    libc=ctypes.CDLL(None,use_errno=True); rename=getattr(libc,'renameat2',None)
    if rename is None: raise ValueError('atomic no-replace checkout publication is unavailable')
    rename.argtypes=[ctypes.c_int,ctypes.c_char_p,ctypes.c_int,ctypes.c_char_p,ctypes.c_uint]
    if rename(-100,os.fsencode(checkout),-100,os.fsencode(destination),1): raise OSError(ctypes.get_errno(),'checkout publication failed')
    record('committed',commit=commit)
except BaseException as error:
    record('failed');print('dots bootstrap: '+str(error),file=sys.stderr);sys.exit(1)
PY
fi
export DOTS_BOOTSTRAP_READY=1
set -- --with-dependencies "$@"
[ "$bootstrap_yes" = 0 ] || set -- --yes "$@"
[ "$bootstrap_noninteractive" = 0 ] || set -- --non-interactive "$@"
[ "$bootstrap_json" = 0 ] || set -- --json "$@"
[ "$bootstrap_offline" = 0 ] || set -- --offline "$@"
exec sh "$bootstrap_destination/install.sh" "$@"
