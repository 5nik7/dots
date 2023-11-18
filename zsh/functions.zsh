#!/usr/bin/zsh

ORANGE="\033[38;5;216m"
PURPLE="\033[38;5;140m"
GRAY="\033[0;30m"
WHITE="\033[0;37m"
RED="\033[0;31m"
GREEN="\033[0;32m"
BLUE="\033[0;34m"
YELLOW="\033[0;33m"
CYAN="\033[0;36m"
PINK="\033[0;35m"
GRAYB="\033[1;30m"
WHITEB="\033[1;37m"
REDB="\033[1;31m"
BLUEB="\033[1;34m"
GREENB="\033[1;32m"
YELLOWB="\033[1;33m"
CYANB="\033[1;36m"
PINKB="\033[1;35m"

NC="\033[0m"

HEADER="${GREENB}"
LINECOLOR="${GRAYB}"
PANELBG="\033[48;5;233m"
solsymble="┊" 

function cecho(){
    printf "${(P)1}${2} ${NC}\n"
}

function print_default() {
	echo -e "$*"
}

function print_info() {
	echo -e "\e[1;36m$*\e[m" # cyan
}

function print_notice() {
	echo -e "\e[1;35m$*\e[m" # magenta
}

function print_success() {
	echo -e "\e[1;32m$*\e[m" # green
}

function print_warning() {
	echo -e "\e[1;33m$*\e[m" # yellow
}

function print_error() {
	echo -e "\e[1;31m$*\e[m" # red
}

function print_debug() {
	echo -e "\e[1;34m$*\e[m" # blue
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

function ls_eza() {
	echo -e ""
	eza -lA --icons --git-repos --git --group-directories-first --no-filesize --no-user --no-time
}

function ll_eza() {
	echo -e ""
	eza -lA --icons --git-repos --git --group-directories-first
}

function cd() {
	builtin cd "$@" && ls_eza
}

function extend_path() {
    [[ -d "$1" ]] || return

    if ! echo "$PATH" | tr ":" "\n" | grep -qx "$1"; then
	    export PATH="$1:$PATH"
    fi
}

function source_path() {
	if [ -f "$1" ]; then
		source "$1"
	fi
}

function fixpath() {
	PATH=$(echo $(sed 's/:/\n/g' <<<$PATH | sort | uniq) | sed -e 's/\s/':'/g')
}


function createdir() {
	if [ ! -d "$1" ]; then
		mkdir -p "$1"
		echo -e "${LINECOLOR}${solsymble}${NC} ${BLUE}Created${NC} ${CYANB}$1${NC}"
	fi
}

function take() {
	if [ ! -d "$2" ]; then
		git clone "https://github.com/$1.git" "$2"
		echo -e "${LINECOLOR}${solsymble}${NC} ${PURPLE}Github.com/${NC}${PINKB}$1 ${GRAY}->${NC} ${CYANB}$2${NC}"
	fi
}

function symlink() {
	root=$(echo "$1" | cut -d "/" -f 1)
	if [ ! -e "$2" ]; then
		ln -s "$1" "$2"
		echo -e "${LINECOLOR}${solsymble}${NC}   ${BLUE}$1${NC} ${GRAY}->${NC} ${CYANB}$2${NC}"
	else
		echo -e "${LINECOLOR}${solsymble}${NC}   ${GRAYB}$2${NC} ${GRAY}already exists${NC}"
	fi
}

function backup() {
	if [ -f "$1" ]; then
		mv -f "$1" "${1}.bak"
		echo -e "${LINECOLOR}${solsymble}${NC}   ${ORANGE}$1${NC} ${GRAY}->${NC} ${YELLOWB}$1.bak${NC}"
	else
		echo -e "${LINECOLOR}${solsymble}${NC}   ${PINKB}$1${NC} ${PINK}does not exist${NC}"
	fi
}

function is_installed() {
	dpkg -s "$1" &>/dev/null
	return $?
}

function installpkg() {
  if ! is_installed "$1"; then
			sudo apt -qq install "$1" -y
			echo -e "${LINECOLOR}${solsymble}${NC}   ${CYANB}$1${NC} ${BREENB}installed${NC}"
		else
			echo -e "${LINECOLOR}${solsymble}${NC}   ${GRAYB}$1${NC} ${GRAY}already installed${NC}"
		fi
}
alias pkg="installpkg"

function cleanvim() {
	rm -rf ~/.config/nvim
	rm -rf ~/.local/share/nvim
	rm -rf ~/.local/state/nvim
	rm -rf ~/.cache/nvim
}

function ssh-key-set {
   ssh-add -D
   ssh-add "$HOME/.ssh/${1:-id_rsa}"
}

function ssh-key-info {
   ssh-keygen -l -f "$HOME/.ssh/${1:-id_rsa}"
}

function history-all() {
	history -E 1
}

function prepend-sudo {
  if [[ $BUFFER != "sudo "* ]]; then
    BUFFER="sudo $BUFFER"; CURSOR+=5
  fi
}

function _smooth_fzf() {
  local fname
  local current_dir="$PWD"
  cd "${XDG_CONFIG_HOME:-~/.config}"
  fname="$(fzf)" || return
  $EDITOR "$fname"
  cd "$current_dir"
}

# vim:ft=zsh:nowrap