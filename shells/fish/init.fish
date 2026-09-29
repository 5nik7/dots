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
contains -- "$DOTS/shells/fish/completions" $fish_complete_path; or set -gp fish_complete_path "$DOTS/shells/fish/completions"
if not set -q _dots_fish_config_ready
    # Explicit list preserves conf.d ordering without discovery at startup.
    for snippet in autopair done fish_frozen_key_bindings fish_frozen_theme fzf usage
        test ! -r "$DOTS/shells/fish/conf.d/$snippet.fish"; or source "$DOTS/shells/fish/conf.d/$snippet.fish"
    end
    set -g _dots_fish_config_ready 1
end
source "$DOTS/shells/fish/interactive.fish"
