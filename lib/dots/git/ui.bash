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
        if [[ $dir == "$ROOT" ]]; then candidate+=" (root)"; break; fi
        parent=${dir%/"$candidate"}
        candidate=${parent##*/}/$candidate
        [[ $parent != "$ROOT" ]] || break
    done
    REPLY=$candidate
}
render_event() {
    local dir=$1 state=$2 detail=$3 file=${4:-} code=$DOTS_UI_CYAN marker='[i]' label
    dots::style
    repo_label "$dir"; display "$REPLY"; label=$REPLY
    case $state in
        blocked|failed) code=$DOTS_UI_RED; marker=$DOTS_UI_ERROR ;;
        published|updated|clean|unchanged) code=$DOTS_UI_GREEN; marker=$DOTS_UI_OK ;;
        modified|selected|planned|missing|cancelled) code=$DOTS_UI_YELLOW; marker=$DOTS_UI_WARN ;;
        *) code=$DOTS_UI_BLUE; marker=$DOTS_UI_INFO ;;
    esac
    if [[ $state == unchanged ]]; then
        printf "  %s%s%s  %sunchanged%s\n" "$DOTS_UI_BOLD$DOTS_UI_BLUE" "$label" "$DOTS_UI_RESET" "$DOTS_UI_GREEN" "$DOTS_UI_RESET"
        LAST_EVENT_REPO=''
        return
    fi
    if [[ $LAST_EVENT_REPO != "$dir" ]]; then
        printf '\n  %s%s%s\n' "$DOTS_UI_BOLD$DOTS_UI_BLUE" "$label" "$DOTS_UI_RESET"
        LAST_EVENT_REPO=$dir
    fi
    display "$state"; printf '    %s%s %s%s' "$code" "$marker" "$REPLY" "$DOTS_UI_RESET"
    if [[ -n $file ]]; then
        ((FULL_PATHS)) && file=$dir/$file
        display "$file"; printf '  %s\n' "$REPLY"
    elif [[ $state == unchanged ]]; then printf '\n'
    else
        printf '\n'
        display "$detail"; dots::row 'Details' "$REPLY"
    fi
}
event() {
    local dir=$1 state=$2 reason=$3
    EVENT_DIRS+=("$dir"); EVENT_STATES+=("$state"); EVENT_REASONS+=("$reason")
    EVENT_FILES+=("${4:-}"); EVENT_CODES+=("${5:-}")
    [[ $state != blocked && $state != failed ]] || RESULT=1
    if ((!JSON)); then
        if [[ $state == blocked || $state == failed ]]; then
            (render_event "$@") >&2
        else render_event "$@"; fi
    fi
}
operations_report() {
    local i comma=''
    if ((JSON)); then
        printf '{"schema":1,"command":"%s","complete":' "$CMD"
        if ((RESULT)); then printf false; else printf true; fi
        printf ',"dry_run":'; if ((DRY_RUN)); then printf true; else printf false; fi
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
