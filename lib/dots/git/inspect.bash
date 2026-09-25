# Adapted from git-it 0.1.0; see LICENSE.
# Local Git discovery, URL parsing and prompt rendering.
# shellcheck disable=SC2034,SC2153
repo_root() {
    text_cmd git -C "$1" rev-parse --show-toplevel 2>/dev/null || return 1
    text_cmd canonical_dir "$REPLY"
}

list_fields() {
    printf '%s\n' root remote url protocol host owner repo owned icon current parent outermost \
        parent_dirname parent_basename submodule_prefix submodule_basename cwd_prefix \
        path_parent path_outermost chain_length chain_repos chain_paths is_submodule
}

select_remote() {
    local dir=$1 branch
    REMOTE=$REMOTE_ARG
    if [[ -z $REMOTE ]]; then
        if text_cmd git -C "$dir" symbolic-ref --quiet --short HEAD 2>/dev/null; then
            branch=$REPLY
            text_cmd git -C "$dir" config --get "branch.$branch.remote" 2>/dev/null && REMOTE=$REPLY
        fi
        [[ -n $REMOTE && $REMOTE != . ]] || REMOTE=origin
    fi
    URL=''
    if text_cmd git -C "$dir" remote get-url -- "$REMOTE" 2>/dev/null; then URL=$REPLY
    elif [[ -n $REMOTE_ARG ]]; then return 1
    else REMOTE=''; fi
}

