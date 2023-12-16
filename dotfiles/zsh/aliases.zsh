# sudo not required for some system commands
for command in pacman su apt ; do
	alias $command="sudo $command"
done; unset command

alias sudo='sudo '
alias visudo="EDITOR=nvim visudo"

alias la="ls -A"
alias lh="ls -d -A .?*" # Shows only hidden files (only on current directory)
alias rm="rm -i"

if [ $commands[eza] ]
then
  alias ll="ll_eza"
  alias l="ls_eza"
fi

alias open="xdg-open"

alias less='less -R -M -X'
alias ls='ls --color=auto'
alias grep='grep --colour=auto'
alias egrep='egrep --colour=auto'
alias fgrep='fgrep --colour=auto'
alias diff="colordiff"
alias cat="bat --plain --wrap=never --paging=never"
alias tree="tree -C"

# get top process eating memory
alias psmem='ps auxf | sort -nr -k 4 | head -5'
# get top process eating cpu ##
alias pscpu='ps auxf | sort -nr -k 3 | head -5'

alias archlinx-fix-keys="sudo pacman-key --init && sudo pacman-key --populate archlinux && sudo pacman-key --refresh-keys"

# systemd
alias sysd-on="systemctl list-unit-files --state=enabled"

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

alias lg='lazygit'

alias update='sudo pacman -Syu --noconfirm'
alias pacin="pacman -Slq | fzf -m --preview 'cat <(pacman -Si {1}) <(pacman -Fl {1} | awk \"{print \$2}\")' | xargs -ro sudo pacman -S"
alias pacrem="pacman -Qq | fzf --multi --preview 'pacman -Qi {1}' | xargs -ro sudo pacman -Rns"
alias pac="pacman -Q | fzf"
alias installed="rm ~/.pacman.list && pac-ages"

alias py3='python3'
alias py='python'

alias ".."="cd .."
alias "..."="cd ../.."
alias "...."="cd ../../.."
alias "....."="cd ../../../.."
alias "......"="cd ../../../../.."
alias "......."="cd ../../../../../.."
alias "........"="cd ../../../../../../.."

alias "h_"="~"

alias startx="startx \"$XDG_CONFIG_HOME/X11/xinitrc\""

# vim:ft=zsh:nowrap
