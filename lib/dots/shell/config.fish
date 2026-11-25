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
    set -l seen
    set -l config "$HOME/.config/dots/config.env"
    if set -q XDG_CONFIG_HOME; and test -n "$XDG_CONFIG_HOME"
        set config "$XDG_CONFIG_HOME/dots/config.env"
    end
    if set -q DOTS_CONFIG_FILE; and test -n "$DOTS_CONFIG_FILE"
        set config "$DOTS_CONFIG_FILE"
    end
    while read -ld \t key kind value description
        set -a keys $key
        set -f kind_$key "$kind"
        set -f value_$key "$value"
        set -f source_$key default
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
            contains -- "$key" $keys; and not contains -- "$key" $seen; or return 1
            set -l kind kind_$key
            set -l value (string trim -- "$pair[2]")
            set value (string replace -r '^"(.*)"$' '$1' -- "$value")
            set value (string replace -r "^'(.*)'\$" '$1' -- "$value")
            _dots_config_valid "$$kind" "$value"; or return 1
            set -f value_$key "$value"
            set -f source_$key config
            set -a seen $key
        end < "$config"
    end
    if not set -q DOTS_CONFIG_FILE; or test -z "$DOTS_CONFIG_FILE"
        for key in $_dots_profile_setting_keys
            contains -- "$key" $keys; or return 1
            set -l kind kind_$key
            set -l name _dots_profile_setting_$key
            set -l origin _dots_profile_source_$key
            _dots_config_valid "$$kind" "$$name"; or return 1
            set -f value_$key "$$name"
            set -f source_$key "$$origin"
        end
    end
    for key in $keys
        if set -q $key; and test -n "$$key"
            set -l kind kind_$key
            _dots_config_valid "$$kind" "$$key"; or return 1
            set -f value_$key "$$key"
            set -f source_$key environment
        end
    end
    for key in $keys
        set -l value value_$key
        set -l source_name source_$key
        set -g _dots_option_$key "$$value"
        set -g _dots_source_$key "$$source_name"
    end
    set -g _DOTS_CONFIG_PATH "$config"
    if not set -q DOTS_CONFIG_FILE; or test -z "$DOTS_CONFIG_FILE"
        if test -n "$_dots_profile_config_path"
            set -g _DOTS_CONFIG_PATH "$_dots_profile_config_path"
        end
    end
end
