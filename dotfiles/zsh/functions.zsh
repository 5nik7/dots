function walbg() {
    wal -n -i "$@"
    swaybg -i "$(< "${HOME}/.cache/wal/wal")"
}

function weather {
    if [[ "$1" == "help" ]]; then
        curl "wttr.in/:help"
    else
        curl "wttr.in/Yakima?uFQ$1"
    fi
}

function femoji() {
    emojis=$(curl -sSL 'https://git.io/JXXO7')
    selected_emoji=$(echo $emojis | fzf)
    echo $selected_emoji
}


function in() {
    yay -Slq | fzf -q "$1" -m --preview 'yay -Si {1}'| xargs -ro yay -S
}

function re() {
    yay -Qq | fzf -q "$1" -m --preview 'yay -Qi {1}' | xargs -ro yay -Rns
}

# function man {
#   LESS_TERMCAP_md=$(printf "${fg_bold[green]}") \
#   LESS_TERMCAP_us=$(printf "${fg[cyan]}") \
#   LESS_TERMCAP_ue=$(printf "$reset_color") \
#   PAGER="${commands[less]:-$PAGER}" \
#   _NROFF_U=1 \
#      command man "$@"
# }

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
	eza -lA --icons --git-repos --git --group-directories-first --no-filesize --no-user --no-time --no-permissions
}

function ll_eza() {
	echo -e ""
	eza -lA --icons --git-repos --git --group-directories-first
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

function rel_path() {
    echo "$1" | sed "s|^$HOME/|~/|"
}

function fold1() {
    echo $(basename "$1")
}

function fold2() {
    echo $(basename "$(dirname "$1")")/$(basename "$1")
}

function fold3() {
    echo $(basename "$(dirname "$(dirname "$1")")")/$(basename "$(dirname "$1")")/$(basename "$1")
}

# mkcd is equivalent to takedir
function mkcd takedir() {
    mkdir -p $@ && cd ''${@:$#}
}

function takeurl() {
    local data thedir
    data="$(mktemp)"
    curl -L "$1" > "$data"
    tar xf "$data"
    thedir="$(tar tf "$data" | head -n 1)"
    rm "$data"
    cd "$thedir"
}

function takegit() {
    git clone "$1"
    cd "$(basename ''${1%%.git})"
}

function take() {
    if [[ $1 =~ ^(https?|ftp).*\.(tar\.(gz|bz2|xz)|tgz)$ ]]; then
        takeurl "$1"
    elif [[ $1 =~ ^([A-Za-z0-9]\+@|https?|git|ssh|ftps?|rsync).*\.git/?$ ]]; then
        takegit "$1"
    else
        takedir "$@"
    fi
}

function gitclo() {
    git clone "$@"
    local param
    local last_arg
    for param; do
        if [[ $param != -* ]]; then
            last_arg="$param"
        fi
    done
    clone_dir=$(basename $last_arg .git)
    cd $clone_dir;
}

# vim:ft=zsh:nowrap
