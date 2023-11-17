#!/usr/bin/zsh

setopt extended_history      # Record start time and elapsed time in history file
setopt append_history        # Add history (instead of creating .zhistory every time)
setopt hist_ignore_all_dups  # Delete older command lines if they overlap
setopt hist_ignore_dups      # Do not add the same command line to history as the previous one
setopt hist_ignore_space     # Remove command lines beginning with a space from history
setopt hist_reduce_blanks    # Extra white space is stuffed and recorded <-teraterm makes history or crazy
setopt hist_save_no_dups     # Ignore old commands that are the same as old commands when writing to history file.
setopt hist_no_store         # history commands are not registered in history
setopt hist_expand           # automatically expand history on completion
setopt share_history
setopt auto_cd               # Move by directory only
setopt no_beep               # Don't beep on command input error
setopt equals                # Expand =COMMAND to COMMAND pathname
setopt nonomatch             # Enable glob expansion to avoid nomatch
setopt glob
setopt extended_glob         # Enable expanded globs
setopt hash_cmds             # Put path in hash when each command is executed         # Don't logout with C-d
setopt long_list_jobs        # Make internal command jobs output jobs -L by default
setopt magic_equal_subst     # command line arguments can be completed after =, e.g. --PREFIX=/USR
setopt multios               # TEE and CAT features are used as needed, such as multiple redirects and pipes
setopt notify                # Notify as soon as background job finishes (don't wait for prompt)
setopt interactive_comments  # Allow comments while typing commands

SAVEHIST=100000
HISTSIZE=100000
HISTFILE=~/.zsh_history

WORDCHARS=''