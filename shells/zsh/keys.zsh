# Personal ZLE preferences. Load before plugins, then finish after their widgets.
export KEYTIMEOUT=1
export VI_MODE_SET_CURSOR=true

HISTORY_SUBSTRING_SEARCH_GLOBBING_FLAGS='i'
HISTORY_SUBSTRING_SEARCH_ENSURE_UNIQUE=1
# These switches use nonempty values as true; use '' rather than 0 to disable.
HISTORY_SUBSTRING_SEARCH_FUZZY=''
HISTORY_SUBSTRING_SEARCH_PREFIXED=''
HISTORY_SUBSTRING_SEARCH_HIGHLIGHT_TIMEOUT=1

if [[ -z ${_DOTS_ZLE_READY:-} ]]; then
  bindkey -v
  _DOTS_ZLE_READY=1
fi
zle_highlight=("${(@)zle_highlight:#paste:*}" 'paste:none')

_dots_zsh_keys_theme() {
  local previous_status=$?
  if [[ -n ${selection_foreground[hex]:-} && -n ${selection_background[hex]:-} ]]; then
    HISTORY_SUBSTRING_SEARCH_HIGHLIGHT_FOUND="fg=${selection_foreground[hex]},bg=${selection_background[hex]},bold"
  else
    HISTORY_SUBSTRING_SEARCH_HIGHLIGHT_FOUND='standout,bold'
  fi
  HISTORY_SUBSTRING_SEARCH_HIGHLIGHT_NOT_FOUND="fg=${error[hex]:-red},bold"
  return "$previous_status"
}

_dots_zsh_keys_apply() {
  # Vi-mode rewrites insert bindings at init and on mode transitions.
  bindkey -M viins '^H' backward-delete-char
  bindkey -M viins '^?' backward-delete-char

  if (( ${+widgets[history-substring-search-up]} && ${+widgets[history-substring-search-down]} )); then
    bindkey -M viins '^[[A' history-substring-search-up
    bindkey -M viins '^[[B' history-substring-search-down
    bindkey -M viins '^[OA' history-substring-search-up
    bindkey -M viins '^[OB' history-substring-search-down
    bindkey -M vicmd '^[[A' history-substring-search-up
    bindkey -M vicmd '^[[B' history-substring-search-down
    bindkey -M vicmd '^[OA' history-substring-search-up
    bindkey -M vicmd '^[OB' history-substring-search-down
    bindkey -M vicmd 'k' history-substring-search-up
    bindkey -M vicmd 'j' history-substring-search-down
    # Terminfo may be absent or contain the same sequences as the literals.
    if [[ -n ${terminfo[kcuu1]:-} ]]; then
      bindkey -M viins "$terminfo[kcuu1]" history-substring-search-up
      bindkey -M vicmd "$terminfo[kcuu1]" history-substring-search-up
    fi
    if [[ -n ${terminfo[kcud1]:-} ]]; then
      bindkey -M viins "$terminfo[kcud1]" history-substring-search-down
      bindkey -M vicmd "$terminfo[kcud1]" history-substring-search-down
    fi
  fi

  if (( ${+widgets[zsh-system-clipboard-vicmd-vi-yank-eol]} )); then
    bindkey -M vicmd 'Y' zsh-system-clipboard-vicmd-vi-yank-eol
  fi
  if (( ${+widgets[zsh-system-clipboard-vicmd-vi-put-after]} )); then
    bindkey -M viins '^V' zsh-system-clipboard-vicmd-vi-put-after
  fi
  # Keep FZF's existing priority over the vi-mode plugin's Ctrl-R default.
  if (( ${+widgets[fzf-history-widget]} )); then
    bindkey -M viins '^R' fzf-history-widget
  fi
  return 0
}

_dots_zsh_keys_cursor() {
  if [[ ${KEYMAP:-} == vicmd ]]; then
    printf '\033[1 q'
  else
    printf '\033[5 q'
  fi
}

_dots_zsh_keys_line_init() {
  zle -K viins
  _dots_zsh_keys_cursor
}

_dots_zsh_keys_preexec() {
  printf '\033[5 q'
}

_dots_zsh_keys_finish() {
  zmodload -i zsh/terminfo 2>/dev/null || :
  _dots_zsh_keys_apply
  _dots_zsh_keys_theme
  autoload -Uz add-zsh-hook add-zle-hook-widget
  # The Dots theme hook is already registered; read its refreshed arrays next.
  add-zsh-hook precmd _dots_zsh_keys_theme
  add-zsh-hook preexec _dots_zsh_keys_preexec
  if (( ! ${+functions[zvm_init]} )); then
    add-zle-hook-widget line-init _dots_zsh_keys_line_init
    add-zle-hook-widget keymap-select _dots_zsh_keys_cursor
  fi
  return 0
}

# Register before the Termux hook can source vi-mode. The lazy callback runs
# after its first normal-mode map installation, later than mode-selection hooks.
typeset -ga zvm_after_init_commands zvm_after_select_vi_mode_commands zvm_after_lazy_keybindings_commands
(( ${zvm_after_init_commands[(Ie)_dots_zsh_keys_apply]} )) ||
  zvm_after_init_commands+=(_dots_zsh_keys_apply)
(( ${zvm_after_select_vi_mode_commands[(Ie)_dots_zsh_keys_apply]} )) ||
  zvm_after_select_vi_mode_commands+=(_dots_zsh_keys_apply)
(( ${zvm_after_lazy_keybindings_commands[(Ie)_dots_zsh_keys_apply]} )) ||
  zvm_after_lazy_keybindings_commands+=(_dots_zsh_keys_apply)
