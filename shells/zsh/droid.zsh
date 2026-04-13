[ -z $USER ] && export USER="$(whoami)"

export ZSH_SYSTEM_CLIPBOARD_METHOD="termux"

function zvm_config() {
  ZVM_SYSTEM_CLIPBOARD_ENABLED=true
  ZVM_CLIPBOARD_COPY_CMD='termux-clipboard-set'
  ZVM_CLIPBOARD_PASTE_CMD='termux-clipboard-get'

  ZVM_OPEN_CMD='termux-open'
  ZVM_OPEN_URL_CMD='termux-open-url'
  ZVM_OPEN_FILE_CMD='nvim'
  ZVM_VI_HIGHLIGHT_FOREGROUND="$crust"
  ZVM_VI_HIGHLIGHT_BACKGROUND="$flamingo"
  ZVM_VI_HIGHLIGHT_EXTRASTYLE=bold

}

zvm_after_init_commands+=('[ -f ~/.fzf.zsh ] && source ~/.fzf.zsh')

export LYNX_CFG="$DOTFILES/lynx/lynx.cfg"
export LYNX_LSS="$DOTFILES/lynx/lynx.lss"

export TERMUX_APP_PACKAGE_MANAGER='apt'

export DROIDOTS="$DOTS/androidots"
export DROIDBIN="$DROIDOTS/bin"

export RISH_APPLICATION_ID="com.termux"

prepath "$DROIDBIN"

function open() {
  termux-open "$@" &>/dev/null &
}

alias rlt="termux-reload-settings"

alias bon="export BTRY='on'"
alias boff="export BTRY=''"

alias upd="pkg update && pkg upgrade -y"

alias ".a"="cd $DROIDOTS"
alias ".af"="cd $DROIDOTS/configs"
alias ".ab"="cd $DROIDOTS/bin"
alias ".v"="cd $DROIDOTS/configs/nvim"

alias path='echo -e ${PATH//:/\\n}'
alias "p:"='echo $PATH | tr ":" "\n"'

function spath() {
  local args="$@"

  echo "${args[@]}" | sed "s|${HOME}|~|" | sed "s|${PREFIX}|/usr|"
}

updpkg() {
  local pkgs="$DROIDOTS/packages"
  echo "$(pkg list-installed 2>/dev/null)" | sed '1d' | tr "/" " " | awk '{print $1}' >|"$pkgs"
}

extpath "${HOME}/perl5/bin"

if has perl; then
  PERL5LIB="${HOME}/perl5/lib/perl5${PERL5LIB:+:${PERL5LIB}}"
  export PERL5LIB
  PERL_LOCAL_LIB_ROOT="${HOME}/perl5${PERL_LOCAL_LIB_ROOT:+:${PERL_LOCAL_LIB_ROOT}}"
  export PERL_LOCAL_LIB_ROOT
  PERL_MB_OPT="--install_base \"${HOME}/perl5\""
  export PERL_MB_OPT
  PERL_MM_OPT="INSTALL_BASE=${HOME}/perl5"
  export PERL_MM_OPT
fi
