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
source "$_dots_fish_directory/init.fish"
