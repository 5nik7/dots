#compdef pkgs
# pkgs managed completion 0.1.1
local -a values descriptions selected args types matches labels
local line name desc role curtag
local -i i width=0
args=("${(@)words[2,CURRENT]}")
# fzf-tab uses native candidates/descriptions. Do not nest a second picker.
if [[ ${PKGS_FUZZY_TAB:-1} != 0 && -t 2 ]] &&
   (( ! ${+functions[_fzf_tab]} && ! ${+functions[fzf-tab-complete]} )); then
    selected=("${(@f)$(command pkgs __complete --pick -- "${args[@]}")}")
    selected=("${(@)selected:#}")
    if (( ${#selected} )); then
        local joined="${(j: :)${(q)selected}}"
        compadd -U -Q -- "$joined"
    fi
else
    while IFS= read -r line; do
        name=${line%%$'\t'*}; line=${line#*$'\t'}
        role=${line##*$'\t'}; desc=${line%$'\t'*}
        [[ -n "$name" ]] || continue
        values+=("$name")
        descriptions+=("$desc")
        (( ${#name} <= width )) || width=${#name}
        types+=("$role")
    done < <(command pkgs __complete --display-types -- "${args[@]}")
    for (( i=1; i<=${#values}; i++ )); do
        desc=${descriptions[i]}
        if [[ -n $desc ]]; then printf -v name '%-*s -- %s' "$width" "${values[i]}" "$desc"
        else name=${values[i]}; fi
        descriptions[i]=$name
    done
    for role in command option value; do
        matches=() labels=()
        for (( i=1; i<=${#values}; i++ )); do
            [[ ${types[i]} == $role ]] || continue
            matches+=("${values[i]}"); labels+=("${descriptions[i]}")
        done
        curtag=${role}s
        (( ! ${#matches} )) || compadd -U -J "$curtag" -X "${(C)curtag}" -d labels -- "${matches[@]}"
    done
fi
