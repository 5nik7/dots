
HISTFILE=~/.zsh_history
HISTSIZE=10000
SAVEHIST=$HISTSIZE

setopt_if_exists() {
  if [[ "${options[$1]+1}" ]]; then
    setopt "$1"
  fi
}

setopt_if_exists hist_expire_dups_first
setopt_if_exists hist_ignore_dups
setopt_if_exists hist_ignore_space
setopt_if_exists hist_verify
setopt_if_exists hist_ignore_all_dups
setopt_if_exists hist_find_no_dups
setopt_if_exists inc_append_history
setopt_if_exists share_history
setopt_if_exists extended_glob
setopt_if_exists no_clobber
setopt_if_exists interactive_comments
setopt_if_exists no_list_beep
setopt_if_exists always_to_end
setopt_if_exists auto_list
setopt_if_exists menu_complete
setopt_if_exists complete_in_word

unset setopt_if_exists
unsetopt beep

zle_highlight=('paste:none')

bindkey -v
