export WINROOT=/mnt/c
export WINHOME=/mnt/c/Users/njen
export WINDIR=$WINROOT/Windows

extend_path "$WINHOME/scoop/shims"
extend_path "$WINROOT/shims"
extend_path "$WINROOT/shims/pwsh"
extend_path "$WINROOT/vscode/bin"
extend_path "$WINDIR/System32/WindowsPowerShell/v1.0"
extend_path "$WINDIR/System32"
extend_path "$WINDIR"

eval "$(vfox activate zsh)"

PATH="/home/njen/perl5/bin${PATH:+:${PATH}}"; export PATH;
PERL5LIB="/home/njen/perl5/lib/perl5${PERL5LIB:+:${PERL5LIB}}"; export PERL5LIB;
PERL_LOCAL_LIB_ROOT="/home/njen/perl5${PERL_LOCAL_LIB_ROOT:+:${PERL_LOCAL_LIB_ROOT}}"; export PERL_LOCAL_LIB_ROOT;
PERL_MB_OPT="--install_base \"/home/njen/perl5\""; export PERL_MB_OPT;
PERL_MM_OPT="INSTALL_BASE=/home/njen/perl5"; export PERL_MM_OPT;

function mdat() {
  rich --text-full -y -e -d 1 -m "$@"
}

function google {
    open "https://www.google.com/search?q=$*"
}

function www {
  if [[ $1 == https://* ]]; then
    open "$1"
  else
    open "https://$1"
}
