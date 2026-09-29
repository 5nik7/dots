# Cursor styles
set -gx fish_vi_force_cursor 1
set -gx fish_cursor_default block
set -gx fish_cursor_insert line blink
set -gx fish_cursor_visual block
set -gx fish_cursor_replace_one underscore

# Path
fish_add_path --path /bin
fish_add_path --path ~/.cargo/bin
fish_add_path --path ~/.local/bin
# fish_add_path --path ~/.luarocks/bin
# fish_add_path --path ~/Library/Python/3.{8,9}/bin
# fish_add_path --path /usr/local/opt/sqlite/bin
fish_add_path --path /usr/local/sbin
# fish_add_path --path ~/.gem/ruby/2.6.0/bin
# fish_add_path --path ~/.local/bin/pnpm-bins
# fish_add_path --path ~/.local/share/bob-nvim/bin
# fish_add_path --path ~/.local/share/bob-nvim/nvim-linux64/bin
fish_add_path --path /var/lib/flatpak/exports/bin/
fish_add_path --path ~/.dotnet/tools
# fish_add_path --path ~/.local/share/mise/shims

# set -gx DENO_INSTALL "~/.deno"
# fish_add_path --path ~/.deno/bin

command -q nvim; and set -gx EDITOR nvim
set -gx VISUAL $EDITOR
set -gx SUDO_EDITOR $EDITOR

# Fish
set fish_emoji_width 2

if status is-interactive
    # Commands to run in interactive sessions can go here
end

function d
    set tmp (mktemp -t "yazi-cwd.XXXXXX")
    yazi $argv --cwd-file="$tmp"
    if read -z cwd <"$tmp"; and [ -n "$cwd" ]; and [ "$cwd" != "$PWD" ]
        builtin cd -- "$cwd"
    end
    rm -f -- "$tmp"
end

abbr mv "mv -iv"
abbr cp "cp -riv"
abbr mkdir "mkdir -vp"
alias ls="eza --color=always --icons --group-directories-first"
alias la 'eza --color=always --icons --group-directories-first --all'
alias ll 'eza --color=always --icons --group-directories-first --all --long'
abbr l ll

# Editor
abbr vim nvim
abbr vi nvim
abbr v nvim
# alias vimpager 'nvim - -c "lua require(\'util\').colorize()"'
# abbr vd "VIM=~/projects/neovim nvim --luamod-dev"
abbr sv sudoedit
abbr vudo sudoedit
