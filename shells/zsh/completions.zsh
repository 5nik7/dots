
# Basic auto/tab complete:
autoload -U compinit
# zstyle ':completion:*' menu select

zstyle ':completion:*' group-name ''
zstyle ':completion:*' completer _expand _extensions _complete _ignored _approximate
zstyle ':completion:*' matcher-list 'm:{a-zA-Z-_}={A-Za-z_-}' 'r:|=*' 'l:|=* r:|=*'

zstyle ':completion:*' list-suffixes
zstyle ':completion:*' expand prefix suffix
zstyle ':completion:*' keep-prefix true

zstyle ':completion:*' complete true

# disable sort when completing `git checkout`
zstyle ':completion:*:git-checkout:*' sort false

# set descriptions format to enable group support
zstyle ':completion:*:descriptions' format '[%d]'

# zstyle ':completion:*:*:*:*:descriptions' format '%F{green}-- %d --%f'
# zstyle ':completion:*:messages' format ' %F{purple} -- %d --%f'
# zstyle ':completion:*:warnings' format ' %F{red}-- no matches found --%f

zstyle ':completion:*' list-colors ${(s.:.)LS_COLORS}

zstyle ':completion:*' menu no

zstyle ':fzf-tab:complete:cd:*' fzf-preview 'eza -1 --color=always $realpath'

zstyle ':fzf-tab:*' fzf-flags --color=fg:7,fg+:6,pointer:6,prompt:2,gutter:-1,info:8,separator:0 --bind=tab:accept

# zstyle ':fzf-tab:*' use-fzf-default-opts yes

# switch group using `<` and `>`
zstyle ':fzf-tab:*' switch-group '<' '>'
#

zmodload zsh/complist
compinit
_comp_options+=(globdots)   # Include hidden files.

