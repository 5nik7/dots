#!/usr/bin/env bash
# dots-owned CLI for the adapted git-it engine; see LICENSE.
# shellcheck source-path=SCRIPTDIR
# shellcheck disable=SC2034
set -u
set -o pipefail
export GIT_OPTIONAL_LOCKS=0
LIB=$(cd -- "${BASH_SOURCE[0]%/*}" && pwd) || exit 3
DOTS_LIB_DIR=${DOTS_LIB_DIR:-${LIB%/git}}
source "$LIB/common.bash"
source "$LIB/ui.bash"
((BASH_VERSINFO[0] >= 5)) || die 3 'requires Bash 5 or newer'
CMD=$1; shift
TARGET=${DOTS:-${LIB%/lib/dots/git}} CONFIG=${XDG_CONFIG_HOME:-$HOME/.config}/dots/git.conf
NO_CONFIG=0 EXPLICIT_CONFIG=0 REMOTE_ARG='' OUTERMOST=0 DRY_RUN=0 ADVANCE=0 ALL=0 YES=0 INIT=0 MESSAGE='' JSON=0 FULL_PATHS=0
OWNERS=() HOST_ALIASES=() STATUS_DIRS=() PUB_DIRS=()
while (($#)); do
    arg=$1; shift
    case $arg in
        -C|--directory|--config|-m|--message)
            (($#)) || die 2 "$arg requires a value"
            case $arg in -C|--directory) TARGET=$1 ;; --config) CONFIG=$1; EXPLICIT_CONFIG=1 ;; *) MESSAGE=$1 ;; esac
            shift ;;
        --no-config) NO_CONFIG=1 ;;
        --json) JSON=1 ;;
        --full-paths) FULL_PATHS=1 ;;
        --dry-run) DRY_RUN=1 ;;
        --all) ALL=1 ;;
        --yes) YES=1 ;;
        --remote) ADVANCE=1 ;;
        --init) INIT=1 ;;
        *) die 2 "unknown argument: $arg" ;;
    esac
done
if [[ $CMD != publish ]] && ((ALL || YES || EXPLICIT_CONFIG || NO_CONFIG)) || [[ $CMD != publish && -n $MESSAGE ]]; then die 2 'publish options require publish'; fi
if [[ $CMD != sync ]] && ((ADVANCE || INIT)); then die 2 'sync options require sync'; fi
[[ $CMD != status || $DRY_RUN == 0 ]] || die 2 'status is already read-only'
command -v git >/dev/null 2>&1 || die 3 'Git is required'
case $(uname -s) in MINGW*|MSYS*|CYGWIN*) die 3 'native Windows Git management is not implemented' ;; esac
[[ -z ${GIT_DIR+x}${GIT_WORK_TREE+x}${GIT_INDEX_FILE+x}${GIT_COMMON_DIR+x} ]] || die 3 'unset Git repository/index redirection variables'
if [[ $CMD == publish && $NO_CONFIG == 0 ]]; then
    if [[ -e $CONFIG ]]; then
        [[ -f $CONFIG && ! -L $CONFIG && -r $CONFIG ]] || die 2 'configuration must be a readable regular file'
        records_cmd git config --no-includes --null --file "$CONFIG" --list 2>/dev/null || die 2 'invalid config'
        for row in "${RECORDS[@]}"; do
            key=${row%%$'\n'*}; value=${row#*$'\n'}
            case $key in
                dots-git.owner) [[ $value == */* && $value != *$'\n'* ]] || die 2 'owner must be host/namespace'; OWNERS+=("$value") ;;
                dots-git.hostalias) [[ $value == *=* ]] || die 2 'hostAlias must be alias=hostname'; HOST_ALIASES+=("$value") ;;
                *) die 2 "unknown configuration key: $key" ;;
            esac
        done
    elif ((EXPLICIT_CONFIG)); then die 2 'configuration does not exist'; fi
fi
source "$LIB/inspect.bash"
text_cmd canonical_dir "$TARGET" 2>/dev/null || die 3 'target must be an existing directory'
repo_root "$REPLY" || die 3 'not inside a Git worktree'
ROOT=$REPLY
colors
if [[ $CMD == status ]]; then
    source "$LIB/status.bash"
    status_main
else
    source "$LIB/operations.bash"
    ((!JSON)) && dots::heading "Git $CMD"
    operations_main
fi
