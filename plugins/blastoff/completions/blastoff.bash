# Offline positional completion. Never execute the application or read TOML.
_blastoff() {
    local LC_ALL=C root=${BLASTOFF_HOME:-$HOME/.config/blastoff}
    [[ $root == '~/'* ]] && root=$HOME/${root:2}
    local cur=${COMP_WORDS[COMP_CWORD]} word prev='' pending=0 literal=0 selection= presentation= i
    local -a positional=() candidates=() input=()
    COMPREPLY=()
    # Readline splits ':' (and '=') into separate words by default. Reassemble
    # those fragments before dispatch, then remove the already-inserted prefix.
    local trim=''
    for ((i=1; i<=COMP_CWORD; i++)); do
        word=${COMP_WORDS[i]}
        if [[ $word == : || $word == = ]]; then
            if ((${#input[@]})); then input[${#input[@]}-1]+=$word; else input+=("$word"); fi
        elif [[ $prev == : || $prev == = ]]; then
            input[${#input[@]}-1]+=$word
        else input+=("$word")
        fi
        prev=$word
    done
    if ((${#input[@]})); then
        cur=${input[${#input[@]}-1]}
        unset 'input[${#input[@]}-1]'
    fi
    if [[ $COMP_WORDBREAKS == *:* && $cur == *:* ]]; then trim=${cur%:*}:; fi
    if [[ $COMP_WORDBREAKS == *=* && $cur == --color=* ]]; then trim=--color=; fi
    if [[ $COMP_WORDBREAKS == *=* && $cur == --fancy=* ]]; then trim=--fancy=; fi
    for word in "${input[@]}"; do
        if ((pending == 1)); then pending=0; continue; fi
        if ((pending == 2)); then pending=0; [[ $word == unicode || $word == ascii ]] && continue; fi
        if ((!literal)); then
            case $word in
                --) literal=1; continue ;;
                --json|--force|--replace-link|-v|--verbose|--dry-run|-y|--yes) continue ;;
                --color) pending=1; continue ;;
                --fancy) presentation=fancy; pending=2; continue ;;
                --fancy=*) presentation=fancy; continue ;;
                --fzf) presentation=fzf; continue ;;
                --all|--pick) selection=$word; continue ;;
                --color=*) continue ;;
            esac
        fi
        if ((${#positional[@]} == 0)); then
            case $word in
                -l|--list) positional+=(list); continue ;;
                -t|--theme) positional+=(theme apply); continue ;;
            esac
        fi
        positional+=("$word")
    done
    local command=${positional[0]} action=${positional[1]} count=${#positional[@]}
    local kind='' prefix='' mode='' file base upper value
    if ((pending == 1)); then candidates=(auto always never)
    elif ((pending == 2)); then candidates=(unicode ascii)
    elif ((!literal)) && [[ $cur == --fancy=* ]]; then candidates=(--fancy=unicode --fancy=ascii)
    elif ((!literal)) && [[ $cur == --color=* ]]; then candidates=(--color=auto --color=always --color=never)
    elif ((!literal)) && [[ $cur == -* ]]; then
        candidates=(-h --help --json --color --force --replace-link -v --verbose --dry-run)
        [[ $command == pick || ( $command:$action == module:show && $count == 2 ) || ( $command:$action == backup:delete && $selection == --pick ) ]] && candidates+=(--fancy --fzf)
        [[ $command:$action == backup:delete ]] && candidates+=(--pick --all -y --yes)
        ((count)) || candidates+=(--version -l --list -t --theme)
    elif ((count == 0)); then
        candidates=(list current pick doctor theme preset module backup migrate completion)
    elif ((count == 1)); then
        case $command in
            theme) candidates=(list apply save copy import delete edit) ;;
            preset) candidates=(list apply save) ;;
            module) candidates=(list save load delete show) ;;
            backup) candidates=(create list restore delete) ;;
            pick) candidates=(fancy fzf) ;;
            completion) candidates=(bash zsh fish) ;;
            migrate) mode=directory ;;
        esac
    elif ((count == 2)); then
        case $command:$action in
            theme:apply|theme:copy)
                kind=themes
                case $cur in
                    local:*) prefix=local: ;;
                    preset:*) kind='' ;;
                    *) candidates=(local: preset:) ;;
                esac ;;
            theme:delete) kind=themes ;;
            module:load|module:delete|module:show) kind=modules ;;
            backup:restore) kind=backups ;;
            theme:import) mode=file ;;
        esac
    fi
    if [[ $command:$action == backup:delete ]] && ((count >= 2 && pending == 0)) && { ((literal)) || [[ $cur != -* ]]; }; then
        if ((!literal && count > 2)); then
            case ${positional[2]} in [aA][lL][lL]) selection=all ;; esac
        fi
        if [[ -z $selection ]]; then
            kind=backups
            if ((!literal)); then
                ((count == 2)) && candidates+=(all)
                ((count > 2)) && candidates+=(y yes)
            fi
        elif ((!literal)); then candidates=(y yes)
        fi
    fi
    if [[ $command:$action == backup:delete && $cur != -* ]] && ((!literal && count > 2 && pending == 0)); then
        case ${positional[count-1]} in [yY]|[yY][eE][sS]) kind=''; candidates=() ;; esac
    fi
    if [[ $command == pick && $action == fancy ]]; then presentation=fancy; fi
    if [[ $command == pick && $action == fzf ]]; then presentation=fzf; fi
    if [[ -n $presentation ]]; then
        local -a compatible=()
        for value in "${candidates[@]}"; do
            [[ $presentation == fancy && ( $value == --fzf || $value == fzf ) ]] && continue
            [[ $presentation == fzf && ( $value == --fancy* || $value == fancy ) ]] && continue
            compatible+=("$value")
        done
        candidates=("${compatible[@]}")
    fi
    if [[ -n $kind && -d $root && ! -L $root/$kind ]]; then
        for file in "$root/$kind/"*.toml; do
            [[ -f $file && ! -L $file ]] || continue
            base=${file##*/}; base=${base%.toml}; upper=${base^^}
            [[ ${#base} -le 96 && $base =~ ^[A-Za-z0-9][A-Za-z0-9_-]*$ ]] || continue
            case $upper in CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9]) continue ;; esac
            # Paired filenames only: backup kind/checksum remain unverified.
            if [[ $kind == backups ]]; then
                if [[ $command:$action == backup:delete ]] && ((!literal)); then
                    case $upper in ALL|Y|YES) continue ;; esac
                fi
                [[ -f $root/$kind/$base.json && ! -L $root/$kind/$base.json ]] || continue
            fi
            candidates+=("$prefix$base")
        done
    fi
    if [[ -n $mode ]]; then
        local path=$cur
        [[ $path == '~/'* ]] && path=$HOME/${path:2}
        if [[ $mode == directory ]]; then
            mapfile -t candidates < <(compgen -d -- "$path")
        else mapfile -t candidates < <(compgen -f -- "$path")
        fi
        for value in "${candidates[@]}"; do
            [[ -d $value ]] && value+=/
            COMPREPLY+=("$value")
        done
        compopt -o filenames 2>/dev/null || :
    else
        for value in "${candidates[@]}"; do
            [[ $value == "$cur"* ]] && COMPREPLY+=("${value#"$trim"}")
        done
        for value in "${COMPREPLY[@]}"; do
            [[ $value == *: ]] && { compopt -o nospace 2>/dev/null || :; break; }
        done
    fi
    return 0
}
complete -F _blastoff blastoff
