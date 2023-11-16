function cd() {
	builtin cd "$@" && eza -lA --icons --git-repos --git --group-directories-first --no-filesize --no-user --no-time
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
		info "Creating $1"
		mkdir -p "$1"
	fi
}

function take() {
	if [ ! -d "$2" ]; then
		info "Cloning github.com/$1 to $2"
		git clone "https://github.com/$1.git" "$2"
	fi
}

function link_bin() {
	if [ ! -e "$HOME/.local/bin/$2" ]; then
			ln -s $(which $1) $HOME/.local/bin/$2
	fi
}

function symlink() {
	if [ -e "$2" ]; then
		mv -frv "$2" "$2.bak"
	fi
	ln -s "$1" "$2"
	printf '    %s 󰜴 %s\n' "$1" "$2"
}

function is_installed() {
	dpkg -s "$1" &>/dev/null
	return $?
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

### echo ###
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

function 256color() {
	for code in {000..255}; do
		print -nP -- "%F{$code}$code %f";
		if [ $((${code} % 16)) -eq 15 ]; then
			echo ""
		fi
	done
}

function prepend-sudo {
  if [[ $BUFFER != "sudo "* ]]; then
    BUFFER="sudo $BUFFER"; CURSOR+=5
  fi
}