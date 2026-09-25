# Recursive local status, with no fetch, index refresh, or file-content output.
collect_status() {
    local dir=$1 path child key value
    local -a paths=() keys=()
    local -A registered=()
    STATUS_DIRS+=("$dir")
    if [[ ! -d $dir ]] || ! repo_root "$dir" || [[ $REPLY != "$dir" ]]; then return; fi
    children "$dir" || { STATUS_ERRORS[$dir]='conflicted submodule index'; RESULT=1; return; }
    paths=("${CHILD_PATHS[@]}")
    # Read registration once per parent instead of rescanning every key per child.
    if ((${#paths[@]})); then
        records_cmd git -C "$dir" config --no-includes --null --name-only --file .gitmodules --get-regexp '^submodule\..*\.path$' 2>/dev/null || :
        keys=("${RECORDS[@]}")
        for key in "${keys[@]}"; do
            if records_cmd git -C "$dir" config --no-includes --null --file .gitmodules --get-all "$key" && ((${#RECORDS[@]} == 1)); then
                value=${RECORDS[0]}
                [[ -n $value ]] || continue
                registered[$value]=$((${registered[$value]:-0} + 1))
            fi
        done
    fi
    for path in "${paths[@]}"; do
        child=$dir/$path
        if ! safe_child_path "$dir" "$path" || [[ ${registered[$path]:-0} != 1 ]] || [[ -L $child/.git ]]; then
            STATUS_DIRS+=("$child"); STATUS_ERRORS[$child]='unsafe or unregistered submodule'; RESULT=1
        else collect_status "$child"; fi
    done
}
status_main() {
    local dir branch state row xy path old ahead behind pair comma='' filecomma index count changed=0 clean=0 branch_label marker columns=${COLUMNS:-80}
    [[ $columns =~ ^[0-9]+$ ]] || columns=80
    local -a rows=() paths=() codes=() oldpaths=()
    declare -A STATUS_ERRORS=()
    RESULT=0 STATUS_DIRS=()
    collect_status "$ROOT"
    if ((JSON)); then printf '{"schema":1,"remote_state":"cached","repositories":['
    else dots::heading 'Git status'; fi
    for dir in "${STATUS_DIRS[@]}"; do
        branch='' ahead=null behind=null state=clean paths=() codes=() oldpaths=()
        if [[ -v STATUS_ERRORS[$dir] ]]; then state=blocked
        elif ! repo_root "$dir" || [[ $REPLY != "$dir" ]]; then state=missing; RESULT=1
        else
            text_cmd git -C "$dir" symbolic-ref --quiet --short HEAD 2>/dev/null && branch=$REPLY
            if [[ -z $branch ]]; then
                text_cmd git -C "$dir" rev-parse --short HEAD 2>/dev/null && branch="detached $REPLY"
            fi
            if ! records_cmd git -C "$dir" status --porcelain=v1 -z --untracked-files=all --ignore-submodules=none; then
                state=blocked; RESULT=1
            else
                rows=("${RECORDS[@]}")
                for ((index=0;index<${#rows[@]};index++)); do
                    row=${rows[index]}; xy=${row:0:2}; path=${row:3}; old=''
                    if [[ $xy == *R* || $xy == *C* ]]; then ((index+=1)); old=${rows[index]}; fi
                    paths+=("$path"); codes+=("$xy"); oldpaths+=("$old")
                    if [[ $xy == *U* || $xy == AA || $xy == DD ]]; then state=conflict; fi
                done
                if ((${#paths[@]})) && [[ $state != conflict ]]; then state=modified; fi
            fi
            if upstream "$dir" && text_cmd git -C "$dir" rev-list --left-right --count "HEAD...$TRACKING" 2>/dev/null; then
                read -r ahead behind <<< "$REPLY"
            fi
        fi
        count=${#paths[@]}
        if [[ $state == clean ]]; then ((clean+=1)); else ((changed+=1)); fi
        if ((JSON)); then
            printf '%s{' "$comma"; comma=,
            json_string "$dir"; printf '"path":%s,' "$REPLY"
            json_string "$branch"; printf '"branch":%s,' "$REPLY"
            json_string "$state"; printf '"status":%s,"ahead":%s,"behind":%s,"files":[' "$REPLY" "$ahead" "$behind"
            filecomma=''
            for ((index=0;index<count;index++)); do
                printf '%s{' "$filecomma"; filecomma=,
                json_string "${paths[index]}"; printf '"path":%s,' "$REPLY"
                json_string "${codes[index]}"; printf '"xy":%s,' "$REPLY"
                json_string "${oldpaths[index]}"; printf '"old_path":%s}' "$REPLY"
            done
            printf ']}'
        else
            repo_label "$dir"; display "$REPLY"; branch_label=$REPLY
            dots::style
            case $state in clean) pair=$DOTS_UI_GREEN; marker=$DOTS_UI_OK ;; blocked|conflict) pair=$DOTS_UI_RED; marker=$DOTS_UI_ERROR ;; *) pair=$DOTS_UI_YELLOW; marker=$DOTS_UI_WARN ;; esac
            display "$branch"
            if ((10#$columns < 60)); then
                printf '\n  %s%s%s %s%s%s\n' "$pair" "$marker" "$DOTS_UI_RESET" "$DOTS_UI_BOLD$DOTS_UI_BLUE" "$branch_label" "$DOTS_UI_RESET"
                printf '    %s  %s%s%s\n' "$REPLY" "$pair" "$state" "$DOTS_UI_RESET"
            else
                printf '\n  %s%s%s %s%s%s  %s  %s%s%s\n' "$pair" "$marker" "$DOTS_UI_RESET" "$DOTS_UI_BOLD$DOTS_UI_BLUE" "$branch_label" "$DOTS_UI_RESET" "$REPLY" "$pair" "$state" "$DOTS_UI_RESET"
            fi
            [[ $ahead == null ]] || dots::row 'Tracking' "$ahead ahead / $behind behind (cached)"
            [[ ! -v STATUS_ERRORS[$dir] ]] || dots::row 'Reason' "${STATUS_ERRORS[$dir]}"
            for ((index=0;index<count;index++)); do
                xy=${codes[index]}; path=${paths[index]}; pair=''
                if [[ $xy == '??' ]]; then pair=untracked
                elif [[ $xy == *U* || $xy == AA || $xy == DD ]]; then pair=conflict
                else
                    [[ ${xy:0:1} == ' ' ]] || pair=staged
                    [[ ${xy:1:1} == ' ' ]] || pair+=${pair:+' + '}modified
                    [[ $xy != *D* ]] || pair+=' deleted'
                    [[ $xy != *R* ]] || pair+=' renamed'
                fi
                ((FULL_PATHS)) && path=$dir/$path
                if [[ -n ${oldpaths[index]} ]]; then
                    old=${oldpaths[index]}; ((FULL_PATHS)) && old=$dir/$old
                    path="$old -> $path"
                fi
                display "$path"; dots::row "$pair" "$REPLY"
            done
        fi
    done
    if ((JSON)); then printf '],"complete":'; if ((RESULT)); then printf false; else printf true; fi; printf '}\n'
    else
        printf '\n'; dots::info "${#STATUS_DIRS[@]} repositories / $changed changed or unavailable / $clean clean"
        dots::info 'Remote state uses local tracking refs; no fetch performed.'
    fi
    return "$RESULT"
}
