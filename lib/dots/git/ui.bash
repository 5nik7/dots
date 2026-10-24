# Human presentation and schema-1 events. Domain records remain undecorated.
# shellcheck source-path=SCRIPTDIR
# shellcheck disable=SC2034
# shellcheck source=../ui.bash
source "$DOTS_LIB_DIR/ui.bash"
colors() {
    dots::style
    BOLD=$DOTS_UI_BOLD RESET=$DOTS_UI_RESET GREEN=$DOTS_UI_GREEN
    CYAN=$DOTS_UI_CYAN RED=$DOTS_UI_RED YELLOW=$DOTS_UI_YELLOW
    dots::style 2
    ERR_BOLD=$DOTS_UI_BOLD ERR_RESET=$DOTS_UI_RESET
}
die() { display "$2"; dots::error "dots git: $REPLY"; exit "$1"; }
# Labels retain their full porcelain meaning; color highlights the strongest state.
file_status_style() {
    local xy=$1 role=staged
    if [[ $xy == *U* || $xy == AA || $xy == DD ]]; then role=conflict
    elif [[ $xy == '??' ]]; then role=untracked
    elif [[ $xy == '!!' ]]; then role=ignored
    elif [[ $xy == *D* ]]; then role=deleted
    elif [[ $xy == *R* ]]; then role=renamed
    elif [[ $xy == *C* ]]; then role=copied
    elif [[ $xy == *A* ]]; then role=added
    elif [[ ${xy:1:1} != ' ' ]]; then role=modified
    fi
    dots::git_style "$role"
}
# Presentation ownership is local-only and cached independently of publish policy.
declare -A PRESENTATION_REPOS=() PRESENTATION_HOSTS=()
PRESENTATION_CONFIG_READY=0
PRESENTATION_OWNERS=() PRESENTATION_ALIASES=()
repo_presentation_style() {
    local dir=${1:-} fd=${2:-1} role=repo
    dots::style "$fd"
    if [[ ( $DOTS_UI_RESET || $DOTS_UI_INFO != '[i]' ) && -n $dir ]]; then
        if [[ ! ${PRESENTATION_REPOS[$dir]+yes} ]]; then
            local REMOTE URL PROTOCOL HOST OWNER REPO OWNED HOST_ICON SAFE_URL REMOTE_ARG=''
            local -a OWNERS=() HOST_ALIASES=() RECORDS=()
            local row key value valid=1
            if ((!PRESENTATION_CONFIG_READY)); then
                PRESENTATION_CONFIG_READY=1
                if [[ ${NO_CONFIG:-0} == 0 && -f ${CONFIG:-} && ! -L $CONFIG && -r $CONFIG ]] &&
                    records_cmd git config --no-includes --null --file "$CONFIG" --list 2>/dev/null; then
                    for row in "${RECORDS[@]}"; do
                        key=${row%%$'\n'*}; value=${row#*$'\n'}
                        case $key in
                            dots-git.owner) [[ $value == */* && $value != *$'\n'* ]] || valid=0; OWNERS+=("$value") ;;
                            dots-git.hostalias) [[ $value == *=* ]] || valid=0; HOST_ALIASES+=("$value") ;;
                            *) valid=0 ;;
                        esac
                    done
                    if ((valid)); then PRESENTATION_OWNERS=("${OWNERS[@]}"); PRESENTATION_ALIASES=("${HOST_ALIASES[@]}"); fi
                fi
            fi
            OWNERS=("${PRESENTATION_OWNERS[@]}"); HOST_ALIASES=("${PRESENTATION_ALIASES[@]}")
            PRESENTATION_HOSTS[$dir]=''
            if repo_root "$dir" && [[ $REPLY == "$dir" ]] && select_remote "$dir"; then
                parse_url "$URL"
                [[ $PROTOCOL == file ]] || PRESENTATION_HOSTS[$dir]=$HOST_ICON
                [[ $OWNED != true ]] || role=repo_owned
            fi
            PRESENTATION_REPOS[$dir]=$role
        fi
        role=${PRESENTATION_REPOS[$dir]}
    fi
    dots::git_style "$role" "$fd"
}
repo_identity_label() {
    REPLY=$2
    if [[ $DOTS_UI_INFO != '[i]' ]]; then
        local icon=
        [[ ! $1 ]] || icon=${PRESENTATION_HOSTS[$1]:-}
        REPLY="$icon $2"
    fi
}
branch_identity_label() {
    REPLY=$1
    if [[ $DOTS_UI_INFO != '[i]' && -n $1 && $1 != 'detached '* ]]; then REPLY="$1"; fi
}
status_header() {
    local label=$1 branch=$2 state=$3 columns=$4 repo_style branch_style state_style marker
    local raw_label=$label raw_branch=$branch
    repo_presentation_style "${5:-}"; repo_style=$REPLY
    repo_identity_label "${5:-}" "$label"; label=$REPLY
    if [[ $branch == 'detached '* ]]; then dots::git_style detached
    else dots::git_style branch; fi
    branch_style=$REPLY
    dots::git_style "$state"; state_style=$REPLY
    case $state in clean) marker=$DOTS_UI_OK ;; blocked|conflict) marker=$DOTS_UI_ERROR ;; *) marker=$DOTS_UI_WARN ;; esac
    branch_identity_label "$branch"; display "$REPLY"; branch=$REPLY
    columns=$((10#$columns)); (( columns >= 20 )) || columns=20
    if dots::human && { (( ${#label}+${#branch}+${#state}+12 > columns )) || [[ $raw_label$raw_branch == *[!\ -~]* ]]; }; then
        printf '\n'
        dots::line "$label" "$repo_style" 2 "$columns"
        dots::line "$branch" "$branch_style" 4 "$columns"
        dots::line "$marker $state" "$state_style" 4 "$columns"
    elif (( columns < 60 )); then
        printf '\n  %s%s%s %s%s%s\n' "$state_style" "$marker" "$DOTS_UI_RESET" "$repo_style" "$label" "$DOTS_UI_RESET"
        printf '    %s%s%s  %s%s%s\n' "$branch_style" "$branch" "$DOTS_UI_RESET" "$state_style" "$state" "$DOTS_UI_RESET"
    else
        printf '\n  %s%s%s %s%s%s  %s%s%s  %s%s%s\n' "$state_style" "$marker" "$DOTS_UI_RESET" "$repo_style" "$label" "$DOTS_UI_RESET" "$branch_style" "$branch" "$DOTS_UI_RESET" "$state_style" "$state" "$DOTS_UI_RESET"
    fi
}
tracking_row() {
    local ahead=$1 behind=$2 columns=$3 ahead_style behind_style
    dots::git_style ahead; ahead_style=$REPLY
    dots::git_style behind; behind_style=$REPLY
    if [[ ! $DOTS_UI_RESET ]]; then dots::row Tracking "$ahead ahead / $behind behind (cached)"; return; fi
    columns=$((10#$columns)); (( columns >= 20 )) || columns=20
    if (( columns < 60 || ${#ahead}+${#behind}+55 > columns )); then
        dots::line Tracking "$DOTS_UI_BLUE" 2 "$columns"
        dots::line "$ahead ahead /" "$ahead_style" 6 "$columns"
        dots::line "$behind behind (cached)" "$behind_style" 6 "$columns"
    else
        printf '  %s%-26s%s %s%s ahead%s / %s%s behind%s (cached)\n' "$DOTS_UI_BLUE" Tracking "$DOTS_UI_RESET" "$ahead_style" "$ahead" "$DOTS_UI_RESET" "$behind_style" "$behind" "$DOTS_UI_RESET"
    fi
}
repo_label() {
    local dir=$1 candidate other parent collision
    if ((FULL_PATHS)); then REPLY=$dir; return; fi
    candidate=${dir##*/}
    while :; do
        collision=0
        for other in "${STATUS_DIRS[@]:-}" "${PUB_DIRS[@]:-}"; do
            if [[ $other != "$dir" && $other == */"$candidate" ]]; then collision=1; break; fi
        done
        ((collision)) || break
        # ROOT is initialized by main.bash before rendering.
        # shellcheck disable=SC2153
        if [[ $dir == "$ROOT" ]]; then candidate+=" (root)"; break; fi
        parent=${dir%/"$candidate"}
        candidate=${parent##*/}/$candidate
        [[ $parent != "$ROOT" ]] || break
    done
    REPLY=$candidate
}
render_event() {
    dots::progress_stop
    local dir=$1 state=$2 detail=$3 file=${4:-} code=$DOTS_UI_CYAN marker='[i]' label repo_style
    dots::style
    repo_presentation_style "$dir"; repo_style=$REPLY
    repo_label "$dir"; repo_identity_label "$dir" "$REPLY"; display "$REPLY"; label=$REPLY
    case $state in
        blocked|failed) dots::git_style blocked; code=$REPLY; marker=$DOTS_UI_ERROR ;;
        published|updated|clean|unchanged) dots::git_style clean; code=$REPLY; marker=$DOTS_UI_OK ;;
        modified|missing) dots::git_style "$state"; code=$REPLY; marker=$DOTS_UI_WARN ;;
        pending) dots::git_style modified; code=$REPLY; marker=$DOTS_UI_WARN ;;
        selected|planned|cancelled) code=$DOTS_UI_YELLOW; marker=$DOTS_UI_WARN ;;
        *) code=$DOTS_UI_BLUE; marker=$DOTS_UI_INFO ;;
    esac
    local columns=${COLUMNS:-80}
    [[ $columns =~ ^[0-9]+$ ]] || columns=80
    columns=$((10#$columns)); (( columns >= 20 )) || columns=20
    if dots::human && [[ $state == unchanged && ( ${#label} -gt $((columns-15)) || $label == *[!\ -~]* ) ]]; then
        dots::line "$label" "$repo_style" 2 "$columns"
        dots::line unchanged "$code" 4 "$columns"
        LAST_EVENT_REPO=''
        return
    fi
    if [[ $state == unchanged ]]; then
        printf "  %s%s%s  %sunchanged%s\n" "$repo_style" "$label" "$DOTS_UI_RESET" "$code" "$DOTS_UI_RESET"
        LAST_EVENT_REPO=''
        return
    fi
    if [[ $LAST_EVENT_REPO != "$dir" ]]; then
        if dots::human; then
            printf '\n'; dots::line "$label" "$repo_style" 2 "$columns"
        else printf '\n  %s%s%s\n' "$repo_style" "$label" "$DOTS_UI_RESET"; fi
        LAST_EVENT_REPO=$dir
    fi
    display "$state"; printf '    %s%s %s%s' "$code" "$marker" "$REPLY" "$DOTS_UI_RESET"
    if [[ -n $file ]]; then
        local actual=$dir/$file
        ((FULL_PATHS)) && file=$dir/$file
        if dots::human; then
            printf '\n'; dots::resource_row 'File' "$actual" "$file"
        else display "$file"; printf '  %s\n' "$REPLY"; fi
    elif [[ $state == unchanged ]]; then printf '\n'
    else
        printf '\n'
        if dots::human && [[ $state == planned && ${CMD:-} == publish && $detail == 'branch '* ]]; then
            local branch_value=${detail#branch } tail branch_code
            branch_value=${branch_value%%: publish to *}; tail=${detail#"branch $branch_value"}
            branch_identity_label "$branch_value"; local branch_text=$REPLY
            dots::git_style branch; branch_code=$REPLY
            dots::line Branch "$DOTS_UI_BLUE" 2 "$columns"
            dots::line "$branch_text" "$branch_code" 4 "$columns"
            # Ref is also a named branch identity, separate from the literal URL/message.
            local ref=${PREVIEW_REF[$dir]:-}
            if [[ $ref ]]; then
                tail=${tail/" → $ref"/}
                dots::line 'Target branch' "$DOTS_UI_BLUE" 2 "$columns"
                branch_identity_label "$ref"; dots::line "$REPLY" "$branch_code" 4 "$columns"
            fi
            display "${tail#: }"; dots::row Details "$REPLY"
        elif dots::human && [[ $state == planned && ${CMD:-} == sync && $detail == 'fetch and fast-forward/check out '* ]]; then
            local tracking=${detail#fetch and fast-forward/check out }
            tracking=${tracking%; remote state not checked}
            branch_identity_label "$tracking"; local tracking_text=$REPLY
            dots::git_style branch
            dots::row Details 'Fetch and fast-forward/check out'
            dots::line "$tracking_text" "$REPLY" 4 "$columns"
            dots::row Remote 'Remote state not checked'
        elif dots::human && [[ $state == pending && $detail == 'Submodule '* ]]; then
            local suffix=' differs from the parent index; record its pointer separately. Parent index was not changed by this command.'
            local child_value=${detail#Submodule } child_code
            child_value=${child_value%"$suffix"}
            repo_presentation_style "$dir/$child_value"; child_code=$REPLY
            repo_identity_label "$dir/$child_value" "$child_value"
            local child_text=$REPLY
            dots::line Submodule "$DOTS_UI_BLUE" 2 "$columns"
            dots::line "$child_text" "$child_code" 4 "$columns"
            dots::row Details "${suffix# }"
        else
            display "$detail"; dots::row 'Details' "$REPLY"
        fi
    fi
}
event() {
    dots::progress_stop
    local dir=$1 state=$2 reason=$3
    EVENT_DIRS+=("$dir"); EVENT_STATES+=("$state"); EVENT_REASONS+=("$reason")
    EVENT_FILES+=("${4:-}"); EVENT_CODES+=("${5:-}")
    [[ $state != blocked && $state != failed ]] || RESULT=1
    if ((!JSON)); then
        if [[ $state == blocked || $state == failed ]]; then
            # Cache styles in the parent; the subshell keeps grouping state isolated.
            repo_presentation_style "$dir" 2
            (render_event "$@") >&2
        else render_event "$@"; fi
    fi
}
operations_report() {
    local i comma=''
    if ((JSON)); then
        printf '{"schema":1,"command":"%s","complete":' "${OUTPUT_COMMAND:-$CMD}"
        if ((RESULT)); then printf false; else printf true; fi
        printf ',"dry_run":'; if ((DRY_RUN)); then printf true; else printf false; fi
        if ((${SCOPED_PUBLISH:-0})); then
            json_string "$ROOT"; printf ',"base":%s,"selection":[' "$REPLY"
            local scope_index scope_comma=''
            for scope_index in "${SCOPE_ROOTS[@]}"; do json_string "$scope_index"; printf '%s%s' "$scope_comma" "$REPLY"; scope_comma=,; done
            printf ']'
        fi
        printf ',"events":['
        for ((i=0;i<${#EVENT_DIRS[@]};i++)); do
            printf '%s{' "$comma"; comma=,
            json_string "${EVENT_DIRS[i]}"; printf '"path":%s,' "$REPLY"
            json_string "${EVENT_STATES[i]}"; printf '"status":%s,' "$REPLY"
            json_string "${EVENT_REASONS[i]}"; printf '"detail":%s,' "$REPLY"
            json_string "${EVENT_FILES[i]}"; printf '"file":%s,' "$REPLY"
            json_string "${EVENT_CODES[i]}"; printf '"xy":%s}' "$REPLY"
        done
        printf ']}\n'
    else
        printf '\n'
        if ((RESULT)); then dots::warning 'Incomplete; completed work is retained. Resolve blockers and rerun.'
        elif ((DRY_RUN)); then dots::info 'Preview only; no changes made.'
        else dots::success 'Complete'; fi
        ((DRY_RUN)) && dots::info 'Remote state was not fetched; undiscovered descendants remain unknown.'
    fi
    return 0
}
