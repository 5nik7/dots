# z and zi share this autoload source. Only the requested command is defined.
set -l jump (path change-extension '' (path basename (status filename)))
set -l target __zoxide_$jump
function $jump --wraps $target --inherit-variable jump --inherit-variable target
    if command -sq $jump
        command $jump $argv
        return
    end
    if not functions -q $target
        if set -q dots_shell_tools; and not contains -- all $dots_shell_tools; and not contains -- zoxide $dots_shell_tools
            return 127
        end
        set -l backend "$DOTS/lib/dots/shell/tools.fish"
        if not test -r "$backend"
            set backend (path resolve (path dirname (status filename))/../../../lib/dots/shell/tools.fish)
        end
        source "$backend" zoxide --no-cmd
    end
    functions -q $target; and $target $argv
end
