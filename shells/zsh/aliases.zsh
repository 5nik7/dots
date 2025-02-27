function rlp() {
    local current_shell=$(basename "$SHELL")
    if [ "$current_shell" = "zsh" ]; then
        zource ~/.zshrc
        print_in_yellow "\n ZShell reloaded.\n"
    elif [ "$current_shell" = "bash" ]; then
        zource ~/.bashrc
        print_in_yellow "\n Bash reloaded.\n"
    else
        print_in_red "\n Shell not supported.\n"
    fi
}
alias rl='rlp'

alias c='clear'
alias q='exit'
alias v='nvim'

alias g='git'

alias upd='pkg update && pkg upgrade -y'

alias path='echo $PATH | tr ":" "\n"'

alias ".."="cd .."
alias "..."="cd ../.."
alias "...."="cd ../../.."
alias "....."="cd ../../../.."
alias "......"="cd ../../../../.."
alias "......."="cd ../../../../../.."
alias "........"="cd ../../../../../../.."

alias ".d"="cd $DOTS"

if cmd_exists eza; then
    function l() {
        linebreak
        eza -a -l --group-directories-first --git-repos --git --icons --time-style relative --no-permissions --no-filesize --no-time --no-user --hyperlink --follow-symlinks --no-quotes
        linebreak
    }
      function ll() {
        local timestyle='+󰨲 %m/%d/%y 󰅐 %H:%M'
        linebreak
        eza -a -l --group-directories-first --git-repos --git --icons --hyperlink --follow-symlinks --no-quotes --modified -h --no-user --time-style "$timestyle"
        linebreak
    }
      function lt() {
        local level="$1"
        if [ "$1" = "" ]; then
            level=1
        fi
        linebreak
        eza --group-directories-first --git-repos --git --icons -n --tree -L "$level"
        linebreak
    }
    alias ls="$(eza --icons "$@")"
fi

if cmd_exists yazi; then
    function y() {
      local tmp="$(mktemp -t "yazi-cwd.XXXXXX")"
      yazi "$@" --cwd-file="$tmp"
      if cwd="$(cat -- "$tmp")" && [ -n "$cwd" ] && [ "$cwd" != "$PWD" ]; then
        builtin cd -- "$cwd"
      fi
      rm -f -- "$tmp"
    }
    alias d='y'
fi

if cmd_exists nvim; then
    EDITOR='nvim'
elif cmd_exists vim; then
    EDITOR='vim'
elif cmd_exists vi; then
    EDITOR='vi'
elif cmd_exists code; then
    EDITOR='code'
else
    EDITOR='nano'
fi

export EDITOR
export SYSTEMD_EDITOR=$EDITOR
export VISUAL="$EDITOR"
export EDITOR_TERM="$TERMINAL -e $EDITOR"

alias edit='$EDITOR'
alias e='$EDITOR'
alias v='$EDITOR'
alias vi='$EDITOR'
alias vim='$EDITOR'
alias sv="sudo $EDITOR"

if [[ -d "$HOME/dev" ]]; then
  export DEV="$HOME/dev"
  alias dev="cd $DEV"
fi

if cmd_exists lazygit; then
  alias lg='lazygit'
fi
