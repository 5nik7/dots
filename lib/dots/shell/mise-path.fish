set -l inherited_path $PATH
if test -d "$shim"
    if test -n "$MISE_SHELL"; and test -n "$__MISE_ORIG_PATH"
        set -l original (string split : -- "$__MISE_ORIG_PATH")
        set -l active_path
        set -l seen 0
        set -l shim_key (string replace -r '(?<=.)/+$' '' -- "$shim")
        set -l existing_keys (string replace -r '(?<=.)/+$' '' -- $inherited_path)
        for entry in $inherited_path
            set -l key (string replace -r '(?<=.)/+$' '' -- "$entry")
            if test "$key" = "$shim_key"
                if test $seen = 0; set -a active_path "$shim"; end
                set seen 1
            else if not contains -- "$entry" $previous_profile_paths
                if test $seen = 0; and not contains -- "$shim_key" $existing_keys; and contains -- "$entry" $original; and not contains -- "$entry" $DOTBIN $DOTSCRIPTS $THEMESBIN $profile_paths
                    set -a active_path "$shim"
                    set seen 1
                end
                set -a active_path "$entry"
            end
        end
        if test $seen = 0
            set -a active_path "$shim"
        end
        set inherited_path $active_path
        set previous_profile_paths
    else
        set -a profile_paths "$shim"
    end
end
