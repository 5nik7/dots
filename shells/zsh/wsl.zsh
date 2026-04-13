function zvm_config() {
  ZVM_SYSTEM_CLIPBOARD_ENABLED=true
  ZVM_CLIPBOARD_COPY_CMD='cpy'
  ZVM_CLIPBOARD_PASTE_CMD='cmd'

  ZVM_OPEN_CMD='open'
  ZVM_OPEN_URL_CMD='open-url'
  ZVM_OPEN_FILE_CMD='nvim'
  ZVM_VI_HIGHLIGHT_FOREGROUND="$crust"
  ZVM_VI_HIGHLIGHT_BACKGROUND="$flamingo"
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

has vfox && eval "$(vfox activate zsh)"



PATH="/home/njen/perl5/bin${PATH:+:${PATH}}"
export PATH
PERL5LIB="/home/njen/perl5/lib/perl5${PERL5LIB:+:${PERL5LIB}}"
export PERL5LIB
PERL_LOCAL_LIB_ROOT="/home/njen/perl5${PERL_LOCAL_LIB_ROOT:+:${PERL_LOCAL_LIB_ROOT}}"
export PERL_LOCAL_LIB_ROOT
PERL_MB_OPT="--install_base \"/home/njen/perl5\""
export PERL_MB_OPT
PERL_MM_OPT="INSTALL_BASE=/home/njen/perl5"
export PERL_MM_OPT

function open() {
  pwsh.exe -Command "Start-Process '$1' -WindowStyle Hidden -ErrorAction SilentlyContinue"
}
