if cmd_exists fd; then
    export FZF_DEFAULT_COMMAND='fd --type f --strip-cwd-prefix --hidden --exclude .git'
fi

if cmd_exists bat; then
     PREVIEWER='bat --style=numbers --color=always --pager=never'
   else
     PREVIEWER='cat'
fi

export FZF_DEFAULT_OPTS="--style full \
  --height 90% \
  --border sharp \
  --input-border sharp \
  --list-border sharp \
  --layout reverse \
  --info right \
  --prompt '> ' \
  --pointer '┃' \
  --marker '│' \
  --separator '──' \
  --scrollbar '│' \
  --preview-window='border-sharp' \
  --preview-window='bottom:50%'\
  --preview-label=' PREVIEW ' --color=7 \
  --border-label=' FILES ' --color=7 \
  --tabstop=2 \
  --color=16 \
  --preview '${PREVIEWER} {}'"

export FZF_DEFAULT_OPTS="$FZF_DEFAULT_OPTS --color bg+:0,bg:-1,spinner:4,hl:7:underline,fg:8,header:3,info:8,pointer:6,marker:14,fg+:6,prompt:2,hl+:10:underline,gutter:-1,selected-bg:0,separator:0,list-border:0,preview-border:8,border:8,preview-bg:-1,preview-label:0,label:7,query:13,input-border:0"

function finst() {
  fzpkgs="$(pkg list-all | tr '/' ' '  | grep -v installed | grep -v Listing | awk '{print $1}' | fzf --preview 'apt-cache show {}')"
  if [ -z "$fzpkgs" ]; then
    echo "No package selected."
  else
    pkg install -y "$fzpkgs"
  fi
};
