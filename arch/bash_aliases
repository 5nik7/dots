alias c="clear"
alias q="exit"
alias cleanram="sudo sh -c 'sync; echo 3 > /proc/sys/vm/drop_caches'"
alias trim_all="sudo fstrim -va"
alias mkgrub='sudo grub-mkconfig -o /boot/grub/grub.cfg'
alias mtar='tar -zcvf' # mtar <archive_compress>
alias utar='tar -zxvf' # utar <archive_decompress> <file_list>
alias z='zip -r' # z <archive_compress> <file_list>
alias uz='unzip' # uz <archive_decompress> -d <dir>
alias ..="cd .."
alias psg="ps aux | grep -v grep | grep -i -e VSZ -e"
alias mkdir="mkdir -p"
alias pacin="pacman -Slq | fzf -m --preview 'cat <(pacman -Si {1}) <(pacman -Fl {1} | awk \"{print \$2}\")' | xargs -ro sudo pacman -S"
alias paruin="paru -Slq | fzf -m --preview 'cat <(paru -Si {1}) <(paru -Fl {1} | awk \"{print \$2}\")' | xargs -ro  paru -S"
alias pacrem="pacman -Qq | fzf --multi --preview 'pacman -Qi {1}' | xargs -ro sudo pacman -Rns"
alias pac="pacman -Q | fzf"
alias parucom="paru -Gc"
alias parupd="paru -Qua"
alias pacupd="pacman -Qu"
alias parucheck="paru -Gp"
alias cleanpac='sudo pacman -Rns $(pacman -Qtdq); paru -c'
alias installed="grep -i installed /var/log/pacman.log"

# use exa if available
if [[ -x "$(command -v exa)" ]]; then
  alias ll="exa -HF --icons --git --long --group-directories-first"
  alias l="exa -HF --icons --git --all --long --group-directories-first"
else
  alias l="ls -lah ${colorflag}"
  alias ll="ls -lFh ${colorflag}"
fi

alias la="ls -AF ${colorflag}"
alias lld="ls -l | grep ^d"
alias cp='cp -rv'
alias mv='mv -v'
alias srm='sudo rm -rfv'
alias lnf='ln -sfv'
alias mkdir='mkdir -v'
alias lpath='echo $PATH | tr ":" "\n"'
alias bat='bat --color=always --paging=never'
alias grep='grep --color=auto'
alias mv='mv -v'
alias cp='cp -vr'
alias rm='rm -vrf'
alias t='tmux'
alias tls='tmux ls'
alias tks='tmux kill-session'
alias v=$EDITOR
alias vim=$EDITOR
alias d='ranger'
alias update='sudo pacman -Syyuu --noconfirm'
alias dots='cd $DOTFILES'

# vim:ft=zsh
