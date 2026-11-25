[ -z $USER ] && export USER="$(whoami)"

export ZSH_SYSTEM_CLIPBOARD_METHOD="termux"

zvm_config() {
  ZVM_SYSTEM_CLIPBOARD_ENABLED=true
  ZVM_CLIPBOARD_COPY_CMD='termux-clipboard-set'
  ZVM_CLIPBOARD_PASTE_CMD='termux-clipboard-get'

  ZVM_OPEN_CMD='termux-open'
  ZVM_OPEN_URL_CMD='termux-open-url'
  ZVM_OPEN_FILE_CMD='nvim'
  ZVM_VI_HIGHLIGHT_FOREGROUND="${selection_foreground[hex]}"
  ZVM_VI_HIGHLIGHT_BACKGROUND="${selection_background[hex]}"
  ZVM_VI_HIGHLIGHT_EXTRASTYLE=bold

}

# Bindings and vi-mode lifecycle callbacks are owned by shells/zsh/keys.zsh.
_dots_termux_editor_plugins() {
  _dots_default_plugin jeffreytse/zsh-vi-mode depth=1
  _dots_default_plugin kutsan/zsh-system-clipboard
}
_dots_termux_editor_plugins

export LYNX_CFG="${dot[configs]}/lynx/lynx.cfg"
export LYNX_LSS="${dot[configs]}/lynx/lynx.lss"

export TERMUX_APP_PACKAGE_MANAGER='apt'

export RISH_APPLICATION_ID="com.termux"

open() (
  termux-open "$@" >/dev/null 2>&1 &
)

spath() {
  local args="$@"

  echo "${args[@]}" | sed "s|${HOME}|~|" | sed "s|${PREFIX}|/usr|"
}

alias rlt='termux-reload-settings'

alias upd="pkg update && pkg upgrade -y"

alias path='spath "$(echo -e ${PATH//:/\\n})"'

alias "p:"='spath "$(echo $PATH | tr ":"  "\n")"'

updpkg() {
  local pipkgs="$DOTSTERMUX/pip"
  local pkgs="$DOTSTERMUX/pkgs"
  local pkgs_all="$DOTSTERMUX/pkgs_all"
  echo "$(pkg list-installed 2>/dev/null)" | sed '1d' | tr "/" " " | awk '{print $1}' >|"$pkgs_all"
  echo "$(pkg list-installed 2>/dev/null)" | sed '1d' | grep -v automatic | cut -d '/' -f 1 >|"$pkgs"
  echo "$(pip list --format=freeze)" >|"$pipkgs"
}

extpath "${HOME}/perl5/bin"

if has perl; then _dots_zsh_perl_environment "$HOME/perl5"; fi

# vim: set noet ft=zsh tw=4 sw=4 ff=unix
