set -l root "$HOME/dots"
set -l cli (command -s dots)
if set -q DOTS_BOOTSTRAP_DIR; and test -n "$DOTS_BOOTSTRAP_DIR"
    set root "$DOTS_BOOTSTRAP_DIR"
else if not test "$cli" -ef "$root/bin/dots"; and test -f "$HOME/.local/share/dots/bootstrap/checkout"; and test -r "$HOME/.local/share/dots/bootstrap/checkout"
    read -l pin < "$HOME/.local/share/dots/bootstrap/checkout"
    test -z "$pin"; or set root "$pin"
end
if not string match -q '/*' -- "$root"; or not test -f "$root/bin/dots"; or not test -x "$root/bin/dots"; or not test -r "$root/lib/dots/shell/startup.bash"; or not test -r "$root/shells/fish/init.fish"; or begin
    test -z "$DOTS_BOOTSTRAP_DIR"; and test -n "$cli"; and not test "$cli" -ef "$root/bin/dots"
end
    set -l mode offline
    status is-interactive; and set mode interactive
    set root (command sh "$HOME/.local/share/dots/bootstrap/locate.sh" "$mode" fish)
end
if test -n "$root"; and test -r "$root/shells/fish/init.fish"
    source "$root/shells/fish/init.fish"
end
