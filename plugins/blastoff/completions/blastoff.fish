# One positional dispatcher; -f disables Fish's implicit filename fallback.
# Only shell builtins and local filenames; never read TOML or run Blastoff.
function __blastoff_candidates
    set -l root $HOME/.config/blastoff
    if set -q BLASTOFF_HOME; and test -n "$BLASTOFF_HOME"
        set root $BLASTOFF_HOME
    end
    if string match -q '~/*' -- "$root"
        set root "$HOME/"(string sub -s 3 -- "$root")
    end
    set -l words (commandline -opc)
    set -e words[1]
    set -l cur (commandline -ct | string unescape)
    test (count $cur) -gt 0; or set cur ''
    set -l positional
    set -l pending 0
    set -l literal 0
    set -l selection ""
    set -l presentation ""
    for word in $words
        if test $pending = 1
            set pending 0
            continue
        end
        if test $pending = 2
            set pending 0
            if contains -- "$word" unicode ascii
                continue
            end
        end
        if test $literal = 0
            switch $word
                case --
                    set literal 1
                    continue
                case --json --force --replace-link -v --verbose --dry-run -y --yes
                    continue
                case --color
                    set pending 1
                    continue
                case --fzf
                    set presentation fzf
                    continue
                case --fancy
                    set presentation fancy
                    set pending 2
                    continue
                case '--fancy=*'
                    set presentation fancy
                    continue
                case --all --pick
                    set selection $word
                    continue
                case '--color=*'
                    continue
            end
        end
        if test (count $positional) = 0
            switch $word
                case -l --list
                    set -a positional list
                    continue
                case -t --theme
                    set -a positional theme apply
                    continue
            end
        end
        set -a positional "$word"
    end
    set -l candidates
    set -l kind ''
    set -l prefix ''
    set -l mode ''
    set -l n (count $positional)
    if test $pending = 1
        set candidates auto always never
    else if test $pending = 2
        set candidates unicode ascii
    else if test $literal = 0; and string match -q -- '--fancy=*' "$cur"
        set candidates --fancy=unicode --fancy=ascii
    else if test $literal = 0; and string match -q -- '--color=*' "$cur"
        set candidates --color=auto --color=always --color=never
    else if test $literal = 0; and string match -q -- '-*' "$cur"
        set candidates -h --help --json --color --force --replace-link -v --verbose --dry-run
        if test "$positional[1]" = pick; or test "$positional[1]:$positional[2]" = module:show -a $n = 2; or test "$positional[1]:$positional[2]" = backup:delete -a "$selection" = --pick
            set -a candidates --fancy --fzf
        end
        if test "$positional[1]:$positional[2]" = backup:delete
            set -a candidates --pick --all -y --yes
        end
        if test $n = 0
            set -a candidates --version -l --list -t --theme
        end
    else if test $n = 0
        set candidates list current pick doctor theme preset module backup migrate completion
    else if test $n = 1
        switch $positional[1]
            case theme
                set candidates list apply save copy import delete edit
            case preset
                set candidates list apply save
            case module
                set candidates list save load delete show
            case backup
                set candidates create list restore delete
            case pick
                set candidates fancy fzf
            case completion
                set candidates bash zsh fish
            case migrate
                set mode directory
        end
    else if test $n = 2
        switch "$positional[1]:$positional[2]"
            case theme:apply theme:copy
                set kind themes
                switch $cur
                    case 'local:*'
                        set prefix local:
                    case 'preset:*'
                        set kind ''
                    case '*'
                        set candidates local: preset:
                end
            case theme:delete
                set kind themes
            case module:load module:delete module:show
                set kind modules
            case backup:restore
                set kind backups
            case theme:import
                set mode file
        end
    end
    if test "$positional[1]:$positional[2]" = backup:delete; and test $n -ge 2; and test $pending = 0
        if test $literal = 1; or not string match -q -- '-*' "$cur"
            if test $literal = 0; and test $n -gt 2
                if string match -riq '^all$' -- "$positional[3]"
                    set selection all
                end
            end
            if test -z "$selection"
                set kind backups
                if test $literal = 0
                    if test $n = 2
                        set -a candidates all
                    else
                        set -a candidates y yes
                    end
                end
            else if test $literal = 0
                set candidates y yes
            end
        end
    end
    if test "$positional[1]:$positional[2]" = backup:delete; and test $literal = 0; and test $n -gt 2; and test $pending = 0
        if not string match -q -- '-*' "$cur"; and string match -riq '^(y|yes)$' -- "$positional[-1]"
            set kind ""
            set candidates
        end
    end
    if test -n "$kind"; and test -d "$root"; and not test -L "$root/$kind"
        for file in "$root/$kind/"*.toml
            test -f "$file"; and not test -L "$file"; or continue
            set -l base (string replace -r '^.*/([^/]+)\.toml$' '$1' -- "$file")
            string match -rq '^[A-Za-z0-9][A-Za-z0-9_-]{0,95}$' -- "$base"; or continue
            string match -riq '^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])$' -- "$base"; and continue
            # Filename pairs only, not verified config-kind backup metadata.
            if test "$kind" = backups
                if test "$positional[1]:$positional[2]" = backup:delete; and test $literal = 0
                    string match -riq '^(all|y|yes)$' -- "$base"; and continue
                end
                test -f "$root/$kind/$base.json"; and not test -L "$root/$kind/$base.json"; or continue
            end
            set -a candidates "$prefix$base"
        end
    end
    if test -n "$mode"
        set -l path "$cur"
        if string match -q '~/*' -- "$path"
            set path "$HOME/"(string sub -s 3 -- "$path")
        end
        for file in "$path"*
            if test -d "$file"
                set -a candidates "$file/"
            else if test "$mode" = file; and test -e "$file"
                set -a candidates "$file"
            end
        end
    end
    if test "$positional[1]" = pick; and contains -- "$positional[2]" fancy fzf
        set presentation $positional[2]
    end
    for value in $candidates
        if test "$presentation" = fancy; and contains -- "$value" --fzf fzf
            continue
        end
        if test "$presentation" = fzf; and string match -rq '^(--fancy($|=)|fancy$)' -- "$value"
            continue
        end
        # Fish performs prefix matching and shell quoting on these raw lines.
        printf '%s\n' "$value"
    end
end
complete -c blastoff -f -a '(__blastoff_candidates)'