parse_url() {
    local url=$1 rest authority path alias entry identity
    PROTOCOL=local HOST='' OWNER='' REPO='' OWNED=false HOST_ICON='' SAFE_URL=$url
    if [[ $url =~ ^([a-zA-Z][a-zA-Z0-9+.-]*)://(.*)$ ]]; then
        PROTOCOL=${BASH_REMATCH[1],,}; rest=${BASH_REMATCH[2]}
        authority=${rest%%/*}; path=${rest#*/}; [[ $rest == */* ]] || path=''
        authority=${authority##*@}
        SAFE_URL="$PROTOCOL://$authority/$path"
        HOST=${authority%%:*}
        if [[ $authority == \[*\]* ]]; then HOST=${authority%%]*}; HOST+=']'; fi
    elif [[ $url != /* && $url != ./* && $url != ../* && $url == *:* ]]; then
        PROTOCOL=ssh; authority=${url%%:*}; HOST=${authority##*@}; path=${url#*:}
        SAFE_URL="$HOST:$path"
    else
        path=$url
    fi
    # Query strings can contain credentials; never render them.
    SAFE_URL=${SAFE_URL%%\?*}; SAFE_URL=${SAFE_URL%%\#*}
    path=${path%%\?*}; path=${path%%\#*}; path=${path#/}; path=${path%/}
    HOST=${HOST,,}
    for entry in "${HOST_ALIASES[@]}"; do
        alias=${entry%%=*}
        [[ $HOST == "${alias,,}" ]] && HOST=${entry#*=}
    done
    HOST=${HOST,,}
    REPO=${path##*/}; REPO=${REPO%.git}
    [[ $path == */* ]] && OWNER=${path%/*}
    case $HOST in github.com) HOST_ICON='󰊤' ;; gitlab.com) HOST_ICON='' ;; bitbucket.org) HOST_ICON='' ;; esac
    if [[ -n $HOST && -n $OWNER && $PROTOCOL != file ]]; then
        for identity in "${OWNERS[@]}"; do
            if [[ ${identity%%/*} == "$HOST" && ${identity#*/} == "$OWNER" ]]; then OWNED=true; break; fi
        done
    fi
}

# A gitlink must match exactly, at stage zero, and resolve to this child.
verified_edge() {
    local parent=$1 child=$2 rel row meta count=0
    [[ $child == "$parent/"* ]] || return 1
    rel=${child#"$parent/"}
    records_cmd git -C "$parent" ls-files --stage -z -- ":(literal)$rel" || return 1
    for row in "${RECORDS[@]}"; do
        meta=${row%%$'\t'*}
        [[ $meta == '160000 '* && $meta == *' 0' && ${row#*$'\t'} == "$rel" ]] && ((count+=1))
    done
    ((count == 1)) || return 1
    repo_root "$child" && [[ $REPLY == "$child" ]] || return 1
    REPLY=$rel
}

ancestry() {
    local current=$ROOT candidate rel i
    local -a reverse=("$ROOT") hops=()
    while [[ $current != / ]]; do
        candidate=''
        text_cmd git -C "$current" rev-parse --show-superproject-working-tree 2>/dev/null && candidate=$REPLY
        if [[ -z $candidate ]]; then
            repo_root "${current%/*}/" || break
            candidate=$REPLY
        else
            text_cmd canonical_dir "$candidate" || break; candidate=$REPLY
        fi
        [[ $candidate != "$current" ]] || break
        verified_edge "$candidate" "$current" || break
        rel=$REPLY; reverse+=("$candidate"); hops+=("$rel"); current=$candidate
    done
    CHAIN=(); HOPS=()
    for ((i=${#reverse[@]}-1;i>=0;i--)); do CHAIN+=("${reverse[i]}"); done
    for ((i=${#hops[@]}-1;i>=0;i--)); do HOPS+=("${hops[i]}"); done
}

in_progress() {
    local dir=$1 name
    for name in MERGE_HEAD CHERRY_PICK_HEAD REVERT_HEAD rebase-merge rebase-apply sequencer; do
        text_cmd git -C "$dir" rev-parse --git-path "$name" || return 0
        [[ $REPLY == /* ]] || REPLY=$dir/$REPLY
        [[ ! -e $REPLY ]] || return 0
    done
    return 1
}

clean_own_files() {
    local dir=$1
    in_progress "$dir" && return 1
    git -C "$dir" diff --cached --quiet --ignore-submodules=none -- || return 1
    records_cmd git -C "$dir" status --porcelain=v1 -z --untracked-files=all --ignore-submodules=all || return 1
    ((${#RECORDS[@]} == 0))
}

# Return all stage-zero gitlinks, independent of submodule.active filters.
children() {
    local dir=$1 row meta mode oid stage path
    CHILD_PATHS=(); CHILD_OIDS=()
    records_cmd git -C "$dir" ls-files --stage -z || return 1
    for row in "${RECORDS[@]}"; do
        meta=${row%%$'\t'*}; path=${row#*$'\t'}
        read -r mode oid stage <<< "$meta"
        [[ $stage == 0 ]] || return 1
        if [[ $mode == 160000 ]]; then CHILD_PATHS+=("$path"); CHILD_OIDS+=("$oid"); fi
    done
}

safe_child_path() {
    local base=$1 path=$2 part cursor=$1
    [[ -n $path && $path != /* ]] || return 1
    while [[ -n $path ]]; do
        part=${path%%/*}
        [[ -n $part && $part != . && $part != .. ]] || return 1
        cursor+=/$part
        [[ ! -L $cursor ]] || return 1
        [[ ! -e $cursor || -d $cursor ]] || return 1
        [[ $path == */* ]] || break
        path=${path#*/}
    done
    [[ $cursor == "$base/"* ]]
}

submodule_name() {
    local dir=$1 path=$2 key value name='' count=0
    local -a keys=()
    # Read keys and values separately: both subsection names and path values
    # can contain newlines, making config's key-newline-value output ambiguous.
    records_cmd git -C "$dir" config --no-includes --null --name-only --file .gitmodules --get-regexp '^submodule\..*\.path$' 2>/dev/null || return 1
    keys=("${RECORDS[@]}")
    for key in "${keys[@]}"; do
        records_cmd git -C "$dir" config --no-includes --null --file .gitmodules --get-all "$key" || return 1
        ((${#RECORDS[@]} == 1)) || return 1
        value=${RECORDS[0]}
        if [[ $value == "$path" ]]; then name=${key#submodule.}; name=${name%.path}; ((count+=1)); fi
    done
    ((count == 1)) || return 1
    REPLY=$name
}

upstream() {
    local dir=$1
    text_cmd git -C "$dir" symbolic-ref --quiet --short HEAD 2>/dev/null || return 1; BRANCH=$REPLY
    text_cmd git -C "$dir" config --get "branch.$BRANCH.remote" || return 1; UP_REMOTE=$REPLY
    text_cmd git -C "$dir" config --get-all "branch.$BRANCH.merge" || return 1; UP_REF=$REPLY
    [[ $UP_REMOTE != . && $UP_REF == refs/heads/* && $UP_REF != *$'\n'* ]] || return 1
    git check-ref-format "$UP_REF" >/dev/null 2>&1 || return 1
    TRACKING="refs/remotes/$UP_REMOTE/${UP_REF#refs/heads/}"
    git check-ref-format "$TRACKING" >/dev/null 2>&1
}

fetch_branch() {
    git -C "$1" -c fetch.recurseSubmodules=false fetch --quiet --no-tags --no-recurse-submodules \
        --refmap= -- "$2" "$3:$4" >/dev/null 2>&1
}

remote_contains() {
    text_cmd git -C "$1" for-each-ref --format='%(refname)' --contains "$2" refs/remotes/ 2>/dev/null && [[ -n $REPLY ]]
}

# Do not let a parent change remove/retype populated submodules or adopt an
# unrelated existing directory. Such topology edits need deliberate Git work.
safe_topology() {
    local dir=$1 target=$2 row meta path mode oid current
    local -A old=() next=()
    children "$dir" || return 1
    for path in "${CHILD_PATHS[@]}"; do old[$path]=1; done
    records_cmd git -C "$dir" ls-tree -r -z "$target" || return 1
    for row in "${RECORDS[@]}"; do
        meta=${row%%$'\t'*}; path=${row#*$'\t'}; read -r mode current oid <<< "$meta"
        [[ $mode == 160000 ]] || continue
        next[$path]=1
        safe_child_path "$dir" "$path" || return 1
        [[ -v old[$path] || ! -e $dir/$path ]] || return 1
    done
    for path in "${!old[@]}"; do [[ -v next[$path] ]] || return 1; done
}

