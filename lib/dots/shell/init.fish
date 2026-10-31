for name in DOTRUBY RUBYCOMP _dots_applied_DOTRUBY _dots_applied_RUBYCOMP
    set -e $name
end
set -l _dots_retired_paths "$DOTS/ruby/completion" "$HOME/dots/ruby/completion"
if set -q DOTS_PROFILE_CHECKOUT; and test -n "$DOTS_PROFILE_CHECKOUT"
    set -a _dots_retired_paths "$DOTS_PROFILE_CHECKOUT/ruby/completion"
end
set -l _dots_retained_path
for entry in $PATH
    set -l normalized (string replace -r '/+$' '' -- "$entry")
    contains -- "$normalized" $_dots_retired_paths; or set -a _dots_retained_path "$entry"
end
set -gx PATH $_dots_retained_path
for name in DOTS_ENV_HOOKS DOTS_ENV_ORIGINS
    if set -q $name
        set -l retained
        for record in (string split ';' -- $$name)
            if test -n "$record"; and not string match -rq '^(DOTRUBY|RUBYCOMP)[:|]' -- "$record"
                set -a retained "$record"
            end
        end
        set -gx $name (string join ';' -- $retained)
    end
end
set -l _dots_cache_root "$HOME/.cache"
set -q XDG_CACHE_HOME; and set _dots_cache_root "$XDG_CACHE_HOME"
set -l _dots_environment_cache "$_dots_cache_root/dots/startup/environment.fish"
set -l _dots_environment_ready 0
if test -f "$_dots_environment_cache"
    source "$_dots_environment_cache"; and set _dots_environment_ready 1
end
if test $_dots_environment_ready = 0; and command -q python3
    if command python3 -B "$DOTS/lib/dots/native_startup.py" fish "$_dots_environment_cache"
        source "$_dots_environment_cache"; and set _dots_environment_ready 1
    end
end
if test $_dots_environment_ready = 0
    if set -q _dots_generated_names
        printf 'dots: profile environment preparation failed; previous profile environment retained\n' >&2
        return 1
    end
    printf 'dots: profile environment preparation unavailable; retaining minimal integration\n' >&2
end
source "$DOTS/lib/dots/shell/config.fish"
_dots_config_load; or begin
    printf 'dots: invalid settings; initialization stopped\n' >&2
    return 1
end
while read -l line
    set -l fields (string split \t -- "$line")
    set -l value "$DOTS"
    test "$fields[3]" = .; or set value "$DOTS/$fields[3]"
    test "$fields[1]" = -; or set -gx $fields[1] "$value"
    test "$fields[2]" = -; or set -g dot_$fields[2] "$value"
end < "$DOTS/lib/dots/shell/paths.tsv"
set -gx THEMESCMD "$DOTS/bin/theme"
set -l state "$HOME/.local/state"
if set -q XDG_STATE_HOME; and test -n "$XDG_STATE_HOME"
    set state "$XDG_STATE_HOME"
end
set -g _DOTS_STATE "$state/dots"
set -gx THEMESBIN "$_DOTS_STATE/themes/commands/current/bin"
set -g dot_state "$_DOTS_STATE"
set -g dot_config "$_DOTS_CONFIG_PATH"
set -l clean_path
for directory in $PATH
    contains -- "$directory" "$DOTS/themes/bin" "$THEMESBIN"; or set -a clean_path "$directory"
end
set -gx PATH $clean_path
for directory in "$DOTBIN" "$DOTSCRIPTS"
    if test -d "$directory"; and not contains -- "$directory" $PATH
        set -gx PATH "$directory" $PATH
    end
end
if test $_dots_option_DOTS_INIT_COMMANDS = 1
    set -gx PATH $PATH "$THEMESBIN"
end
set -l profile_entries (string split : -- "$DOTS_PROFILE_PATHS" | string match -rv '^$')
set -l ordered_path
for entry in $profile_entries $PATH
    contains -- "$entry" $ordered_path; or set -a ordered_path "$entry"
end
set -gx PATH $ordered_path
status is-interactive; or return 0
source "$DOTS/lib/dots/shell/less.fish"
set -g esc (printf '\033')
set -g ESC "$esc"
set -g rst (printf '\033[0m')
set -g RST "$rst"
if test $_dots_option_DOTS_INIT_COLORS = 0
    for name in $_DOTS_COLOR_SHORTCUTS
        set -e $name
    end
    set -g _DOTS_COLOR_SHORTCUTS
