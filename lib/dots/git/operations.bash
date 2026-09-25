# shellcheck disable=SC2034,SC2153
# Adapted from git-it 0.1.0; see LICENSE.
cleanup_locks() {
    local dir
    for dir in "${LOCKS[@]}"; do rmdir -- "$dir" 2>/dev/null || :; done
}

lock_repo() {
    local dir=$1 common
    ((DRY_RUN)) && return 0
    text_cmd git -C "$dir" rev-parse --git-common-dir || return 1
    common=$REPLY; [[ $common == /* ]] || common=$dir/$common
    text_cmd canonical_dir "$common" || return 1; common=$REPLY/git-it.lock
    [[ -v HELD[$common] ]] && return 0
    if ! mkdir -- "$common" 2>/dev/null; then
        event "$dir" blocked 'another dots git or git-it operation holds the lock (or a stale lock needs manual inspection)'
        return 1
    fi
    HELD[$common]=1; LOCKS+=("$common")
}

sync_children() {
    local dir=$1 i path oid child
    local -a paths=() oids=()
    children "$dir" || { event "$dir" blocked 'cannot enumerate a conflict-free submodule index'; return 1; }
    paths=("${CHILD_PATHS[@]}"); oids=("${CHILD_OIDS[@]}")
    for ((i=0;i<${#paths[@]};i++)); do
        path=${paths[i]}; oid=${oids[i]}; child=$dir/$path
        if ! safe_child_path "$dir" "$path" || [[ -L $child/.git ]] || ! submodule_name "$dir" "$path"; then
            event "$child" blocked 'unsafe path or missing/ambiguous .gitmodules entry'; continue
        fi
        if ! repo_root "$child" || [[ $REPLY != "$child" ]]; then
            if ((!INIT)); then event "$child" blocked 'not initialized; use sync --init to permit downloading this submodule'; continue; fi
            if ((DRY_RUN)); then event "$child" planned 'initialize at recorded commit; deeper structure requires download'; continue; fi
            # Refuse to adopt any nonempty directory, including hidden files.
            if [[ -d $child ]] && [[ -n $(find "$child" -mindepth 1 -maxdepth 1 -print -quit) ]]; then
                event "$child" blocked 'uninitialized submodule directory is not empty'; continue
            fi
            if ! git --literal-pathspecs -C "$dir" -c submodule.recurse=false submodule update --init --checkout -- "$path" >/dev/null 2>&1; then
                event "$child" failed 'initialization failed; check URL, credentials, and Git transport policy'; continue
            fi
        fi
        sync_node "$child" "$oid" "$dir" "$path" || :
    done
}

sync_node() {
    local dir=$1 pinned=${2:-} parent=${3:-} path=${4:-} before target name branch remote ref tracking attached=0
    [[ ! -v VISITED[$dir] ]] || { event "$dir" blocked 'repeated repository in traversal'; return 1; }
    VISITED[$dir]=1
    lock_repo "$dir" || return 1
    if ! clean_own_files "$dir"; then event "$dir" blocked 'local edits, staged changes, untracked files, or an operation in progress'; return 1; fi
    text_cmd git -C "$dir" rev-parse --verify HEAD || { event "$dir" blocked 'repository has no commit'; return 1; }; before=$REPLY
    if [[ -z $pinned ]]; then
        upstream "$dir" || { event "$dir" blocked 'root needs an attached branch with one configured upstream'; return 1; }
        remote=$UP_REMOTE; ref=$UP_REF; tracking=$TRACKING; attached=1
    elif ((ADVANCE)); then
        submodule_name "$parent" "$path" || return 1; name=$REPLY
        branch=''
        if text_cmd git -C "$parent" config --get "submodule.$name.branch" 2>/dev/null; then branch=$REPLY
        elif text_cmd git -C "$parent" config --file .gitmodules --get "submodule.$name.branch" 2>/dev/null; then branch=$REPLY; fi
        if [[ $branch == . ]]; then
            text_cmd git -C "$parent" symbolic-ref --quiet --short HEAD 2>/dev/null || { event "$dir" blocked 'branch=. requires an attached parent'; return 1; }; branch=$REPLY
        fi
        if [[ -n $branch ]]; then
            select_remote "$dir" || return 1; remote=${REMOTE:-origin}; ref=refs/heads/$branch; tracking=refs/remotes/$remote/$branch
            git check-ref-format "$ref" >/dev/null 2>&1 || { event "$dir" blocked 'invalid configured submodule branch'; return 1; }
        elif upstream "$dir"; then remote=$UP_REMOTE; ref=$UP_REF; tracking=$TRACKING
        else event "$dir" blocked '--remote requires a configured submodule branch or attached upstream'; return 1; fi
    fi
    if ((DRY_RUN)); then
        if [[ -z $pinned || $ADVANCE == 1 ]]; then
            event "$dir" planned "fetch and fast-forward/check out $remote/$ref; remote state not checked"
        else event "$dir" planned "check out parent-recorded commit $pinned; missing objects may need download"; fi
        sync_children "$dir"; return 0
    fi
    if [[ -z $pinned || $ADVANCE == 1 ]]; then
        if ! fetch_branch "$dir" "$remote" "$ref" "$tracking"; then event "$dir" failed 'fetch failed; check upstream, credentials, or rewritten remote history'; return 1; fi
        text_cmd git -C "$dir" rev-parse --verify "$tracking^{commit}" || return 1; target=$REPLY
    else
        target=$pinned
        if ! git -C "$dir" cat-file -e "$target^{commit}" 2>/dev/null; then
            select_remote "$dir" || return 1; remote=${REMOTE:-origin}
            if ! git -C "$dir" fetch --quiet --no-tags --no-recurse-submodules -- "$remote" "$target" >/dev/null 2>&1; then
                event "$dir" failed 'recorded commit could not be fetched'; return 1
            fi
        fi
    fi
    # Fetch can invoke credential helpers; recheck worktree state afterwards.
    if ! clean_own_files "$dir" || ! text_cmd git -C "$dir" rev-parse HEAD || [[ $REPLY != "$before" ]]; then
        event "$dir" blocked 'repository changed during fetch'; return 1
    fi
    if ((attached)); then
        if git -C "$dir" merge-base --is-ancestor "$target" HEAD; then
            event "$dir" unchanged 'already current or locally ahead; local commits retained'
        elif ! git -C "$dir" merge-base --is-ancestor HEAD "$target"; then
            event "$dir" blocked 'local and upstream histories diverged'; return 1
        elif ! safe_topology "$dir" "$target"; then
            event "$dir" blocked 'submodule removal, replacement, or occupied new path needs manual review'; return 1
        elif ! git -C "$dir" -c submodule.recurse=false merge --ff-only --no-edit --no-overwrite-ignore "$target" >/dev/null 2>&1; then
            event "$dir" failed 'fast-forward failed; local work was not reset'; return 1
        else event "$dir" updated 'fast-forwarded upstream'; fi
    elif [[ $before == "$target" ]]; then event "$dir" unchanged 'at selected submodule commit'
    else
        if ! remote_contains "$dir" "$before"; then event "$dir" blocked 'refusing to leave a submodule commit without remote reachability evidence'; return 1; fi
        if ! safe_topology "$dir" "$target"; then event "$dir" blocked 'submodule topology change needs manual review'; return 1; fi
        if ! git -C "$dir" -c submodule.recurse=false checkout --quiet --detach --no-overwrite-ignore "$target" -- >/dev/null 2>&1; then
            event "$dir" failed 'submodule checkout failed; local work was not reset'; return 1
        else event "$dir" updated 'checked out selected commit; parent pointer is not staged'; fi
    fi
    sync_children "$dir"
}

# Snapshot all publish inputs, including unstaged/untracked contents for --all.
fingerprint() {
    local dir=$1
    # shellcheck disable=SC2016
    text_cmd bash -o pipefail -c '
        dir=$1; all=$2
        {
            git -C "$dir" rev-parse HEAD || exit
            git -C "$dir" status --porcelain=v1 -z --untracked-files=all --ignore-submodules=all || exit
            git -C "$dir" diff --cached --binary --no-ext-diff --no-textconv || exit
            if [[ $all == 1 ]]; then
                git -C "$dir" diff --binary --no-ext-diff --no-textconv --ignore-submodules=all || exit
                while IFS= read -r -d "" file; do
                    if [[ -L $dir/$file ]]; then readlink -- "$dir/$file" || exit
                    elif [[ -f $dir/$file ]]; then git hash-object --no-filters -- "$dir/$file" || exit
                    else exit 1; fi
                done < <(git -C "$dir" ls-files --others --exclude-standard -z)
            fi
        } | sha256sum
    ' bash "$dir" "$ALL"
}

collect_publish() {
    local dir=$1 parent=${2:-} path child
    local -a paths=()
    [[ ! -v VISITED[$dir] ]] || { event "$dir" blocked 'repeated repository'; return 1; }
    VISITED[$dir]=1; PARENT[$dir]=$parent
    lock_repo "$dir" || { BLOCKED[$dir]=1; return 1; }
    if ! children "$dir"; then BLOCKED[$dir]=1; event "$dir" blocked 'conflicted index'; return 1; fi
    paths=("${CHILD_PATHS[@]}")
    for path in "${paths[@]}"; do
        child=$dir/$path
        if ! safe_child_path "$dir" "$path" || [[ -L $child/.git ]] || ! submodule_name "$dir" "$path" || ! repo_root "$child" || [[ $REPLY != "$child" ]]; then
            BLOCKED[$dir]=1; event "$child" blocked 'initialize the submodule before recursive publication'; continue
        fi
        collect_publish "$child" "$dir" || BLOCKED[$dir]=1
    done
    if ! fingerprint "$dir"; then BLOCKED[$dir]=1; event "$dir" blocked 'cannot snapshot publish inputs'; return 1; fi
    SNAPSHOTS[$dir]=$REPLY; PUB_DIRS+=("$dir")
}

publish_destination() {
    local dir=$1 row
    upstream "$dir" || return 1
    # Explicit upstream refspecs prevent push.default or push refspec surprises.
    if git -C "$dir" config --get-all "remote.$UP_REMOTE.push" >/dev/null 2>&1 ||
       git -C "$dir" config --get "branch.$BRANCH.pushRemote" >/dev/null 2>&1 ||
       git -C "$dir" config --get remote.pushDefault >/dev/null 2>&1; then return 1; fi
    text_cmd git -C "$dir" config --bool --get "remote.$UP_REMOTE.mirror" 2>/dev/null && [[ $REPLY == true ]] && return 1
    text_cmd git -C "$dir" remote get-url --push --all -- "$UP_REMOTE" || return 1
    [[ -n $REPLY && $REPLY != *$'\n'* ]] || return 1
    row=$REPLY; parse_url "$row"
    [[ $OWNED == true ]] || return 1
    PUSH_URL=$row
}

publication_needed() {
    local dir=$1 parent=${PARENT[$1]} path row meta index head
    git -C "$dir" diff --cached --quiet --ignore-submodules=none -- || return 0
    if ((ALL)); then
        records_cmd git -C "$dir" status --porcelain=v1 -z --untracked-files=all --ignore-submodules=all || return 0
        ((${#RECORDS[@]} == 0)) || return 0
    fi
    if [[ -n $parent ]]; then
        path=${dir#"$parent/"}
        text_cmd git -C "$dir" rev-parse HEAD || return 0; head=$REPLY
        records_cmd git -C "$parent" ls-files --stage -z -- ":(literal)$path" || return 0
        ((${#RECORDS[@]} == 1)) || return 0
        row=${RECORDS[0]}; meta=${row%%$'\t'*}; index=${meta#* }; index=${index%% *}
        [[ $index == "$head" ]] || return 0
    fi
    if upstream "$dir"; then
        git -C "$dir" rev-parse --verify "$TRACKING" >/dev/null 2>&1 || return 0
        git -C "$dir" merge-base --is-ancestor HEAD "$TRACKING" || return 0
    fi
    return 1
}

publish_preview() {
    local dir=$1 row parent=${PARENT[$1]} dest
    if [[ -v BLOCKED[$dir] ]]; then
        event "$dir" blocked 'required child or preflight check failed'
        [[ -z $parent ]] || BLOCKED[$parent]=1
        return 1
    fi
    if publication_needed "$dir" || [[ -v EXPECTED[$dir] ]]; then
        if in_progress "$dir" || ! publish_destination "$dir"; then
            BLOCKED[$dir]=1; [[ -z $parent ]] || BLOCKED[$parent]=1
            event "$dir" blocked 'needs an owned push URL, attached upstream, unambiguous push configuration, and no operation in progress'
            return 1
        fi
        dest="$SAFE_URL → $UP_REF"
        PREVIEW_DEST[$dir]=$PUSH_URL; PREVIEW_REF[$dir]=$UP_REF
        PREVIEW_REMOTE[$dir]=$UP_REMOTE; PREVIEW_BRANCH[$dir]=$BRANCH
        ((PUBLISH_CANDIDATES+=1))
        event "$dir" planned "branch $BRANCH: publish to $dest; message: $MESSAGE"
        [[ -z $parent ]] || EXPECTED[$parent]=1
    else
        event "$dir" unchanged 'no selected changes or known ahead commits (remote state not fetched)'
        return 0
    fi
    records_cmd git -C "$dir" status --porcelain=v1 -z --untracked-files=all || return 1
    local skip=0
    for row in "${RECORDS[@]}"; do
        if ((skip)); then skip=0; continue; fi
        [[ ${row:0:2} != *R* && ${row:0:2} != *C* ]] || skip=1
        if ((ALL)) || [[ ${row:0:1} != ' ' && ${row:0:1} != '?' ]]; then
            event "$dir" selected "${row:0:2} ${row:3}" "${row:3}" "${row:0:2}"
        fi
    done
    return 0
}

publish_node() {
    local dir=$1 parent=${PARENT[$1]} remote ref tracking before destination path child index head old row meta
    [[ ! -v BLOCKED[$dir] ]] || { event "$dir" blocked 'a required child or preflight check failed'; return 1; }
    if ! fingerprint "$dir" || [[ $REPLY != "${SNAPSHOTS[$dir]}" ]]; then
        event "$dir" blocked 'publish inputs changed after preview'; return 1
    fi
    in_progress "$dir" && { event "$dir" blocked 'Git operation in progress'; return 1; }
    # A clean dependency can stay detached or foreign when its parent pointer
    # is unchanged. Otherwise it must pass the same publication checks.
    if ! publication_needed "$dir"; then event "$dir" unchanged 'no selected changes or known ahead commits'; return 0; fi
    if ! publish_destination "$dir"; then
        event "$dir" blocked 'publication requires an owned push URL, attached upstream, and unambiguous push configuration'; return 1
    fi
    if [[ $PUSH_URL != "${PREVIEW_DEST[$dir]:-}" || $UP_REF != "${PREVIEW_REF[$dir]:-}" ||
          $UP_REMOTE != "${PREVIEW_REMOTE[$dir]:-}" || $BRANCH != "${PREVIEW_BRANCH[$dir]:-}" ]]; then
        event "$dir" blocked 'branch or destination changed after the preview'; return 1
    fi
    remote=$UP_REMOTE; ref=$UP_REF; tracking=$TRACKING; destination=$PUSH_URL
    text_cmd git -C "$dir" rev-parse HEAD || return 1; before=$REPLY
    if ! fetch_branch "$dir" "$remote" "$ref" "$tracking"; then event "$dir" failed 'upstream fetch failed'; return 1; fi
    if ! git -C "$dir" merge-base --is-ancestor "$tracking" HEAD; then
        event "$dir" blocked 'remote is ahead or diverged; sync or resolve manually before publishing'; return 1
    fi
    if ! fingerprint "$dir" || [[ $REPLY != "${SNAPSHOTS[$dir]}" ]] || ! publish_destination "$dir" ||
       [[ $PUSH_URL != "$destination" || $UP_REF != "$ref" || $UP_REMOTE != "$remote" || $BRANCH != "${PREVIEW_BRANCH[$dir]}" ]]; then
        event "$dir" blocked 'inputs or destination changed during preflight'; return 1
    fi
    if ((ALL)); then
        stage_own_files "$dir" || { event "$dir" failed 'staging failed; inspect index'; return 1; }
    fi
    if ! git -C "$dir" diff --cached --quiet --ignore-submodules=none --; then
        if ! git -C "$dir" commit -m "$MESSAGE" >/dev/null 2>&1; then
            event "$dir" failed 'commit failed; staged changes retained (check identity and hooks)'; return 1
        fi
    fi
    if ! git -C "$dir" -c push.followTags=false push --porcelain --recurse-submodules=check -- "$destination" "HEAD:$ref" >/dev/null 2>&1; then
        event "$dir" failed 'push failed; local commit retained and parent publication blocked'; return 1
    fi
    event "$dir" published 'selected changes and ahead commits pushed'
    # Pushing an explicit URL need not update a named remote-tracking ref.
    # Refresh evidence before Git checks availability in the parent's push.
    if ! fetch_branch "$dir" "$destination" "$ref" "$tracking"; then
        event "$dir" failed 'push completed, but refreshing remote evidence failed; parent remains blocked'; return 1
    fi
    if [[ -n $parent ]]; then
        # Parent may have deliberately staged an older pointer. Do not replace it.
        path=${dir#"$parent/"}
        records_cmd git -C "$parent" ls-files --stage -z -- ":(literal)$path" || return 1
        row=${RECORDS[0]}; meta=${row%%$'\t'*}; index=${meta#* }; index=${index%% *}
        records_cmd git -C "$parent" ls-tree -z HEAD -- ":(literal)$path" || return 1
        old=''; if ((${#RECORDS[@]})); then meta=${RECORDS[0]%%$'\t'*}; old=${meta##* }; fi
        text_cmd git -C "$dir" rev-parse HEAD || return 1; head=$REPLY
        if [[ $index != "$old" && $index != "$head" ]]; then
            event "$parent" blocked 'pre-existing staged child pointer differs; preserved for manual review'; return 1
        fi
        # Child worktree changes are excluded from the parent's fingerprint;
        # its own files and staged gitlinks must still match the preview.
        if ! fingerprint "$parent" || [[ $REPLY != "${SNAPSHOTS[$parent]}" ]]; then
            event "$parent" blocked 'parent changed during child publication'; return 1
        fi
        git -C "$parent" add -- ":(literal)$path" >/dev/null 2>&1 || return 1
        fingerprint "$parent" || return 1; SNAPSHOTS[$parent]=$REPLY
    fi
}

operations_main() {
    EVENT_DIRS=(); EVENT_STATES=(); EVENT_REASONS=(); EVENT_FILES=(); EVENT_CODES=(); LAST_EVENT_REPO=''; LOCKS=(); PUB_DIRS=(); RESULT=0; PUBLISH_CANDIDATES=0
    declare -gA HELD=() VISITED=() BLOCKED=() SNAPSHOTS=() PARENT=() EXPECTED=()
    declare -gA PREVIEW_DEST=() PREVIEW_REF=() PREVIEW_REMOTE=() PREVIEW_BRANCH=()
    trap cleanup_locks EXIT
    trap 'exit 130' INT
    trap 'exit 143' TERM
    if ((OUTERMOST)); then ancestry; ROOT=${CHAIN[0]}; fi
    if [[ $CMD == sync ]]; then sync_node "$ROOT" || RESULT=1
    else
        command -v sha256sum >/dev/null 2>&1 || die 3 'publishing requires sha256sum'
        if [[ -z $MESSAGE ]]; then
            text_cmd date -u '+%Y-%m-%d %H:%M UTC'; MESSAGE="Sync via ${HOSTNAME:-unknown} on $REPLY"
        fi
        collect_publish "$ROOT" || RESULT=1
        local dir parent answer
        ((!JSON)) && dots::heading "Publish preview"
        for dir in "${PUB_DIRS[@]}"; do publish_preview "$dir"; done
        if ((!JSON && PUBLISH_CANDIDATES > 0)); then dots::info "Published child pointers may be staged in their parents."; fi
        if ((!DRY_RUN && PUBLISH_CANDIDATES > 0)); then
            if ((!YES)); then
                [[ -t 0 ]] || die 2 'publish requires a terminal confirmation or --yes'
                if ((JSON)); then
                    local preview_i
                    {
                        LAST_EVENT_REPO=''
                        for ((preview_i=0;preview_i<${#EVENT_DIRS[@]};preview_i++)); do
                            render_event "${EVENT_DIRS[preview_i]}" "${EVENT_STATES[preview_i]}" "${EVENT_REASONS[preview_i]}" "${EVENT_FILES[preview_i]}"
                        done
                    } >&2
                fi
                printf '%sPublish the selected changes? [y/N]%s ' "$ERR_BOLD" "$ERR_RESET" >&2
                IFS= read -r answer || answer=''
                if [[ $answer != y && $answer != Y ]]; then event "$ROOT" cancelled 'nothing committed or pushed'; operations_report; return "$RESULT"; fi
            fi
            if ((!JSON)); then dots::heading "Publishing selected repositories"; LAST_EVENT_REPO=''; fi
            for dir in "${PUB_DIRS[@]}"; do
                parent=${PARENT[$dir]}
                # Validate parent BEFORE permitting the known child-induced change.
                if [[ -n $parent ]]; then
                    if ! fingerprint "$parent" || [[ $REPLY != "${SNAPSHOTS[$parent]}" ]]; then
                        BLOCKED[$dir]=1; BLOCKED[$parent]=1
                    fi
                fi
                if ! publish_node "$dir"; then
                    RESULT=1; [[ -z $parent ]] || BLOCKED[$parent]=1
                fi
            done
        fi
    fi
    operations_report
    return "$RESULT"
}


# Stage ordinary files only. Gitlinks are deliberately staged by publication.
stage_own_files() {
    local dir=$1 path
    local -A links=()
    local -a files=() paths=()
    children "$dir" || return 1
    for path in "${CHILD_PATHS[@]}"; do links[$path]=1; done
    records_cmd git -C "$dir" ls-files --cached --others --exclude-standard -z || return 1
    paths=("${RECORDS[@]}")
    for path in "${paths[@]}"; do
        [[ -v links[$path] ]] || files+=(":(literal)$path")
    done
    ((${#files[@]})) || return 0
    git -C "$dir" add --all -- "${files[@]}" >/dev/null 2>&1
}
