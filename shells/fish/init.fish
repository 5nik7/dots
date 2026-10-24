# Resolve the file itself before taking its parent directory.
set -l _dots_fish_file (path resolve -- (status filename))
if test (count $_dots_fish_file) -ne 1; or not test -r "$_dots_fish_file"
    printf 'dots: cannot resolve Fish startup file\n' >&2
    return 1
end
set -l _dots_fish_directory (path dirname -- "$_dots_fish_file")
if not test -r "$_dots_fish_directory/environment.fish"; or not test -r "$_dots_fish_directory/../../bin/dots"
    printf 'dots: Fish startup requires the Dots checkout layout\n' >&2
    return 1
end
source "$_dots_fish_directory/environment.fish"; or return
status is-interactive; or return 0
for directory in "$DOTS/shells/fish/functions"
    contains -- "$directory" $fish_function_path; or set -gp fish_function_path "$directory"
end
# User configuration and installed local completions override bundled providers.
set -l _dots_fish_config "$HOME/.config"
set -l _dots_fish_data "$HOME/.local/share"
if set -q XDG_CONFIG_HOME; and test -n "$XDG_CONFIG_HOME"
    set _dots_fish_config "$XDG_CONFIG_HOME"
end
if set -q XDG_DATA_HOME; and test -n "$XDG_DATA_HOME"
    set _dots_fish_data "$XDG_DATA_HOME"
end
set -l _dots_completion_paths
for directory in "$_dots_fish_config/fish/completions" "$_dots_fish_data/fish/vendor_completions.d"
    test ! -d "$directory"; or set -a _dots_completion_paths "$directory"
end
# Androidots is optional. Fixed native paths only; never generate on startup.
if test -d "$DOTS/androidots"
    if test -n "$TERMUX_VERSION$TERMUX__PREFIX"; or string match -q '*/com.termux/files/usr' -- "$PREFIX"
        contains -- "$DOTS/androidots/shells/fish/completions" $_dots_completion_paths; or set -a _dots_completion_paths "$DOTS/androidots/shells/fish/completions"
    end
end
contains -- "$DOTS/shells/fish/completions" $_dots_completion_paths; or set -a _dots_completion_paths "$DOTS/shells/fish/completions"
for directory in $fish_complete_path
    contains -- "$directory" $_dots_completion_paths; or set -a _dots_completion_paths "$directory"
end
set -g fish_complete_path $_dots_completion_paths
if not set -q _dots_fish_config_ready
    # Explicit list preserves conf.d ordering without discovery at startup.
    for snippet in autopair done fish_frozen_key_bindings fish_frozen_theme fzf usage
        test ! -r "$DOTS/shells/fish/conf.d/$snippet.fish"; or source "$DOTS/shells/fish/conf.d/$snippet.fish"
    end
    set -g _dots_fish_config_ready 1
end
source "$DOTS/shells/fish/interactive.fish"
