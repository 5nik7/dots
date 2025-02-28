if cmd_exists fd; then
  export FZF_DEFAULT_COMMAND='fd --type f --strip-cwd-prefix --hidden --exclude .git'
fi

if cmd_exists bat; then
   CAT_PREVIEWER='bat --style=numbers --color=always --pager=never'
else
   CAT_PREVIEWER='cat'
fi

FZF_COLORS="bg+:0,\
bg:-1,\
spinner:4,\
hl:12,\
fg:8,\
header:3,\
info:8,\
pointer:13,\
marker:14,\
fg+:13,\
prompt:2,\
hl+:10,\
gutter:-1,\
selected-bg:0,\
separator:0,\
preview-border:8,\
border:8,\
preview-bg:-1,\
preview-label:0,\
label:7,\
query:13,\
input-border:4"

export FZF_DEFAULT_OPTS="--height 60% \
--border sharp \
--layout reverse \
--info right \
--color '$FZF_COLORS' \
--prompt ' ' \
--pointer '┃' \
--marker '│' \
--separator '──' \
--scrollbar '│' \
--preview-window='border-sharp' \
--preview-window='right:65%' \
--preview '$CAT_PREVIEWER {}'"

function finst() {
 local fzpkgs="$(pkg list-all | tr '/' ' '  | grep -v installed | grep -v Listing | awk '{print $1}' | fzf --preview 'apt-cache show {}')"
 if [ -z "$fzpkgs" ]; then
   echo "No package selected."
 else
   pkg install -y "$fzpkgs"
 fi
}

source <(fzf --zsh)
