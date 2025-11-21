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

function www() {
  [ "$#" -gt 0 ] || {
  ingit=$(command git rev-parse --is-inside-work-tree 2> /dev/null)
  if [ "$ingit" = true ]; then
    GIT_REMOTE=$(command git remote get-url origin 2> /dev/null)
    if [[ -z "$GIT_REMOTE" ]]; then
      GIT_REMOTE=$(command git ls-remote --get-url 2> /dev/null)
    fi
    GIT_REMOTE_URL=$(echo $GIT_REMOTE | sed -E "s/^https?:\\/\\/(.+@)?//; s/\\.git$//; s/\\.git$//; s/.+@(.+):([[:digit:]]+)\\/(.+)$/\\1\\/\\3/; s/.+@(.+):(.+)$/\\1\\/\\2/; s/\\/$//")
    termux-open-url "https://$GIT_REMOTE_URL"
  else
    termux-open-url "https://google.com"
  fi
  }
  if [ "$#" -gt 0 ]; then
    if [[ $1 == https://* ]]; then
      termux-open-url "$1"
    else
      termux-open-url "https://$1"
    fi
  fi
}

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
