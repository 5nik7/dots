ZINIT_HOME="${XDG_DATA_HOME:-${HOME}/.local/share}/zinit/zinit.git"
[ ! -d $ZINIT_HOME ] && mkdir -p "$(dirname $ZINIT_HOME)"
[ ! -d $ZINIT_HOME/.git ] && git clone https://github.com/zdharma-continuum/zinit.git "$ZINIT_HOME"
source "${ZINIT_HOME}/zinit.zsh"

autoload -Uz _zinit
# (( ${+_comps} )) && _comps[zinit]=_zinit

zinit ice lucid wait blockf atpull'zinit creinstall -q .' atload"zicdreplay"
zinit light zsh-users/zsh-completions
zinit ice lucid wait
zinit light hlissner/zsh-autopair
zinit ice lucid wait atload"_zsh_autosuggest_start"
zinit light zsh-users/zsh-autosuggestions
zinit ice lucid wait
zinit light zdharma-continuum/fast-syntax-highlighting

# zinit light-mode for \
#     Aloxaf/fzf-tab \

autoload -Uz compinit
compinit -i
