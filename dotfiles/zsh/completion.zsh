autoload -Uz colors && colors

ZSH_COMPDUMP="${ZDOTDIR:-$HOME}/.zcompdump"
autoload -Uz compinit
if [ $ZSH_COMPDUMP(Nmh-24) ]
then # check for recent compdump file within last 24h
  compinit -C # -C do not validate cache
else
  rm -f $ZSH_COMPDUMP
  compinit
fi

# zstyle ':completion:*' use-cache on
# zstyle ':completion::complete:*' cache-path "${ZDOTDIR:-$HOME}/.zcompcache"
# zstyle ':completion::complete:paket:add:*' use-cache off

LISTMAX=0
ZLE_SPACE_SUFFIX_CHARS=$'&|'

_comp_options+=(globdots)

zstyle ':fzf-tab:*'                 prefix ''
zstyle ':fzf-tab:*'                 fzf-flags '--no-mouse'
zstyle ':fzf-tab:complete:cd:*' fzf-preview 'eza -lA --color=always --icons --git-repos --git --group-directories-first --no-filesize --no-user --no-time --no-permissions $realpath'

# zstyle ':completion:*:descriptions' format '[%d]'

zstyle ':completion:*:*:-command-:*:*' file-patterns '*(#q-*):executables:executable\ file *(-/):directories:directory'

zstyle ':completion:*'                 ignored-patterns '_*'

zstyle ':completion:*:options'         description 'yes'

# zstyle ':completion:*:options'         auto-description 'specify: %d'
# zstyle ':completion:*:descriptions'    format '%F{yellow}❬%B%d%b%F{yellow}❭%f' # enable and format completion groups
# zstyle ':completion:*:warnings'        format '%F{red}no matches%f' # enable and format no match
# zstyle ':completion:*:messages'        format '%F{purple}%d%f'
# # zstyle ':completion:*:corrections'     format '%U%F{green}%d (errors: %e)%f%u'

# zstyle ':completion:*'                 special-dirs true
# zstyle ':completion:*'                 ignore-parents parent pwd # cd will never select the parent directory (e.g.: cd ../<TAB>)
# zstyle ':completion:*'                 list-dirs-first yes # list folders first on completion
# zstyle ':completion:*'                 list-colors ${(s.:.)LS_COLORS} # colorize file system completion

### Menu behaviour
zstyle ':completion:*'                 menu select # interactive # always show completions
zstyle ':completion:*:default'         menu yes=0 select=0
zstyle ':completion:*:default'         menu select
# zstyle ':completion:*:manuals'         separate-sections true
# zstyle ':completion:*'                 auto-description true
# zstyle ':completion:*:auto-describe'   format 'specify: %d'

### Listing behaviour
zstyle ':completion:*'                 list-prompt '%SAt %p: Hit TAB for more, or the character to insert%s' # Make the list prompt friendly
zstyle ':completion:*'                 last-prompt yes
zstyle ':completion:*'                 list-grouped yes
zstyle ':completion:*'                 list-packed yes
zstyle ':completion:*'                 file-list always
zstyle ':completion:*'                 strip-comments false

zstyle ':completion:*:*:*:*:processes'       command 'ps -u ${USER} -o pid,user,command'
zstyle ':completion:*:*:*:*:processes'       list-colors '=(#b) #([0-9]#) ([0-9a-z-_]#)*=0=01;34=02=0'
zstyle ':completion:*:*:*:*:processes-names' command  'ps -c -u ${USER} -o command | uniq'

zstyle ':completion:*:kill:*'                force-list always
zstyle ':completion:*:killall:*'             command 'ps -u $USER -o command'

zstyle ':completion:*'                       sort true
# zstyle ':completion:*:git-checkout:*'        sort false

# vim:ft=zsh:nowrap
