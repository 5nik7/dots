function extend_path() {
	[[ -d "$1" ]] || return

	if ! echo "$PATH" | tr ":" "\n" | grep -qx "$1"; then
		export PATH="$PATH:$1"
	fi
}

function prepend_path() {
	[[ -d "$1" ]] || return

	if ! echo "$PATH" | tr ":" "\n" | grep -qx "$1"; then
		export PATH="$1:$PATH"
	fi
}

function finst() {
    fzpkgs="$(pkg list-all | tr '/' ' ' | grep -v installed | grep -v Listing | awk '{print $1}' | fzf --preview 'apt-cache show {}')"
    if [ -z "$fzpkgs" ]; then
      echo "No package selected."
    else
      pkg install -y "$fzpkgs"
    fi
  }

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

function aptget_check () {
  apt-get -s upgrade | grep -P "\d\K upgraded"
}

function finst_pac() {
    pacman -Slq | fzf -q "$1" -m --preview 'pacman -Si {1}'| xargs -ro pacman -S
}

function frm_pac() {
    pacman -Qq | fzf -q "$1" -m --preview 'pacman -Qi {1}' | xargs -ro pacman -Rns
}

function weather {
  if [[ "$1" == "help" || "$1" == "-h" || "$1" == "--help" ]]; then
    curl "wttr.in/:help"
  else
    curl "wttr.in/$1"
  fi
}

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
            $showcolor $(( row*8 + col )) $row
        done
        echo
    done
    echo

    echo 6·6·6 RGB color codes:
    for blockrow in {0..2}; do
        for red in {0..5}; do
            for blockcol in {0..1}; do
                green=$(( blockrow*2 + blockcol ))
                for blue in {0..5}; do
                    $showcolor $(( red*36 + green*6 + blue + 16 )) $green
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
            $showcolor $(( row*12 + col + 232 )) $row
        done
        echo
    done
    echo
}

function _showcolor256_fg() {
    local code=$( printf %03d $1 )
    echo -ne "\033[38;5;${code}m"
    echo -nE " $code "
    echo -ne "\033[0m"
}

function _showcolor256_bg() {
    if (( $2 % 2 == 0 )); then
        echo -ne "\033[1;37m"
    else
        echo -ne "\033[0;30m"
    fi
    local code=$( printf %03d $1 )
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
		print -nP -- "%F{$code}$code %f";
		if [ $((${code} % 16)) -eq 15 ]; then
			echo ""
		fi
	done
}


# function cd() {
# 	builtin cd "$@" && ls_eza
# }

function fixpath() {
	PATH=$(echo $(sed 's/:/\n/g' <<<$PATH | sort | uniq) | sed -e 's/\s/':'/g')
}

function cleanvim() {
	rm -rvf ~/.config/nvim
	rm -rvf ~/.local/share/nvim
	rm -rvf ~/.local/state/nvim
	rm -rvf ~/.cache/nvim
}

function ssl-download-certificate {
  local host=$1
  local port=${2:-443}
  openssl s_client -showcerts -connect "${host}:${port}" </dev/null 2>/dev/null | openssl 'x509' -outform 'PEM' > "${host}:${port}.pem"
}

function ssh-key-set {
   ssh-add -D
   ssh-add "$HOME/.ssh/${1:-id_rsa}"
}

function ssh-key-info {
   ssh-keygen -l -f "$HOME/.ssh/${1:-id_rsa}"
}

function fzf-history() {
  RBUFFER="$(history -n 0 | fzf)"
}
zle -N fzf-history fzf-history

function prepend-sudo {
  if [[ $BUFFER != "sudo "* ]]; then
    BUFFER="sudo $BUFFER"; CURSOR+=5
  fi
}
zle -N prepend-sudo
bindkey -M vicmd s prepend-sudo

function _smooth_fzf() {
  local fname
  local current_dir="$PWD"
  cd "${XDG_CONFIG_HOME:-~/.config}"
  fname="$(fzf)" || return
  $EDITOR "$fname"
  cd "$current_dir"
}
