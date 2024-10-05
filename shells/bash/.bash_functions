function gup() {
  if [ -d .git ]; then
  commitDate=$(date +"%m-%d-%Y %H:%M")
    echo -e ""
    git add .
    git commit -m "Update @ $commitDate"
    git push
    echo -e ""
  else 
    echo -e "This directory does not contain a .git directory"
  fi
}

function dd {
    if [ -z "$1" ]; then
        explorer.exe .
    else
        explorer.exe "$1"
    fi
}

# function cd() {
#   builtin cd "$@" && eza -xa --icons --group-directories-first
# }
#
function google {
    open "https://www.google.com/search?q=$*"
}

function femoji() {
    emojis=$(curl -sSL 'https://git.io/JXXO7')
    selected_emoji=$(echo $emojis | fzf)
    echo $selected_emoji
}

# ex - archive extractor
function ex() {
    if [ -f "$1" ]; then
        case $1 in
        *.tar.bz2) tar xjf "$1" ;;
        *.tar.gz) tar xzf "$1" ;;
        *.bz2) bunzip2 "$1" ;;
        *.rar) unrar x "$1" ;;
        *.gz) gunzip "$1" ;;
        *.tar) tar xf "$1" ;;
        *.tbz2) tar xjf "$1" ;;
        *.tgz) tar xzf "$1" ;;
        *.zip) unzip "$1" ;;
        *.Z) uncompress "$1" ;;
        *.7z) 7z x "$1" ;;
        *) echo "'$1' cannot be extracted via ex()" ;;
        esac
    else
        echo "'$1' is not a valid file"
    fi
}
