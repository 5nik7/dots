# shellcheck shell=bash disable=SC2034
# Presentation-only projections. JSON/events and Git operation order stay owned
# by their existing controllers. No subprocess is started for a file row.
view_select() {
    [[ $1 == default || $1 == short || $1 == verbose ]] || die 2 'view requires default, short or verbose'
    [[ ! ${GIT_VIEW_EXPLICIT:-} || $GIT_VIEW_EXPLICIT == "$1" ]] || die 2 'conflicting Git views; select default, short or verbose'
    GIT_VIEW_EXPLICIT=$1
}
view_resolve() {
    GIT_VIEW=''
    (( ! JSON )) || return 0
    if [[ -t 1 ]] && command -v stty >/dev/null 2>&1; then
        local terminal_rows terminal_columns
        # Preserve stdout's terminal before process substitution redirects it.
        { read -r terminal_rows terminal_columns < <(stty size <&3 2>/dev/null) || :; } 3<&1
        [[ $terminal_columns =~ ^[1-9][0-9]*$ ]] && COLUMNS=$terminal_columns
    fi
    if [[ ${GIT_VIEW_EXPLICIT:-} ]]; then GIT_VIEW=$GIT_VIEW_EXPLICIT
    elif [[ -t 1 || ${DOTS_MENU_CAPTURE:-} == 1 ]]; then GIT_VIEW=${_DOTS_GIT_VIEW:-default}; fi
}
view_file_label() {
    local xy=$1 marker state where index
    REPLY=''
    if [[ $GIT_VIEW == short ]]; then REPLY=$xy; return; fi
    case $xy in
        '??') REPLY=untracked; return ;; '!!') REPLY=ignored; return ;;
        DD) REPLY='conflict: both deleted'; return ;; AA) REPLY='conflict: both added'; return ;;
        UU) REPLY='conflict: both modified'; return ;; AU) REPLY='conflict: added by us'; return ;;
        UA) REPLY='conflict: added by them'; return ;; UD) REPLY='conflict: deleted by them'; return ;;
        DU) REPLY='conflict: deleted by us'; return ;;
    esac
    for index in 0 1; do
        marker=${xy:index:1}; [[ $marker && $marker != ' ' ]] || continue
        if ((index)); then where=unstaged; else where=staged; fi
        case $marker in M) state=modified ;; A) state=added ;; D) state=deleted ;; R) state=renamed ;;
            C) state=copied ;; T) state='type changed' ;; U) state=unmerged ;; *) state=$marker ;; esac
        REPLY+=${REPLY:+' + '}$where' '$state
    done
    REPLY=${REPLY:-selected}
    [[ $GIT_VIEW != verbose ]] || REPLY="$xy $REPLY"
}
view_file() {
    local dir=$1 xy=$2 path=$3 old=${4:-} label display actual=$1/$3 code old_actual=''
    local changed=${5:-0}
    view_file_label "$xy"; label=$REPLY
    if [[ $changed == 1 && $GIT_VIEW != short ]]; then
        case ${xy:0:1} in M) label=modified ;; A) label=added ;; D) label=deleted ;; R) label=renamed ;; C) label=copied ;; T) label='type changed' ;; esac
    fi
    display=$path; (( ! FULL_PATHS )) || display=$actual
    if [[ $old ]]; then
        old_actual=$dir/$old
        (( ! FULL_PATHS )) || old=$dir/$old
    fi
    file_status_style "$xy"; code=$REPLY
    if [[ $changed == 1 && ( ${xy:0:1} == M || ${xy:0:1} == T ) ]]; then dots::git_style modified; code=$REPLY; fi
    if [[ $GIT_VIEW == short ]]; then
        dots::settings
        local old_width=${_DOTS_FORMATTING[label_width]-} old_gap=${_DOTS_FORMATTING[label_gap]-}
        _DOTS_FORMATTING[label_width]=2; _DOTS_FORMATTING[label_gap]=2
        dots::resource_row "$label" "$actual" "$display" '' '' "$code" paths "$old_actual" "$old"
        if [[ $old_width ]]; then _DOTS_FORMATTING[label_width]=$old_width; else unset '_DOTS_FORMATTING[label_width]'; fi
        if [[ $old_gap ]]; then _DOTS_FORMATTING[label_gap]=$old_gap; else unset '_DOTS_FORMATTING[label_gap]'; fi
    else dots::resource_row "$label" "$actual" "$display" '' '' "$code" paths "$old_actual" "$old"; fi
}
# Small repository headers retain semantic colors across wrapped spans. File rows
# continue to use the shared resource renderer; no formatting subprocess per row.
view_spans() {
    local columns=${COLUMNS:-80} used=2 text code char size i active=''
    [[ $columns =~ ^[0-9]+$ ]] || columns=80
    columns=$((10#$columns)); ((columns >= 20)) || columns=20
    printf '  '
    while (($#)); do
        text=$1 code=$2; shift 2
        dots::text "$text"; text=$REPLY
        for ((i=0;i<${#text};i++)); do
            char=${text:i:1}; size=1; [[ $char == [\ -~] ]] || size=2
            if ((used+size > columns)); then
                printf '%s\n  ' "$DOTS_UI_RESET"; used=2; active=''
            fi
            if [[ $code != "$active" ]]; then printf '%s%s' "$DOTS_UI_RESET" "$code"; active=$code; fi
            printf '%s' "$char"; ((used+=size))
        done
    done
    printf '%s\n' "$DOTS_UI_RESET"
}
view_status_header() {
    local dir=$1 branch=$2 state=$3 ahead=$4 behind=$5 label
    local repo_code branch_code state_code ahead_code behind_code
    repo_label "$dir"; display "$REPLY"; label=$REPLY
    repo_presentation_style "$dir"; repo_code=$REPLY
    repo_identity_label "$dir" "$label"; label=$REPLY
    if [[ ! $branch && ( $state == missing || $state == blocked ) ]]; then branch=unavailable; fi
    branch=${branch:-unborn}
    if [[ $branch == 'detached '* ]]; then dots::git_style detached; else dots::git_style branch; fi
    branch_code=$REPLY; branch_identity_label "$branch"; display "$REPLY"; branch=$REPLY
    dots::git_style "$state"; state_code=$REPLY
    dots::git_style ahead; ahead_code=$REPLY
    dots::git_style behind; behind_code=$REPLY
    if [[ $ahead == null ]]; then
        view_spans "$label" "$repo_code" "  $branch" "$branch_code" "  $state" "$state_code" '  tracking unknown (cached)' "$DOTS_UI_DIM"
    else
        view_spans "$label" "$repo_code" "  $branch" "$branch_code" "  $state" "$state_code" "  $ahead ahead" "$ahead_code" " / $behind behind (cached)" "$behind_code"
    fi
}
view_metadata() {
    local dir=$1 REMOTE URL PROTOCOL HOST OWNER REPO OWNED HOST_ICON SAFE_URL REMOTE_ARG=''
    local BRANCH UP_REMOTE UP_REF TRACKING
    presentation_config
    local -a OWNERS=("${PRESENTATION_OWNERS[@]}") HOST_ALIASES=("${PRESENTATION_ALIASES[@]}")
    dots::resource_row Path "$dir" "$dir" dir
    if text_cmd git -C "$dir" rev-parse --verify HEAD 2>/dev/null; then dots::row HEAD "$REPLY"; else dots::row HEAD unborn; fi
    if upstream "$dir"; then dots::row Upstream "$TRACKING"; else dots::row Upstream unavailable; fi
    if select_remote "$dir"; then
        parse_url "$URL"
        dots::row Remote "$REMOTE"; dots::row URL "$SAFE_URL"; dots::row Owner "${OWNER:-unavailable}"
        if ((${#OWNERS[@]})); then dots::row Owned "$OWNED"; else dots::row Owned unavailable; fi
    fi
}
declare -A VIEW_FILES=() VIEW_PREVIEWS=() VIEW_RENAMES=()
VIEW_LAST_REPO=''
view_event() {
    local dir=$1 state=$2 detail=$3 file=${4:-} xy=${5:-} key label role code
    key=$dir/$file
    if [[ $file && ${VIEW_FILES[$key]:-} && $state != blocked && $state != failed && $state != pending ]]; then
        [[ $GIT_VIEW != verbose ]] || dots::row "$state" "$detail"
        return 0
    fi
    [[ ! $file ]] || VIEW_FILES[$key]=1
    if [[ $state == unchanged && ${VIEW_PREVIEWS[$dir]:-} && $GIT_VIEW != verbose ]]; then return 0; fi
    [[ $state != planned && $state != unchanged ]] || VIEW_PREVIEWS[$dir]=1
    repo_label "$dir"; repo_presentation_style "$dir"; code=$REPLY
    repo_label "$dir"; repo_identity_label "$dir" "$REPLY"; display "$REPLY"; label=$REPLY
    if [[ $file ]]; then
        [[ $VIEW_LAST_REPO == "$dir" ]] || dots::line "$label" "$code" 2 "${COLUMNS:-80}"
        view_file "$dir" "$xy" "$file" "${VIEW_RENAMES[$key]:-}"
        case $state in blocked|failed|pending) dots::row Details "$detail" ;; esac
    else
        case $state in blocked|failed) role=blocked ;; published|updated|unchanged) role=clean ;; *) role=modified ;; esac
        dots::git_style "$role"; view_spans "$label" "$code" "  $state" "$REPLY"
        if [[ $GIT_VIEW == verbose || $state == planned || $state == blocked || $state == failed || $state == pending || $state == cancelled || $state == skipped ]]; then dots::row Details "$detail"; fi
        if [[ $GIT_VIEW == verbose && $state == planned ]] && repo_root "$dir" && [[ $REPLY == "$dir" ]]; then view_metadata "$dir"; fi
    fi
    VIEW_LAST_REPO=$dir
}

# A post-update report from actual commits, never an operation event or preview.
view_changes() {
    [[ ${GIT_VIEW:-} ]] || return 0
    local dir=$1 before=$2 after status old new i
    text_cmd git -C "$dir" rev-parse HEAD || { dots::row Files 'Change list unavailable; inspect the repository history.'; return 0; }; after=$REPLY
    [[ $before != "$after" ]] || return 0
    records_cmd git -C "$dir" diff --no-ext-diff --no-textconv --name-status -z --find-renames "$before" "$after" -- || { dots::row Files 'Change list unavailable; inspect the repository history.'; return 0; }
    local -a changes=("${RECORDS[@]}")
    dots::progress_stop
    for ((i=0;i<${#changes[@]};i++)); do
        status=${changes[i]}; ((i+=1)); old=${changes[i]}; new=$old
        if [[ $status == R* || $status == C* ]]; then ((i+=1)); new=${changes[i]}; else old=''; fi
        view_file "$dir" "${status:0:1} " "$new" "$old" 1
    done
}

# Verbose phase evidence remains available even with transient progress off.
view_phase() {
    dots::progress_stop
    if [[ ${GIT_VIEW:-} == verbose ]]; then dots::row Phase "$1" >&2
    else dots::progress_external "$1"; fi
}
