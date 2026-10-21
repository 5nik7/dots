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
source "$DOTS/lib/dots/shell/init.fish"

# Clear recognized inherited Dots overrides without replacing custom choices.
if set -q STARSHIP_CONFIG
    for _dots_starship_root in "$DOTFILES" "$DOTCONFIG" "$DOTS/config" "$DOTS/configs" "$HOME/dots/config" "$HOME/dots/configs" "$HOME/.dots/config" "$HOME/.dots/configs"
        if test -n "$_dots_starship_root"; and test "$STARSHIP_CONFIG" = "$_dots_starship_root/starship/starship.toml"
            set -e STARSHIP_CONFIG
            break
        end
    end
end
