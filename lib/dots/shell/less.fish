# Native, builtin-only adapter; shared contract: less_style.py.
function _dots_less_style --argument-names fg bg mode enabled
    set -l reset (printf '\033[0m')
    set -l owned 0
    if set -q _DOTS_LESS_STYLE; and test -n "$_DOTS_LESS_STYLE"; and test "$LESS_TERMCAP_so" = "$_DOTS_LESS_STYLE"; and test "$LESS_TERMCAP_se" = "$reset"
        set owned 1
    end
    if begin; set -q LESS_TERMCAP_so; or set -q LESS_TERMCAP_se; end; and test $owned = 0
        set -e _DOTS_LESS_STYLE
        return 0
    end
    if set -q LESS_TERMINFO_smso; or set -q LESS_TERMINFO_rmso
        if test $owned = 1
            set -e LESS_TERMCAP_so
            set -e LESS_TERMCAP_se
        end
        set -e _DOTS_LESS_STYLE
        return 0
    end
    if test "$enabled" != 1; or begin; test "$mode" != always; and begin; test "$mode" != auto; or test "$TERM" = dumb; or test -z "$TERM"; or test -n "$NO_COLOR"; end; end
        if test $owned = 1
            set -e LESS_TERMCAP_so
            set -e LESS_TERMCAP_se
        end
        set -e _DOTS_LESS_STYLE
        return 0
    end
    string match -rq '^#[a-fA-F0-9]{6}$' -- "$fg"; and string match -rq '^#[a-fA-F0-9]{6}$' -- "$bg"; or return 0
    set -l rgb
    for value in "$fg" "$bg"
        for position in 2 4 6
            set -a rgb "0x"(string sub -s $position -l 2 -- "$value")
        end
    end
    set -gx LESS_TERMCAP_so (printf '\033[0;38;2;%d;%d;%d;48;2;%d;%d;%dm' $rgb)
    set -gx LESS_TERMCAP_se "$reset"
    set -gx _DOTS_LESS_STYLE "$LESS_TERMCAP_so"
end
