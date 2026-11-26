open() {
  pwsh.exe -Command "Start-Process '$1' -WindowStyle Hidden -ErrorAction SilentlyContinue"
}

function zvm_config() {
  ZVM_SYSTEM_CLIPBOARD_ENABLED=true
  ZVM_CLIPBOARD_COPY_CMD='cpy'
  ZVM_CLIPBOARD_PASTE_CMD='pst'

  ZVM_OPEN_CMD='open'
  ZVM_OPEN_URL_CMD='open'
  ZVM_OPEN_FILE_CMD='nvim'
  ZVM_VI_HIGHLIGHT_FOREGROUND="${selection_foreground[hex]}"
  ZVM_VI_HIGHLIGHT_BACKGROUND="${selection_background[hex]}"
  ZVM_VI_HIGHLIGHT_EXTRASTYLE=bold

}

export WINROOT=/mnt/c
export WINHOME=/mnt/c/Users/njen
export WINDIR=$WINROOT/Windows

extpath "$WINHOME/scoop/shims"
extpath "$WINROOT/shims"
extpath "$WINROOT/shims/pwsh"
extpath "$WINROOT/vscode/bin"
extpath "$WINDIR/System32/WindowsPowerShell/v1.0"
extpath "$WINDIR/System32"
extpath "$WINDIR"

if has vfox && [[ -z ${_DOTS_TOOL_READY[vfox]:-} ]] &&
  _dots_zsh_generated vfox activate zsh && eval "$REPLY"; then
  _DOTS_TOOL_READY[vfox]=1
fi
if has bob && [[ -z ${_DOTS_TOOL_READY[bob]:-} ]] &&
  _dots_zsh_generated bob complete zsh && eval "$REPLY"; then
  _DOTS_TOOL_READY[bob]=1
fi

path=(/home/njen/perl5/bin "${(@)path:#/home/njen/perl5/bin}")
_dots_zsh_perl_environment /home/njen/perl5

spath() {
  local args="$@"

  echo "${args[@]}" | sed "s|${HOME}|~|" | sed "s|${PREFIX}|/usr|"
}

alias path='spath "$(echo -e ${PATH//:/\\n})"'

alias "p:"='spath "$(echo $PATH | tr ":"  "\n")"'

# vim: set noet ft=zsh tw=4 sw=4 ff=unix
