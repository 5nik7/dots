#    _____  _____ __  ______  ______
#   /__  / / ___// / / / __ \/ ____/
#     / /  \__ \/ /_/ / /_/ / /
#  _ / /_____/ / __  / _, _/ /___
# (_)____/____/_/ /_/_/ |_|\____/

export DOTS="${HOME}/dots"
export ZSHDOT="${DOTS}/shells/zsh"
export ZFUNC="${ZSHDOT}/zfunc"
export DOTSBIN="${DOTS}/bin"
export backups="${HOME}/.backups"


function zource() {
	if [ -f "${1}" ]; then
		source "${1}"
	fi
}

function zieces() {
  zfile="${ZSHDOT}/${1}.zsh"
  if [ -f "${zfile}" ]; then
    source "${zfile}"
  fi
}

zieces "zutil"
zieces "functions"
zieces "options"
zieces "plugins"
zieces "completions"
zieces "aliases"

if is_installed fzf; then

  if cmd_exists bat; then
       CAT_PREVIEWER='bat --style=numbers --color=always --pager=never'
     else
       CAT_PREVIEWER='cat'
  fi

  export FZF_DEFAULT_OPTS="--height 60% \
--border sharp \
--layout reverse \
--info right \
--prompt ' ' \
--pointer '┃' \
--marker '│' \
--separator '──' \
--scrollbar '│' \
--preview-window='border-sharp' \
--preview-window='right:65%' \
--preview '$CAT_PREVIEWER {}'"

  source <(fzf --zsh)

  function finst() {
    fzpkgs="$(pkg list-all | tr '/' ' '  | grep -v installed | grep -v Listing | awk '{print $1}' | fzf --preview 'apt-cache show {}')"
    if [ -z "$fzpkgs" ]; then
      echo "No package selected."
    else
      pkg install -y "$fzpkgs"
    fi
  }

fi

fpath=( "${ZFUNC}" "${fpath[@]}" )

addir "${HOME}/.local/bin"
addir "${backups}"

extend_path "${HOME}/.local/bin"
extend_path "${HOME}/src/nerd-fonts/bin/scripts"

extend_path "${HOME}/.local/share/nvim/mason/bin"

prepend_path "${DOTSBIN}"

export SHHHH="${DOTS}/secrets"
zource "${SHHHH}/secrets.sh"

if is_installed zoxide; then
  eval "$(zoxide init zsh)"
  alias cd='z'
fi

if is_installed starship; then
  eval "$(starship init zsh)"
fi


if is_installed perl; then

  extend_path "${HOME}/perl5/bin"

  # PATH="/data/data/com.termux/files/home/perl5/bin${PATH:+:${PATH}}"; export PATH;
  PERL5LIB="/data/data/com.termux/files/home/perl5/lib/perl5${PERL5LIB:+:${PERL5LIB}}"; export PERL5LIB;
  PERL_LOCAL_LIB_ROOT="/data/data/com.termux/files/home/perl5${PERL_LOCAL_LIB_ROOT:+:${PERL_LOCAL_LIB_ROOT}}"; export PERL_LOCAL_LIB_ROOT;
  PERL_MB_OPT="--install_base \"/data/data/com.termux/files/home/perl5\""; export PERL_MB_OPT;
  PERL_MM_OPT="INSTALL_BASE=/data/data/com.termux/files/home/perl5"; export PERL_MM_OPT;
fi
