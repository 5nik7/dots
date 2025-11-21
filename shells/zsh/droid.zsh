export ZSH_SYSTEM_CLIPBOARD_METHOD="termux"

zinit light kutsan/zsh-system-clipboard

export LYNX_CFG="$DOTFILES/lynx/lynx.cfg"
export LYNX_LSS="$DOTFILES/lynx/lynx.lss"

export TERMUX_APP_PACKAGE_MANAGER='apt'

export DROIDOTS="$DOTS/androidots"

prepend_path "$DROIDOTS/bin"

function open() {
  termux-open "$@"
}

alias rlt="termux-reload-settings"

alias bon="export BTRY='on'"
alias boff="export BTRY=''"

alias upd="pkg update && pkg upgrade -y"

alias ".a"="cd $DROIDOTS"
alias ".af"="cd $DROIDOTS/configs"
alias ".ab"="cd $DROIDOTS/bin"
alias ".v"="cd $DROIDOTS/configs/nvim"

function google() {
  termux-open-url "https://www.google.com/search?q=$*"
}
alias goog='google'

function updpkg() {
 local pkgs="$DROIDOTS/packages"
 command pkg list-installed | tr '/' ' ' | awk '{print $1}' >! "$pkgs"
 sed -i '1d' "$pkgs"
}

extend_path "${HOME}/perl5/bin"

if cmd_exists perl; then
  PERL5LIB="${HOME}/perl5/lib/perl5${PERL5LIB:+:${PERL5LIB}}"; export PERL5LIB;
  PERL_LOCAL_LIB_ROOT="${HOME}/perl5${PERL_LOCAL_LIB_ROOT:+:${PERL_LOCAL_LIB_ROOT}}"; export PERL_LOCAL_LIB_ROOT;
  PERL_MB_OPT="--install_base \"${HOME}/perl5\""; export PERL_MB_OPT;
  PERL_MM_OPT="INSTALL_BASE=${HOME}/perl5"; export PERL_MM_OPT;
fi

prepend_path "${DOTS}/androidots/bin"

alias fetchskull="cat ~/dots/androidots/configs/fastfetch/skull | lolcat -8 >! ~/dots/androidots/configs/fastfetch/skullcolor && cat ~/dots/androidots/configs/fastfetch/skullcolor"
