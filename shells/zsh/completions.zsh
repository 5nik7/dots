# Basic auto/tab complete:
autoload -U compinit
zstyle ':completion:*' menu select
zmodload zsh/complist
compinit
_comp_options+=(globdots)   # Include hidden files.

zstyle ':completion:*' group-name ''
zstyle ':completion:*' completer _expand _extensions _complete _ignored _approximate
zstyle ':completion:*' matcher-list 'm:{a-zA-Z-_}={A-Za-z_-}' 'r:|=*' 'l:|=* r:|=*'

zstyle ':completion:*' list-suffixes
zstyle ':completion:*' expand prefix suffix
zstyle ':completion:*' keep-prefix true

zstyle ':completion:*' complete true

