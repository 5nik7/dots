# shellcheck disable=SC1090,SC1091,SC2153
# Preserve existing order and only insert directories that exist.
prepath "$RUBYCOMP"
prepath "$THEMESBIN"
extpath "$HOME/.fzf/bin"
[[ ! -r $XDG_DATA_HOME/bob/env/env.sh ]] || source "$XDG_DATA_HOME/bob/env/env.sh"
prepath "$GOBIN"
extpath "$HOME/.local/share/gem/ruby/3.4.0/bin"
prepath "$HOME/.cargo/bin"
[[ -d $HOME/.local/bin ]] || command mkdir -p -- "$HOME/.local/bin"
prepath "$HOME/.local/bin"
prepath "$HOME/bin"
true
