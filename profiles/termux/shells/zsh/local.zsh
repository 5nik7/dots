prepath "${droid[bin]}"
fpath=(${droid[bin]} $fpath)

[ -z $USER ] && export USER="$(whoami)"

export ZSH_SYSTEM_CLIPBOARD_METHOD="termux"

zvm_config() {
  ZVM_SYSTEM_CLIPBOARD_ENABLED=true
  ZVM_CLIPBOARD_COPY_CMD='termux-clipboard-set'
  ZVM_CLIPBOARD_PASTE_CMD='termux-clipboard-get'

  ZVM_OPEN_CMD='open'
  ZVM_OPEN_URL_CMD='open'
  ZVM_OPEN_FILE_CMD='nvim'
  ZVM_VI_HIGHLIGHT_FOREGROUND="${crust[hex]}"
  ZVM_VI_HIGHLIGHT_BACKGROUND="${flamingo[hex]}"
  ZVM_VI_HIGHLIGHT_EXTRASTYLE=bold

}

zinit light kutsan/zsh-system-clipboard

bindkey -M vicmd Y zsh-system-clipboard-vicmd-vi-yank-eol
bindkey "^V" zsh-system-clipboard-vicmd-vi-put-after

zvm_after_init_commands+=('[ -f ~/.fzf.zsh ] && source ~/.fzf.zsh')

export LYNX_CFG="${dot[configs]}/lynx/lynx.cfg"
export LYNX_LSS="${dot[configs]}/lynx/lynx.lss"

export TERMUX_APP_PACKAGE_MANAGER='apt'

export RISH_APPLICATION_ID="com.termux"

open() (
  termux-open "$@" >/dev/null 2>&1 &
)

alias rlt='termux-reload-settings'

alias upd="pkg update && pkg upgrade -y"

alias path='echo -e ${PATH//:/\\n}'

alias "p:"='echo $PATH | tr ":" "\n"'

spath() {
  local args="$@"

  echo "${args[@]}" | sed "s|${HOME}|~|" | sed "s|${PREFIX}|/usr|"
}

updpkg() {
  local pipkgs="$DROIDOTS/pip"
  local pkgs="$DROIDOTS/pkgs"
  local pkgs_all="$DROIDOTS/pkgs_all"
  echo "$(pkg list-installed 2>/dev/null)" | sed '1d' | tr "/" " " | awk '{print $1}' >|"$pkgs_all"
  echo "$(pkg list-installed 2>/dev/null)" | sed '1d' | grep -v automatic | cut -d '/' -f 1 >|"$pkgs"
  echo "$(pip list --format=freeze)" >|"$pipkgs"
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

# vim: set noet ft=zsh tw=4 sw=4 ff=unix
