# shellcheck disable=SC2034,SC2153
# Adapted from git-it 0.1.0; see LICENSE.
cleanup_locks() {
    dots::progress_stop
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
    dots::progress_start 'Discovering submodules'
    local dir=$1 i path oid child progress_status=0 child_status
    local -a paths=() oids=()
    children "$dir" || { event "$dir" blocked 'cannot enumerate a conflict-free submodule index'; return 1; }
    paths=("${CHILD_PATHS[@]}"); oids=("${CHILD_OIDS[@]}")
    dots::progress_sequence_start 'Synchronizing submodules' "${#paths[@]}" repo
    for ((i=0;i<${#paths[@]};i++)); do
        path=${paths[i]}; oid=${oids[i]}; child=$dir/$path
        dots::progress_step_start "Submodule: $path" "$((i+1))"
        if ! safe_child_path "$dir" "$path" || [[ -L $child/.git ]] || ! submodule_name "$dir" "$path"; then
            event "$child" blocked 'unsafe path or missing/ambiguous .gitmodules entry'; progress_status=1; continue
        fi
        if ! repo_root "$child" || [[ $REPLY != "$child" ]]; then
            if ((!INIT)); then event "$child" blocked 'not initialized; use sync --init to permit downloading this submodule'; progress_status=1; continue; fi
            if ((DRY_RUN)); then event "$child" planned 'initialize at recorded commit; deeper structure requires download'; continue; fi
            # Refuse to adopt any nonempty directory, including hidden files.
            if [[ -d $child ]] && [[ -n $(find "$child" -mindepth 1 -maxdepth 1 -print -quit) ]]; then
                event "$child" blocked 'uninitialized submodule directory is not empty'; progress_status=1; continue
            fi
            view_phase "Initializing submodule: $path"
            if ! git --literal-pathspecs -C "$dir" -c submodule.recurse=false submodule update --init --checkout -- "$path" >/dev/null 2>&1; then
                event "$child" failed 'initialization failed; check URL, credentials, and Git transport policy'; progress_status=1; continue
            fi
        fi
        child_status=0
        sync_node "$child" "$oid" "$dir" "$path" || child_status=$?
        ((child_status!=0)) || child_status=${SYNC_PROGRESS_STATUS:-0}
        ((child_status==0)) || progress_status=1
        dots::progress_step_end "$child_status"
    done
    dots::progress_sequence_end "$progress_status"
    SYNC_PROGRESS_STATUS=$progress_status
    return 0
}

sync_node() {
    # Traversal historically reports descendant failures through RESULT while
    # returning the node's own status. Keep that contract and retain failure in
    # the progress model independently, including when the last child failed.
    local depth=${DOTS_PROGRESS_DEPTH:-0} rc=0 progress_status
    SYNC_PROGRESS_STATUS=0
    dots::progress_sequence_start "Synchronizing ${1##*/}" 4 step
    sync_node_work "$@" || rc=$?
    progress_status=$rc
    ((progress_status!=0)) || progress_status=${SYNC_PROGRESS_STATUS:-0}
    while ((${DOTS_PROGRESS_DEPTH:-0}>depth)); do dots::progress_sequence_end "$progress_status"; done
    SYNC_PROGRESS_STATUS=$progress_status
    return "$rc"
}
sync_node_work() {
    local dir=$1 pinned=${2:-} parent=${3:-} path=${4:-} before target name branch remote ref tracking attached=0
    dots::progress_step_start 'Inspecting repository'
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
    dots::progress_step_end
    dots::progress_step_start 'Fetching selected commit'
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
            view_phase 'Fetching recorded commit'
            if ! git -C "$dir" fetch --quiet --no-tags --no-recurse-submodules -- "$remote" "$target" >/dev/null 2>&1; then
                event "$dir" failed 'recorded commit could not be fetched'; return 1
            fi
        fi
    fi
    dots::progress_step_end
    dots::progress_step_start 'Updating repository'
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
        elif ! { view_phase "Fast-forwarding repository"; git -C "$dir" -c submodule.recurse=false merge --ff-only --no-edit --no-overwrite-ignore "$target" >/dev/null 2>&1; }; then
            event "$dir" failed 'fast-forward failed; local work was not reset'; return 1
        else event "$dir" updated 'fast-forwarded upstream'; fi
    elif [[ $before == "$target" ]]; then event "$dir" unchanged 'at selected submodule commit'
    else
        if ! remote_contains "$dir" "$before"; then event "$dir" blocked 'refusing to leave a submodule commit without remote reachability evidence'; return 1; fi
        if ! safe_topology "$dir" "$target"; then event "$dir" blocked 'submodule topology change needs manual review'; return 1; fi
        view_phase "Checking out selected commit"
        if ! git -C "$dir" -c submodule.recurse=false checkout --quiet --detach --no-overwrite-ignore "$target" -- >/dev/null 2>&1; then
            event "$dir" failed 'submodule checkout failed; local work was not reset'; return 1
        else event "$dir" updated 'checked out selected commit; parent pointer is not staged'; fi
    fi
    view_changes "$dir" "$before"
    dots::progress_step_end
    dots::progress_step_start 'Synchronizing submodules'
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
    dots::progress_start 'Collecting publish inputs'
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
    local i xy path old
    local -a selected_rows=("${RECORDS[@]}")
    for ((i=0;i<${#selected_rows[@]};i++)); do
        row=${selected_rows[i]}; xy=${row:0:2}; path=${row:3}; old=''
        if [[ $xy == *R* || $xy == *C* ]]; then ((i+=1)); old=${selected_rows[i]}; fi
        # Associative array declared by views.bash.
        # shellcheck disable=SC2004
        VIEW_RENAMES[$dir/$path]=$old
        if ((ALL)) || [[ ${xy:0:1} != ' ' && ${xy:0:1} != '?' ]]; then
            event "$dir" selected "$xy $path" "$path" "$xy"
        fi
    done
    return 0
}

publish_node() {
    dots::progress_sequence_run "Publishing ${1##*/}" 4 step publish_node_work "$@"
}
publish_node_work() {
    local dir=$1 parent=${PARENT[$1]} remote ref tracking before destination path child index head old row meta
    dots::progress_step_start 'Checking publication inputs'
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
    if ((${SCOPED_PUBLISH:-0})) && ! recheck_publish_scope; then
        event "$dir" blocked 'submodule selection changed during preflight'; return 1
    fi
    dots::progress_step_end
    dots::progress_step_start 'Committing selected changes'
    if ((ALL)); then
        stage_own_files "$dir" || { event "$dir" failed 'staging failed; staged changes retained (inspect git status)'; return 1; }
    fi
    if ! git -C "$dir" diff --cached --quiet --ignore-submodules=none --; then
        view_phase 'Committing selected changes'
        if ! git -C "$dir" commit -m "$MESSAGE" >/dev/null 2>&1; then
            event "$dir" failed 'commit failed; staged changes retained (check identity and hooks)'; return 1
        fi
    fi
    dots::progress_step_end
    dots::progress_step_start 'Pushing selected changes'
    view_phase 'Pushing selected changes'
    if ! git -C "$dir" -c push.followTags=false push --porcelain --recurse-submodules=check -- "$destination" "HEAD:$ref" >/dev/null 2>&1; then
        event "$dir" failed 'push failed; local commit retained and parent publication blocked'; return 1
    fi
    dots::progress_step_end
    dots::progress_step_start 'Verifying publication'
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

# The shared selector emits a digest followed by NUL-delimited edge records.
select_publish_scope() {
    local -a args=(_select -C "$ROOT")
    if ((ALL_SUBMODULES)); then args+=(--all-submodules); else args+=(-- "$SCOPE_PATH"); fi
    records_cmd python3 -B "$LIB/inspection.py" "${args[@]}"
}
recheck_publish_scope() {
    select_publish_scope && [[ ${RECORDS[0]:-} == "$SCOPE_HASH" ]]
}
report_parent_pointers() {
    local dir parent head i
    for ((i=0;i<${#SCOPE_ROOTS[@]};i++)); do
        dir=${SCOPE_ROOTS[i]}; parent=${SCOPE_PARENTS[i]}
        repo_root "$dir" && [[ $REPLY == "$dir" ]] || continue
        text_cmd git -C "$dir" rev-parse --verify HEAD 2>/dev/null || continue
        head=$REPLY
        if [[ $head != "${SCOPE_OIDS[i]}" ]]; then
            event "$parent" pending "Submodule ${dir#"$parent/"} differs from the parent index; record its pointer separately. Parent index was not changed by this command."
        fi
    done
}
operations_main() {
    local DOTS_PROGRESS_STARTED='' progress_count=0
    SCOPE_ROOTS=(); SCOPE_PARENTS=(); SCOPE_OIDS=(); SCOPE_HASH=''
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
        dots::progress_start 'Collecting publish inputs'
        if [[ -z $MESSAGE ]]; then
            text_cmd date -u '+%Y-%m-%d %H:%M UTC'; MESSAGE="Sync via ${HOSTNAME:-unknown} on $REPLY"
        fi
        if ((SCOPED_PUBLISH)); then
            select_publish_scope || return $?
            local -a selected_edges=("${RECORDS[@]}")
            local scope_i
            SCOPE_HASH=${selected_edges[0]}
            for ((scope_i=1;scope_i<${#selected_edges[@]};scope_i+=5)); do
                SCOPE_ROOTS+=("${selected_edges[scope_i]}")
                SCOPE_PARENTS+=("${selected_edges[scope_i+1]}")
                SCOPE_OIDS+=("${selected_edges[scope_i+2]}")
                if [[ ${selected_edges[scope_i+3]} != available ]]; then
                    event "${selected_edges[scope_i]}" blocked "${selected_edges[scope_i+4]}"; RESULT=1
                else
                    dots::progress_run 'Collecting publish inputs' collect_publish "${selected_edges[scope_i]}" || RESULT=1
                fi
            done
            if ((!JSON)); then dots::info 'Only selected subtrees will publish; excluded parent indexes remain unchanged.'; fi
            if ((!JSON && ${#SCOPE_ROOTS[@]} == 0)); then dots::info 'No registered submodules.'; fi
        else
            dots::progress_run 'Collecting publish inputs' collect_publish "$ROOT" || RESULT=1
        fi
        dots::progress_sequence_start 'Publishing repositories' "${#PUB_DIRS[@]}" repo
        dots::progress_update 'Reviewing publication'
        dots::progress_stop
        local dir parent answer progress_status
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
                # Source only at the existing approval point; JSON never probes Gum.
                source "$LIB/../interactive.bash"
                if ((!JSON)) && dots::gum_confirm_available; then
                    answer=$(dots::gum_confirm 'Publish the selected changes?' Publish) || return $?
                    if [[ $answer == Publish ]]; then answer=y; else answer=n; fi
                else
                    printf '%sPublish the selected changes? [y/N]%s ' "$ERR_BOLD" "$ERR_RESET" >&2
                    IFS= read -r answer || answer=''
                fi
                if [[ $answer != y && $answer != Y ]]; then dots::progress_cancel; dots::progress_sequence_end 1; event "$ROOT" cancelled 'nothing committed or pushed'; operations_report; return "$RESULT"; fi
            fi
            if ((!JSON)); then dots::heading "Publishing selected repositories"; LAST_EVENT_REPO=''; fi
            for dir in "${PUB_DIRS[@]}"; do
                dots::progress_step_start "Publishing repository: ${dir##*/}" "$((progress_count+1))"
                parent=${PARENT[$dir]}
                if ((SCOPED_PUBLISH)) && ! recheck_publish_scope; then
                    event "$dir" blocked 'submodule selection changed after preview'; RESULT=1; break
                fi
                # Validate parent BEFORE permitting the known child-induced change.
                if [[ -n $parent ]]; then
                    if ! fingerprint "$parent" || [[ $REPLY != "${SNAPSHOTS[$parent]}" ]]; then
                        BLOCKED[$dir]=1; BLOCKED[$parent]=1
                    fi
                fi
                progress_status=0
                if ! publish_node "$dir"; then
                    progress_status=1
                    RESULT=1; [[ -z $parent ]] || BLOCKED[$parent]=1
                fi
                ((progress_count+=1))
                dots::progress_step_end "$progress_status"
                dots::progress_stop
            done
        fi
        dots::progress_sequence_end "$RESULT"
    fi
    dots::progress_stop
    if ((SCOPED_PUBLISH && !DRY_RUN)); then report_parent_pointers; fi
    operations_report
    return "$RESULT"
}


# Stage ordinary files only. Gitlinks are deliberately staged by publication.
stage_own_files() {
    local dir=$1 path
    local -a paths=(.)
    children "$dir" || return 1
    for path in "${CHILD_PATHS[@]}"; do paths+=(":(top,exclude,literal)$path"); done
    # Let Git handle tracked paths beneath ignored directories. Explicitly naming
    # every tracked file can trigger ignored-ancestor errors after partial staging.
    # Literal gitlink exclusions preserve the pointers selected by publication.
    git -C "$dir" add --all -- "${paths[@]}" >/dev/null 2>&1
}
