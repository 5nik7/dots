function gitcheck() {
  if mygit; then
    local changed=$(git status -s | grep -E '^\s*??\s' | awk '{print $2}')
    if [[ -n "$changed" ]]; then
      return 0
    else
      return 1
    fi
  fi
}

function gitmodified() {
  if mygit; then
    git status -s | grep -E '^\s*M\s' | awk '{print $2}'
  fi
}

function gitdeleted() {
  if mygit; then
    git status -s | grep -E '^\s*D\s' | awk '{print $2}'
  fi
}

function gup() {
  local ts=$(date +"%m-%d-%Y %H:%M")
  local cwd=$PWD
  local branchico=''
  local gitico=''
  local gitmodified gitdeleted ico repo root subdirs subrepo subbranch out
  if mygit; then
    local ico=$(git-it -i)
    local repo=$(git-it -r)
    local branch=$(git branch | awk '{print $2}')
    local root=$(git rev-parse --show-toplevel)
    local subdirs=($(git submodule --quiet foreach 'git rev-parse --show-toplevel'))
    gitmodified=$(gitmodified)
    gitdeleted=$(gitdeleted)
    if [[ "$root" != "$cwd" ]]; then
      cd "$root"
    fi
    for subdir in "${subdirs[@]}"; do
      if [[ -d "$subdir" ]]; then
        cd "$subdir"
        if mygit && gitcheck; then
          local subrepo=$(gitsub -f '%B')
          local subbranch=$(git branch | awk '{print $2}')
          echo
          printf "${SUBTEXT}%s ${SKY}%s ${SKY}${BOLD}%s${RST} ${MAUVE}%s${RST}\n" "submodule:" "$ico" "$subrepo" "$branchico$subbranch" | box -hp 1 -bc "${DIM}${SAPPHIRE}" -t "UPDATE" -tc "${SAPPHIRE}"
          git add . && git commit -m "Update @ $ts" && git push
        fi
      fi
    done
    cd "$root"
    if gitcheck; then
      echo
      printf "${SUBTEXT} %s ${SKY}%s ${SKY}${BOLD}%s${RST} ${MAUVE}%s${RST}\n" "repo:" "$ico" "$repo" "$branchico$branch" | box -hp 1 -bc "${DIM}${SAPPHIRE}" -t "UPDATE" -tc "${SAPPHIRE}"
      git add . && git commit -m "Update @ $ts" && git push
      if [[ "$root" != "$cwd" ]]; then
        cd "$cwd"
      fi
    else
      printf "${YELLOW}%s '${BRIGHTYELLOW}${BOLD}%s${RST}${YELLOW}' %s${RST}\n" "$ico" "$repo" "nothing to commit."
    fi
  else
    out=$(pathout $cwd)
    printf "${RED} %s '${BRIGHTRED}${BOLD}%s${RST}${RED}' %s${RST}\n" "$gitico" "$out" "not a repo."
  fi
}

function aptget_check() {
  apt-get -s upgrade | grep -P "\d\K upgraded"
}

function fzpi() {
  pacman -Slq | fzf -q "$1" -m --preview 'pacman -Si {1}' | xargs -ro pacman -S
}

function fzpr() {
  pacman -Qq | fzf -q "$1" -m --preview 'pacman -Qi {1}' | xargs -ro pacman -Rns
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

function showcolors256() {
  local row col blockrow blockcol red green blue
  local showcolor=_showcolor256_${1:-bg}
  local white="\033[1;37m"
  local reset="\033[0m"

  echo -e "Set foreground color: \\\\033[38;5;${white}NNN${reset}m"
  echo -e "Set background color: \\\\033[48;5;${white}NNN${reset}m"
  echo -e "Reset color & style:  \\\\033[0m"
  echo

  echo 16 standard color codes:
  for row in {0..1}; do
    for col in {0..7}; do
      $showcolor $((row * 8 + col)) $row
    done
    echo
  done
  echo

  echo 6·6·6 RGB color codes:
  for blockrow in {0..2}; do
    for red in {0..5}; do
      for blockcol in {0..1}; do
        green=$((blockrow * 2 + blockcol))
        for blue in {0..5}; do
          $showcolor $((red * 36 + green * 6 + blue + 16)) $green
        done
        echo -n "  "
      done
      echo
    done
    echo
  done

  echo 24 grayscale color codes:
  for row in {0..1}; do
    for col in {0..11}; do
      $showcolor $((row * 12 + col + 232)) $row
    done
    echo
  done
  echo
}

function _showcolor256_fg() {
  local code=$(printf %03d $1)
  echo -ne "\033[38;5;${code}m"
  echo -nE " $code "
  echo -ne "\033[0m"
}

function _showcolor256_bg() {
  if (($2 % 2 == 0)); then
    echo -ne "\033[1;37m"
  else
    echo -ne "\033[0;30m"
  fi
  local code=$(printf %03d $1)
  echo -ne "\033[48;5;${code}m"
  echo -nE " $code "
  echo -ne "\033[0m"
}

function showcolors16() {
  _showcolor "\033[0;30m" "\033[1;30m" "\033[40m" "\033[100m"
  _showcolor "\033[0;31m" "\033[1;31m" "\033[41m" "\033[101m"
  _showcolor "\033[0;32m" "\033[1;32m" "\033[42m" "\033[102m"
  _showcolor "\033[0;33m" "\033[1;33m" "\033[43m" "\033[103m"
  _showcolor "\033[0;34m" "\033[1;34m" "\033[44m" "\033[104m"
  _showcolor "\033[0;35m" "\033[1;35m" "\033[45m" "\033[105m"
  _showcolor "\033[0;36m" "\033[1;36m" "\033[46m" "\033[106m"
  _showcolor "\033[0;37m" "\033[1;37m" "\033[47m" "\033[107m"
}

function _showcolor() {
  for code in $@; do
    echo -ne "$code"
    echo -nE "   $code"
    echo -ne "   \033[0m  "
  done
  echo
}

function 256color() {
  for code in {000..255}; do
    print -nP -- "%F{$code}$code %f"
    if [ $((${code} % 16)) -eq 15 ]; then
      echo ""
    fi
  done
}

function fixpath() {
  PATH=$(echo $(sed 's/:/\n/g' <<<$PATH | sort | uniq) | sed -e 's/\s/':'/g')
}

function cleanvim() {
  mv ~/.config/nvim{,.bak}
  mv ~/.local/share/nvim{,.bak}
  mv ~/.local/state/nvim{,.bak}
  mv ~/.cache/nvim{,.bak}
}

function ssl-download-certificate {
  local host=$1
  local port=${2:-443}
  openssl s_client -showcerts -connect "${host}:${port}" </dev/null 2>/dev/null | openssl 'x509' -outform 'PEM' >"${host}:${port}.pem"
}

function ssh-key-set {
  ssh-add -D
  ssh-add "$HOME/.ssh/${1:-id_rsa}"
}

function ssh-key-info {
  ssh-keygen -l -f "$HOME/.ssh/${1:-id_rsa}"
}

function prepend-sudo {
  if [[ $BUFFER != "sudo "* ]]; then
    BUFFER="sudo $BUFFER"
    CURSOR+=5
  fi
}
zle -N prepend-sudo
bindkey -M vicmd s prepend-sudo

function fname() {
  basename "$@" | sed 's/\(.*\)\..*/\1/'
}

function fext() {
  filename=$(basename "$@")
  echo "${filename##*.}"
}

function dat() {
  rich --text-full -y -e -d 1 -m "$@"
}
