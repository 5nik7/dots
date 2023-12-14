# Options foldstart
# Completion
setopt AUTO_LIST               # automatically list choices on ambiguous completion
setopt AUTO_MENU               # show completion menu on a successive tab press
setopt AUTO_PARAM_SLASH        # if completed parameter is a directory, add a trailing slash
setopt COMPLETE_IN_WORD        # complete from the cursor rather than from the end of the word
setopt NO_MENU_COMPLETE        # do not autoselect the first completion entry
setopt HASH_LIST_ALL
setopt ALWAYS_TO_END

# History
setopt HIST_SAVE_NO_DUPS
setopt HIST_IGNORE_ALL_DUPS
setopt SHARE_HISTORY             # write and import history on every command
setopt HIST_FIND_NO_DUPS

# OTHER
setopt INTERACTIVE_COMMENTS    # allow comments in command line
setopt NOBEEP

setopt extended_history
setopt append_history
setopt hist_ignore_all_dups
setopt hist_ignore_dups
setopt hist_ignore_space
setopt hist_reduce_blanks
setopt hist_save_no_dups
setopt hist_no_store
setopt hist_expand
setopt share_history
setopt auto_cd
setopt no_beep
setopt nonomatch
setopt glob
setopt extended_glob
setopt interactive_comments
setopt rmstarsilent

SAVEHIST=100000
HISTSIZE=100000
HISTFILE=~/.zsh_history

WORDCHARS='*?[]~=&;!#$%^(){}<>'
