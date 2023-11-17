#!/usr/bin/zsh

GRAY="\033[0;30m"
WHITE="\033[0;37m"
RED="\033[0;31m"
GREEN="\033[0;32m"
BLUE="\033[0;34m"
YELLOW="\033[0;33m"
CYAN="\033[0;36m"
PURPLE="\033[0;35m"
GRAYB="\033[1;30m"
WHITEB="\033[1;37m"
REDB="\033[1;31m"
BLUEB="\033[1;34m"
GREENB="\033[1;32m"
YELLOWB="\033[1;33m"
CYANB="\033[1;36m"
PURPLEB="\033[1;35m"

function linetest() {
    line
    thickline
    doubleline
    dashline
    dotline
    texture
}

function line() {
	echo -e "${GRAY}󰍴󰍴󰍴󰍴󰍴󰍴󰍴󰍴󰍴󰍴󰍴󰍴󰍴󰍴󰍴󰍴󰍴󰍴󰍴󰍴󰍴󰍴󰍴󰍴󰍴󰍴󰍴󰍴󰍴󰍴󰍴󰍴󰍴󰍴󰍴󰍴${NC}"
}

function thickline() {
	echo -e "${GRAY}${NC}"
}

function doubleline() {
	echo -e "${GRAY}═══════════════════════════════════${NC}"
}

function dashline() {
	echo -e "${GRAY}${NC}"
}

function dotline() {
	echo -e "${GRAY}${NC}"
}

function texture() {
	echo -e "\e[1;30m${GRAY}󰔌󰔌󰔌󰔌󰔌󰔌󰔌󰔌󰔌󰔌󰔌󰔌󰔌󰔌󰔌󰔌󰔌󰔌󰔌󰔌󰔌󰔌󰔌󰔌󰔌󰔌󰔌󰔌󰔌󰔌󰔌󰔌󰔌󰔌󰔌󰔌󰔌󰔌󰔌󰔌󰔌󰔌󰔌󰔌󰔌󰔌󰔌󰔌󰔌󰔌󰔌󰔌󰔌󰔌󰔌󰔌󰔌󰔌${NC}"
}

function cecho(){
    printf "${(P)1}${2} ${NC}\n" # <-- zsh
    # printf "${!1}${2} ${NC}\n" # <-- bash
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

function createdir() {
	if [ ! -d "$1" ]; then
		print_info "Created $1"
		mkdir -p "$1"
	fi
}

function take() {
	if [ ! -d "$2" ]; then
		print_info "Cloning github.com/$1 to $2"
		git clone "https://github.com/$1.git" "$2"
	fi
}

function symlink() {
	if [ ! -e "$2" ]; then
		ln -s "$1" "$2"
		printf '    \n%s 󰜴 %s\n' "$1" "$2"
	else
		print_warning "$2 already exists"
	fi
}

function backup() {
	if [ -f "$1" ]; then
		mv -f "$1" "${1}.bak"
		printf '    \nCreating backup for %s\n' "$1"	
	else
		print_warning "$2 not found"
	fi
}

function is_installed() {
	dpkg -s "$1" &>/dev/null
	return $?
}

function installpkg() {
  if ! is_installed "$1"; then
			sudo nala install "$1" -y
		else
			printf '    \n%s is already installed.\n' "$1"
		fi
}

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