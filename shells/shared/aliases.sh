# Shared interactive aliases. The function loader handles alias-safe definitions.
# Remove the old Bash function forms and our capability-dependent aliases first.
unset -f l ll la lla lt lta ff 2>/dev/null || :
unalias eff ls eza l ll la lla lt lta lsa cd d lg glow paint dev src repos pacman upd paci pacr apt apti aptr 2>/dev/null || :
alias rl=rlp rlc=reload-completion rlcs=reload-completions
alias c=clear q=exit h=history g=git
alias t='tmux attach || tmux new -s Work'
alias gcm='git commit -m' gcam='git commit -a -m' gcad='git commit -a --amend'
alias 'p:'='printf "%s\n" "${PATH//:/$'"'\n'"'}"'
alias path='printf "%s\n" "${PATH//:/$'"'\n'"'}"'
alias rmr='rm -fvr' d8="date '+%-I:%M %p'" get=httpGet
alias decompress='tar -xzf' color_codes=palette
alias ..='cd ..' ...='cd ../..' ....='cd ../../..' .....='cd ../../../..'
alias ......='cd ../../../../..' .......='cd ../../../../../..' ........='cd ../../../../../../..'
alias docs='cd -- "$DOCS"' notes='cd -- "$NOTES"'
alias .c='cd -- "$HOME/.config"' .l='cd -- "$HOME/.local"'
alias .lb='cd -- "$HOME/.local/bin"' .lsh='cd -- "$HOME/.local/share"' .lst='cd -- "$HOME/.local/state"'
alias .d='cd -- "$DOTS"' .df='cd -- "$DOTFILES"' .f='cd -- "$DOTFILES"'
alias .b='cd -- "$DOTBIN"' .s='cd -- "$SHELLS"' .sc='cd -- "$DOTSCRIPTS"'
alias .sz='cd -- "$SHELLS/zsh"' .sb='cd -- "$SHELLS/bash"' .sp='cd -- "$SHELLS/powershell"'
alias .t='cd -- "$DOTHEMES"' .tb='cd -- "$THEMESBIN"'
alias updrbenv='git -C "$(rbenv root)/plugins/ruby-build" pull'
alias sc=script/console sg=script/generate sd=script/destroy
if has eza; then
  alias l='eza --no-user --no-filesize --no-time --no-permissions --group-directories-first --git --git-repos --icons=auto'
  alias ls='eza -lh --no-user --no-filesize --no-time --no-permissions --group-directories-first --git --git-repos --icons=auto'
  alias ll='eza -lh --group-directories-first --git --git-repos --icons=auto'
  alias lt='eza --tree --level=2 --long --icons --git --git-repos --no-filesize --no-time --no-permissions --no-user'
else
  alias l=ls ll='ls -la' lt='ls -R'
fi
alias lsa='ls -a' la=lsa lla='ll -a' lta='lt -a'
# Match the final effective Zsh binding, after native zoxide activation.
if has zoxide && typeset -f z >/dev/null 2>&1; then alias cd=z; fi
if has yazi; then alias d=y; fi
if has lazygit; then alias lg=lazygit; fi
alias edit='$EDITOR' e='$EDITOR' v='$EDITOR' vi='$EDITOR' vim='$EDITOR' sv='sudo "$EDITOR"'
alias ff=_dots_file_picker
if [[ -d $HOME/repos ]]; then export REPOS="$HOME/repos"; alias repos='cd -- "$REPOS"'; fi
if [[ -d $HOME/dev ]]; then export DEV="$HOME/dev"; alias dev='cd -- "$DEV"'; fi
if [[ -d $HOME/src ]]; then export SRCDIR="$HOME/src"; alias src='cd -- "$SRCDIR"'; fi
if has pastel; then alias paint='pastel paint'; else alias paint=_dots_paint; fi
if has glow && [[ -f $DOTFILES/glow/styles/catppuccin-mocha.json ]]; then
  alias glow='glow -s "$DOTFILES/glow/styles/catppuccin-mocha.json"'
fi
if [[ ${distro:-} == arch ]]; then
  alias pacman='sudo pacman' upd='sudo pacman -Syu --noconfirm' paci='sudo pacman -S' pacr='sudo pacman -R'
elif [[ ${distro:-} == ubuntu || ${distro:-} == debian ]]; then
  alias apt='sudo apt' upd='sudo apt update && sudo apt upgrade -y' apti='sudo apt install' aptr='sudo apt remove'
fi
