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
set -gx DOTS (path resolve -- "$_dots_fish_directory/../..")
set -gx DOTBIN "$DOTS/bin"
set -gx DOTSCRIPTS "$DOTS/scripts"
set -gx DOTFILES "$DOTS/config"
set -gx DOTCONFIG "$DOTFILES"
set -gx DOTSHHHH "$DOTS/secrets"
set -gx SHELLS "$DOTS/shells"
set -gx ZSH "$SHELLS/zsh"
set -gx PWSH "$SHELLS/powershell"
for directory in "$DOTBIN" "$DOTSCRIPTS"
    if test -d "$directory"; and not contains -- "$directory" $PATH
        set -gx PATH "$directory" $PATH
    end
end
