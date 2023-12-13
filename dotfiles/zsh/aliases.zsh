if [ $commands[eza] ]
then
  alias ll="ll_eza"
  alias l="ls_eza"
fi

alias grep='grep --color=auto' # colorize matching parts
alias less='less -R -M -X' # -R : enable colors; -M : shows more detailed prompt, including file position; -N : shows line number; -X : supresses the terminal clearing at exit;

alias c="clear"
alias q="exit"
alias ..="cd .."
alias path='echo $PATH | tr ":" "\n"'
alias d='ranger'
alias npmup='npm install -g npm@latest'
alias v="$EDITOR"
alias vi="$EDITOR"
alias dot='cd $DOTS'
alias repos='cd $REPOS'
alias cat='bat'
alias mkdir='mkdir -pv'

alias lg='lazygit'

alias update='sudo pacman -Syyu'

alias py3='python3'
alias py='python'

# vim:ft=zsh
