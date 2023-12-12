### fzf configuration
if [ $commands[fzf] ]
then
  export FZF_DEFAULT_OPTS='
    --color fg:-1,bg:-1,hl:5,fg+:3,bg+:-1,hl+:5
    --color info:42,prompt:-1,spinner:42,pointer:51,marker:33
    --exact
    --ansi'
  if [ $commands[fd] ]
  then
    export FZF_DEFAULT_COMMAND="fd -c always"
  fi
fi


# export FZF_DEFAULT_OPTS="
# --color fg:$foreground,bg:$background,hl:11:underline,hl+:3:underline:reverse,fg+:13,bg+:$backgroud,gutter:$background,border:0
# --color info:8,prompt:8,spinner:5,pointer:10,marker:13
# --pointer='|>'
# --ansi
$ --no-scrollbar
# --info=inline
# --border=sharp
# --preview-window='border-sharp'"