end
function _dots_fish_theme
    if test $_dots_option_DOTS_INIT_THEME != 1
        _dots_less_style '' '' auto 0
        return 0
    end
    set -l generation
    test -r "$_DOTS_STATE/themes/current"; or return 0
    read -l generation < "$_DOTS_STATE/themes/current"
    string match -rq '^g\.[a-zA-Z0-9]+$' -- "$generation"; or return 1
    test "$generation" != "$_DOTS_THEME_GENERATION"; or return 0
    set -l file "$_DOTS_STATE/themes/generations/$generation/shell.tsv"
    test -f "$file"; and test -r "$file"; or return 1
    set -l records
    set -l id
    set -l less_fg ''
    set -l less_bg ''
    set -l less_lighter ''
    while read -l line
        set -l fields (string split \t -- "$line")
        test (count $fields) -eq 3; or return 1
        string match -rq '^(@theme|@palette|@role|[a-z_][a-zA-Z0-9_]*)$' -- "$fields[1]"; or return 1
        string match -rq '^[a-zA-Z0-9_-]+$' -- "$fields[2]"; or return 1
        set -a records "$line"
        if test "$fields[2]" = hex
            switch "$fields[1]"
                case foreground
                    set less_fg "$fields[3]"
                case background
                    set less_bg "$fields[3]"
                case lighter_background
                    set less_lighter "$fields[3]"
            end
        end
        if test "$fields[1]" = @theme; and test "$fields[2]" = id
            set id "$fields[3]"
        end
    end < "$file"
    test -n "$id"; or return 1
    test -n "$less_lighter"; or set less_lighter "$less_bg"
    _dots_less_style "$less_fg" "$less_lighter" "$_dots_option_DOTS_COLOR" 1
    for name in $_DOTS_COLOR_VARIABLES
        set -e $name
    end
    set -g _DOTS_COLOR_VARIABLES
    set -g _DOTS_COLOR_SHORTCUTS
    for record in $records
        set -l fields (string split \t -- "$record")
        set -l name
        switch $fields[1]
            case @theme
                switch $fields[2]
                    case id
                        set -gx DOTS_THEME_ID "$fields[3]"
                        set -g dot_theme "$fields[3]"
                    case family
                        set -gx THEME "$fields[3]"
                    case flavor
                        set -gx FLAVOR "$fields[3]"
                end
            case @palette
                set name dots_color_$fields[2]
            case @role
                set name dots_role_$fields[2]
            case '*'
                if test $_dots_option_DOTS_INIT_COLORS = 1
                    set name dots_color_$fields[1]_(string replace -a - _ -- "$fields[2]")
                    set -ga _DOTS_COLOR_SHORTCUTS $name
                end
        end
        if test -n "$name"
            set -g $name "$fields[3]"
            set -ga _DOTS_COLOR_VARIABLES $name
        end
    end
    if test -r "$_DOTS_STATE/themes/generations/$generation/ls_colors"
        read -gx LS_COLORS < "$_DOTS_STATE/themes/generations/$generation/ls_colors"
    end
    set -l visual_file "$_DOTS_STATE/themes/generations/$generation/visual.tsv"
    if test -r "$visual_file"
        while read -l visual_line
            set -l fields (string split -m 2 \t -- "$visual_line")
            test (count $fields) -eq 3; or return 1
            if test "$fields[1]" = env
                string match -rq '^[A-Z][A-Z0-9_]*$' -- "$fields[2]"; or return 1
                set -gx $fields[2] "$fields[3]"
            end
        end < "$visual_file"
        if set -q DOTS_THEME_FZF_COLORS
            set -q _DOTS_VISUAL_FZF_BASE; or set -g _DOTS_VISUAL_FZF_BASE "$FZF_DEFAULT_OPTS"
            set -l fzf_base "$_DOTS_VISUAL_FZF_BASE"
            if set -q DOTS_THEME_FZF_OPTS
                set fzf_base "$DOTS_THEME_FZF_OPTS"
            end
            set -gx FZF_DEFAULT_OPTS "$fzf_base --color=$DOTS_THEME_FZF_COLORS"
        end
    end
    set -g _DOTS_THEME_GENERATION "$generation"
end
function _dots_fish_prompt --on-event fish_prompt
    set -l previous_status $status
    if test $_dots_option_DOTS_THEME_AUTO_UPDATE = 1
        _dots_fish_theme
    end
    if test $_dots_option_DOTS_INIT_COMPLETION = 1
        set -l token
        if test -r "$_DOTS_STATE/themes/commands/current/fingerprint"
            read -l token < "$_DOTS_STATE/themes/commands/current/fingerprint"
            if test "$token" != "$_DOTS_COMMAND_TOKEN"
                source "$DOTS/lib/dots/completion/fish"
                set -g _DOTS_COMMAND_TOKEN "$token"
            end
        end
    end
    return $previous_status
end
set -g _DOTS_THEME_GENERATION ''
_dots_fish_theme; or printf 'dots: theme artifact unavailable; run theme refresh\n' >&2
if test $_dots_option_DOTS_INIT_COMPLETION = 1
    source "$DOTS/lib/dots/completion/fish"
else
    set -l names dots theme
    if test -r "$_DOTS_STATE/themes/commands/current/names"
        while read -l name
            set -a names "$name"
        end < "$_DOTS_STATE/themes/commands/current/names"
    end
    for name in $names
        complete -e -c $name -a '(__dots_complete_fish)'
    end
end
