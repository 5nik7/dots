# Configure and load plugins using Zinit's
ZINIT_HOME="${ZINIT_HOME:-${XDG_DATA_HOME:-${HOME}/.local/share}/zinit}"

# Added by Zinit's installer
if [[ ! -f ${ZINIT_HOME}/zinit.git/zinit.zsh ]]; then
    print -P "%F{14}Installing ZSH plugin manager %F{13}(zinit)%f"
    command mkdir -p "${ZINIT_HOME}" && command chmod g-rwX "${ZINIT_HOME}"
    command git clone https://github.com/zdharma-continuum/zinit.git "${ZINIT_HOME}/zinit.git" && \
        print -P "%F{10}Installation successful.%f%b" || \
        print -P "%F{9}The clone has failed.%f%b"
fi

source "${ZINIT_HOME}/zinit.git/zinit.zsh"

autoload -Uz _zinit
(( ${+_comps} )) && _comps[zinit]=_zinit

zinit ice wait="0" lucid from="gh-r" as="program" pick="zoxide-*/zoxide -> zoxide" cp="zoxide-*/completions/_zoxide -> _zoxide" atclone="./zoxide init zsh > init.zsh" atpull="%atclone" src="init.zsh"
zinit light ajeetdsouza/zoxide

zinit ice wait"0a" atinit"ZINIT[COMPINIT_OPTS]=-C; zpcompinit; zpcdreplay" atload"_zsh_highlight" lucid
zinit light zdharma-continuum/fast-syntax-highlighting

zinit ice wait"0a" compile'{src/*.zsh,src/strategies/*}' atinit"ZSH_AUTOSUGGEST_USE_ASYNC=1" atload"_zsh_autosuggest_start" lucid
zinit light zsh-users/zsh-autosuggestions

zinit ice wait"0b" lucid
zinit light hlissner/zsh-autopair

zinit ice wait"0b" blockf lucid
zinit light zsh-users/zsh-completions

zinit light chrissicool/zsh-256color
zinit light mafredri/zsh-async
zinit ice depth"1"

zinit ice wait="1" lucid
zinit light Aloxaf/fzf-tab

zinit ice wait'3' lucid from="gh-r" as="program" bpick='*.deb' pick="usr/bin/btm"
zinit light ClementTsang/bottom