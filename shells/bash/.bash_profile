if [[ -r $HOME/.profile ]]; then
    source "$HOME/.profile"
    if [[ -n ${DOTS:-} && $HOME/.profile -ef $DOTS/shells/profile ]]; then
        _dots_login_common=$DOTS/bin/lib/common.sh
    fi
fi
[[ ! -r $HOME/.bashrc ]] || source "$HOME/.bashrc"
unset _dots_login_common
