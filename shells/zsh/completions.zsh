zstyle ':completion:*:git-checkout:*' sort false
zstyle ':completion:*:descriptions' format '%d'
# zstyle ':completion:*:warnings' format ' %F{red}-- no matches found --%f'
# Resolve at completion time: theme refresh replaces LS_COLORS after startup.
zstyle -e ':completion:*' list-colors 'reply=("${(@s.:.)LS_COLORS}")'
zstyle ':completion:*' menu no
zstyle ':fzf-tab:*' use-fzf-default-opts yes
zstyle ':fzf-tab:*' switch-group '<' '>'
source "$DOTS/lib/dots/completion/styles.zsh"

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

# Only a displayed FZF-tab menu allocates preview storage. Ordinary completion
# and shell startup never invoke Anodize's engine. Dynamic scope carries words.
_dots_theme_preview_fzf() {
  local preview_dir
  preview_dir=$(command mktemp -d "${TMPDIR:-/tmp}/dots-completion.XXXXXXXX") || return 1
  local -x DOTS_COMPLETION_PREVIEW_DIR=$preview_dir
  local -x DOTS_COLOR=${DOTS_COLOR:-auto}
  if [[ $DOTS_COLOR == auto ]]; then
    [[ -z ${NO_COLOR:-} && ${TERM:-dumb} != dumb ]] && DOTS_COLOR=always || DOTS_COLOR=never
  fi
  {
    command fzf "$@"
  } always {
    command rm -rf -- "$preview_dir"
  }
}
for _dots_preview_command in anodize theme; do
  zstyle ":fzf-tab:complete:${_dots_preview_command}:*" fzf-command _dots_theme_preview_fzf
  zstyle ":fzf-tab:complete:${_dots_preview_command}:*" fzf-min-height 20
  zstyle ":fzf-tab:complete:${_dots_preview_command}:*" fzf-flags --preview-window=down,70%
  zstyle ":fzf-tab:complete:${_dots_preview_command}:*" fzf-preview '
    python3 -B "$DOTS/plugins/anodize/completion_preview.py" "$DOTS_COMPLETION_PREVIEW_DIR" "$word" "${(@Q)words}"
    if (( $? == 3 )) && [[ -n ${realpath:-} && -n ${_PREVIEW_:-} ]]; then
      "$_PREVIEW_" "$realpath"
    fi'
done
unset _dots_preview_command

# The generic Dots completion function also serves files, Git and other routes.
# Keep their existing preview flags and backend; specialize only theme routes.
_dots_theme_completion_context() {
  local -a preview_words=("${(@Q)words}")
  shift preview_words
  while [[ ${preview_words[1]:-} == (--color=*|--icons=*) ]]; do shift preview_words; done
  [[ ${preview_words[1]:-} == (anodize|theme|themes) ]]
}
_dots_config_completion_context() {
  local -a config_words=("${(@Q)words}")
  shift config_words
  while [[ ${config_words[1]:-} == (--color=*|--icons=*) ]]; do shift config_words; done
  [[ ${config_words[1]:-} == config ]]
}
_dots_config_branch_completion_context() {
  local -a config_words=("${(@Q)words[2,CURRENT-1]}")
  local token expecting=0
  while [[ ${config_words[1]:-} == (--color=*|--icons=*) ]]; do shift config_words; done
  [[ ${config_words[1]:-} == config && ${config_words[2]:-} == (get|set|unset|explain) ]] || return 1
  shift 2 config_words
  for token in "${config_words[@]}"; do
    if (( expecting )); then expecting=0
    elif [[ $token == (--profile|--app) ]]; then expecting=1
    elif [[ $token != --* ]]; then return 1
    fi
  done
  (( ! expecting )) && [[ ${PREFIX:-${words[CURRENT]:-}} == (*.|*\[) ]]
}
# FZF's ** suffix is consumed before selection. Config's .. similarly scopes
# branch candidates; suppress fzf-tab's common-prefix/input query for this case.
zstyle -e ':fzf-tab:complete:dots:*' query-string '
  if _dots_config_branch_completion_context; then reply=()
  else zstyle -a ":fzf-tab:complete:__dots_preview_fallback__:" query-string reply || reply=(prefix input first)
  fi'
zstyle -e ':fzf-tab:complete:dots:*' fzf-command '
  if _dots_theme_completion_context; then reply=(_dots_theme_preview_fzf)
  else
    zstyle -s ":fzf-tab:complete:__dots_preview_fallback__:" fzf-command reply || reply=(fzf)
  fi'
zstyle -e ':fzf-tab:complete:dots:*' fzf-flags '
  if _dots_config_completion_context; then reply=(--preview-window=down,35%)
  elif _dots_theme_completion_context; then reply=(--preview-window=down,70%)
  else zstyle -a ":fzf-tab:complete:__dots_preview_fallback__:" fzf-flags reply
  fi'
zstyle -e ':fzf-tab:complete:dots:*' fzf-min-height '
  if _dots_theme_completion_context; then reply=(20)
  else
    zstyle -s ":fzf-tab:complete:__dots_preview_fallback__:" fzf-min-height reply || reply=(0)
  fi'
zstyle -e ':fzf-tab:complete:dots:*' fzf-preview '
  if _dots_config_completion_context; then
    reply=("python3 -B \"\$DOTS/lib/dots/config_completion.py\" preview \"\$word\"")
  elif _dots_theme_completion_context; then
    zstyle -s ":fzf-tab:complete:anodize:" fzf-preview reply
  else reply=()
  fi'
