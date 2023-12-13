if [ $commands[eza] ]
then
  alias ll="ll_eza"
  alias l="ls_eza"
fi

alias grep='grep --color=auto' # colorize matching parts
alias less='less -R -M -X' # -R : enable colors; -M : shows more detailed prompt, including file position; -N : shows line number; -X : supresses the terminal clearing at exit;

# get top process eating memory
alias psmem='ps auxf | sort -nr -k 4 | head -5'

# get top process eating cpu ##
alias pscpu='ps auxf | sort -nr -k 3 | head -5'

alias archlinx-fix-keys="sudo pacman-key --init && sudo pacman-key --populate archlinux && sudo pacman-key --refresh-keys"

# systemd
alias mach_list_systemctl="systemctl list-unit-files --state=enabled"

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
#alias mkdir='mkdir -v"

alias lg='lazygit'

alias update='sudo pacman -Syyu'
alias pacin="pacman -Slq | fzf -m --preview 'cat <(pacman -Si {1}) <(pacman -Fl {1} | awk \"{print \$2}\")' | xargs -ro sudo pacman -S"
alias pacrem="pacman -Qq | fzf --multi --preview 'pacman -Qi {1}' | xargs -ro sudo pacman -Rns"
alias pac="pacman -Q | fzf"
alias installed="grep -i installed /var/log/pacman

alias py3='python3'
alias py='python'

# vim:ft=zsh
