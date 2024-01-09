source $THEME/drip.sh

### fzf configuration
if [ $commands[fzf] ]
then
  export FZF_DEFAULT_OPTS="
    --color=bg+:$color01,bg:$color00,spinner:$color0C,hl:$color0C,border:$color01
    --color=fg:$color04,header:$color0D,info:$color04,pointer:$color0C
    --color=marker:$color0C,fg+:$color06,prompt:$color07,hl+:$color0B
    --preview-window='border-sharp'
    --pointer='|>'
    --no-scrollbar
    --info=inline
    --preview-window='right,50%,border-left,+{2}+3/3,~3'
    --exact
    --ansi"
  if [ $commands[fd] ]
  then
    export FZF_DEFAULT_COMMAND="fd -c always"
  fi
fi

# ### fzf configuration
# if [ $commands[fzf] ]
# then
#   export FZF_DEFAULT_OPTS="
#     --color fg:-1,bg:-1,hl:5:underline,fg+:3,bg+:-1,hl+:5:underline,border:8
#     --color info:42,prompt:-1,spinner:42,pointer:51,marker:33
#     --preview-window='border-sharp'
#     --pointer='|>'
#     --no-scrollbar
#     --info=inline
#     --preview-window='right,50%,border-left,+{2}+3/3,~3'
#     --exact
#     --ansi"
#   if [ $commands[fd] ]
#   then
#     export FZF_DEFAULT_COMMAND="fd -c always"
#   fi
# fi

# vim:ft=zsh:nowrap
