### fzf configuration
if [ $commands[fzf] ]
then
  export FZF_DEFAULT_OPTS='
    --color fg:-1,bg:-1,hl:5:underline,fg+:3,bg+:-1,hl+:5:underline,border:8
    --color info:42,prompt:-1,spinner:42,pointer:51,marker:33
    --preview-window='border-sharp'
    --pointer="|>"
    --no-scrollbar
    --info=inline
    --preview-window='right,50%,border-left,+{2}+3/3,~3'
    --exact
    --ansi'
  if [ $commands[fd] ]
  then
    export FZF_DEFAULT_COMMAND="fd -c always"
  fi
fi

    # --color fg:$foreground,bg:$background,hl:11:underline,hl+:3:underline:reverse,fg+:13,bg+:$backgroud,gutter:$background,border:0
    # --color info:8,prompt:8,spinner:5,pointer:10,marker:13
    # --border=sharp
    # --info=inline
    # --preview-window='border-sharp'

# Setup fzf
# ---------
#if [[ ! "$PATH" == */usr/local/opt/fzf/bin* ]]; then
#  export PATH="$PATH:/usr/local/opt/fzf/bin"
#fi

# Man path
# --------
#if [[ ! "$MANPATH" == */usr/local/opt/fzf/man* && -d "/usr/local/opt/fzf/man" ]]; then
#  export MANPATH="$MANPATH:/usr/local/opt/fzf/man"
#fi

# Auto-completion
# ---------------
#[[ $- == *i* ]] && source "/usr/local/opt/fzf/shell/completion.zsh" 2> /dev/null

# Key bindings
# ------------
#FILE="/usr/local/opt/fzf/shell/key-bindings.zsh"
#if [[ -a $FILE ]]; then
#    source $FILE
#fi
