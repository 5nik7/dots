zstyle ':completion:*:git-checkout:*' sort false
zstyle ':completion:*:descriptions' format '%d'
# zstyle ':completion:*:warnings' format ' %F{red}-- no matches found --%f'
zstyle ':completion:*' list-colors ${(s.:.)LS_COLORS}
zstyle ':completion:*' menu no
zstyle ':fzf-tab:*' use-fzf-default-opts yes
zstyle ':fzf-tab:*' switch-group '<' '>'

local extract="
local in=\${\${\"\$(<{f})\"%\$'\0'*}#*\$'\0'}
local -A ctxt
for entry in \${(@ps:\2:)CTXT}; do
      local key=\${entry%%=*}
      local value=\${entry#*=}
      ctxt[\$key]=\$value
done
local realpath=\${ctxt[IPREFIX]}\${ctxt[hpre]}\$in
realpath=\${(Qe)~realpath}
"
zstyle ':fzf-tab:complete:*:*' fzf-flags --preview=$extract';$_PREVIEW_ $realpath'
