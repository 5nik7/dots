# Setup fzf
# ---------
if [[ ! "$PATH" == */home/njen/.fzf/bin* ]]; then
  PATH="${PATH:+${PATH}:}/home/njen/.fzf/bin"
fi

# Auto-completion
# ---------------
source "/home/njen/.fzf/shell/completion.zsh"

# Key bindings
# ------------
source "/home/njen/.fzf/shell/key-bindings.zsh"
