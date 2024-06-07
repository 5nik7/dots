zmodload -i zsh/complist
bindkey -M menuselect '^o' accept-and-infer-next-history

zstyle ':completion:*:*:*:*:*' menu select

zstyle ':completion:*' matcher-list 'm:{a-zA-Z}={A-Za-z}' 'r:|=*' 'l:|=* r:|=*'

zstyle ':completion:*' special-dirs true
zstyle ':completion:*' list-colors ''
zstyle ':completion:*:*:kill:*:processes' list-colors '=(#b) #([0-9]#) ([0-9a-z-]#)*=01;34=0=01'

zstyle ':completion:*:cd:*' tag-order local-directories directory-stack path-directories

zstyle -e ':completion:*:(ssh|scp|sftp|rsh|rsync):hosts' hosts 'reply=(${=${${(f)"$(cat {/etc/ssh_,~/.ssh/known_}hosts(|2)(N) /dev/null)"}%%[# ]*}//,/ })'

# Don't complete uninteresting users
zstyle ':completion:*:*:*:users' ignored-patterns \
        adm amanda apache at avahi avahi-autoipd beaglidx bin cacti canna \
        clamav daemon dbus distcache dnsmasq dovecot fax ftp games gdm \
        gkrellmd gopher hacluster haldaemon halt hsqldb ident junkbust kdm \
        ldap lp mail mailman mailnull man messagebus  mldonkey mysql nagios \
        named netdump news nfsnobody nobody nscd ntp nut nx obsrun openvpn \
        operator pcap polkitd postfix postgres privoxy pulse pvm quagga radvd \
        rpc rpcuser rpm rtkit scard shutdown squid sshd statd svn sync tftp \
        usbmux uucp vcsa wwwrun xfs '_*'
# ... unless we really want to.
zstyle '*' single-ignored show

zstyle ':completion:*' list-dirs-first true
zstyle ':completion:*' menu true=long select=long
zstyle ':completion:*:matches' group yes
zstyle ':completion:*' group-name ''
zstyle ':completion:*' verbose true
zstyle ':completion:*:options' description yes
zstyle ':completion:*:options' auto-description '%d'
zstyle ':completion:*:descriptions' format $'\e[33;1m -- %d --\e[0m'
zstyle ':completion:*:messages' format $'\e[31;1m -- %d --\e[0m'
zstyle ':completion:*:warnings' format $'\e[31;1m -- No matches found --\e[0m'
zstyle ':completion:*:functions' ignored-patterns '_*'
zstyle ':completion:*:default' list-colors '=(#b)*(-- *)=0=94' ${(s.:.)LS_COLORS}

# zstyle ':fzf-tab:complete:cd:*' fzf-preview 'exa -1 --icons --git --color=always $realpath'
# zstyle ':fzf-tab:complete:nvim:*' fzf-preview 'bat --color=always --style=numbers --line-range=:500 $realpath'
# zstyle ':fzf-tab:complete:systemctl-*:*' fzf-preview 'SYSTEMD_COLORS=1 systemctl status $word'
# zstyle ':fzf-tab:complete:git-(add|diff|restore):*' fzf-preview 'git diff $word | delta'
# zstyle ':fzf-tab:complete:git-log:*' fzf-preview 'git show --color=always $word'
# zstyle ':fzf-tab:complete:git-help:*' fzf-preview 'git help $word | bat -plman --color=always'
# zstyle ':fzf-tab:complete:git-show:*' fzf-preview \
#     'case "$group" in
#     "commit tag") git show --color=always $word ;;
#     *) git show --color=always $word | delta ;;
#     esac'
# zstyle ':fzf-tab:complete:git-checkout:*' fzf-preview \
#     'case "$group" in
#     "modified file") git diff $word | delta ;;
#     "recent commit object name") git show --color=always $word | delta ;;
#     *) git log --color=always $word ;;
#     esac'