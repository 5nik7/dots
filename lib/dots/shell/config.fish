function _dots_config_valid --argument-names kind value
    switch $kind
        case bool
            contains -- "$value" 0 1
        case style
            contains -- "$value" auto always never
        case suggestions
            contains -- "$value" deja autosuggestions none
        case id
            string match -rq '^[a-z][a-z0-9_]*(-[a-z0-9_]+)*$' -- "$value"
        case '*'
            return 1
    end
end
function _dots_config_load
    set -l keys
    set -l kinds
    set -l values
    set -l origins
    set -l seen
    set -l config "$HOME/.config/dots/config.env"
    if set -q XDG_CONFIG_HOME; and test -n "$XDG_CONFIG_HOME"
        set config "$XDG_CONFIG_HOME/dots/config.env"
    end
    if set -q DOTS_CONFIG_FILE; and test -n "$DOTS_CONFIG_FILE"
        set config "$DOTS_CONFIG_FILE"
    end
    while read -l line
        set -l fields (string split \t -- "$line")
        set -a keys $fields[1]
        set -a kinds $fields[2]
        set -a values $fields[3]
        set -a origins default
    end < "$DOTS/lib/dots/shell/settings.tsv"
    if test -e "$config"
        test -f "$config"; and test -r "$config"; or return 1
        while read -l line
            set line (string trim -- "$line")
            if test -z "$line"; or string match -q '#*' -- "$line"
                continue
            end
            set -l pair (string split -m1 = -- "$line")
            test (count $pair) -eq 2; or return 1
            set -l key (string trim -- "$pair[1]")
            set -l index (contains -i -- "$key" $keys)
            test -n "$index"; and not contains -- "$key" $seen; or return 1
            set -l value (string trim -- "$pair[2]")
            set value (string replace -r '^"(.*)"$' '$1' -- "$value")
            set value (string replace -r "^'(.*)'\$" '$1' -- "$value")
            _dots_config_valid "$kinds[$index]" "$value"; or return 1
            set values[$index] "$value"
            set origins[$index] config
            set -a seen $key
        end < "$config"
    end
    for key in $keys
        set -l index (contains -i -- "$key" $keys)
        if set -q $key; and test -n "$$key"
            _dots_config_valid "$kinds[$index]" "$$key"; or return 1
            set values[$index] "$$key"
            set origins[$index] environment
        end
    end
    for key in $keys
        set -l index (contains -i -- "$key" $keys)
        set -g _dots_option_$keys[$index] "$values[$index]"
        set -g _dots_source_$keys[$index] "$origins[$index]"
    end
    set -g _DOTS_CONFIG_PATH "$config"
end
