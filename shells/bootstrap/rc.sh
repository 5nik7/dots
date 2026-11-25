# Standalone Bash/Zsh entry. The installed cold-path helper survives checkout removal.
_dots_rc_root=${DOTS_BOOTSTRAP_DIR:-"$HOME/dots"}
if [[ -n ${ZSH_VERSION:-} ]]; then
    _dots_rc_shell=zsh
    _dots_rc_cli=${commands[dots]-}
else
    _dots_rc_shell=bash
    _dots_rc_cli=$(type -P dots) || _dots_rc_cli=
fi
if [[ -z ${DOTS_BOOTSTRAP_DIR:-} && ! $_dots_rc_cli -ef $_dots_rc_root/bin/dots &&
      -f $HOME/.local/share/dots/bootstrap/checkout && -r $HOME/.local/share/dots/bootstrap/checkout ]]; then
    IFS= read -r _dots_rc_pin < "$HOME/.local/share/dots/bootstrap/checkout" || :
    [[ -z $_dots_rc_pin ]] || _dots_rc_root=$_dots_rc_pin
fi
if [[ $_dots_rc_root != /* || ! -f $_dots_rc_root/bin/dots || ! -x $_dots_rc_root/bin/dots ||
      ! -r $_dots_rc_root/lib/dots/shell/startup.bash || ! -r $_dots_rc_root/shells/$_dots_rc_shell/init.$_dots_rc_shell ||
      ( -z ${DOTS_BOOTSTRAP_DIR:-} && -n $_dots_rc_cli && ! $_dots_rc_cli -ef $_dots_rc_root/bin/dots ) ]]; then
    _dots_rc_mode=offline
    [[ $- != *i* ]] || _dots_rc_mode=interactive
    _dots_rc_root=$(command sh "$HOME/.local/share/dots/bootstrap/locate.sh" "$_dots_rc_mode" "$_dots_rc_shell") || _dots_rc_root=
fi
if [[ -n $_dots_rc_root && -r $_dots_rc_root/shells/$_dots_rc_shell/init.$_dots_rc_shell ]]; then
    source "$_dots_rc_root/shells/$_dots_rc_shell/init.$_dots_rc_shell"
fi
unset _dots_rc_root _dots_rc_shell _dots_rc_cli _dots_rc_mode _dots_rc_pin
