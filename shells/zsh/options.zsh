HISTFILE=~/.zsh_history
HISTSIZE=100000
SAVEHIST=$HISTSIZE

# Apply preferences in the sourcing scope. LOCAL_OPTIONS belongs to the caller.
for _dots_zsh_option in append_history no_bg_nice local_traps hist_expire_dups_first \
    hist_ignore_dups hist_ignore_space hist_verify hist_ignore_all_dups hist_find_no_dups \
    inc_append_history share_history extended_glob no_clobber interactive_comments \
    no_list_beep always_to_end auto_list menu_complete complete_in_word re_match_pcre \
    complete_aliases ignore_eof; do
  [[ -z ${options[$_dots_zsh_option]+set} ]] || setopt "$_dots_zsh_option"
done
unset _dots_zsh_option
# A running shell can still contain the helper from an older prepared bundle.
case ${functions_source[setopt_if_exists]-} in
  "$DOTS/shells/zsh/options.zsh"|"${XDG_CACHE_HOME:-$HOME/.cache}"/dots/startup/zsh-*/*/bundle)
    unfunction setopt_if_exists ;;
esac
unsetopt beep
