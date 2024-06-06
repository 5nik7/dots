function rngr() {
    local tmp="$(mktemp -t "ranger-cwd.XXXXX")"
    ranger --choosedir="$tmp"
    if cwd="$(cat "$tmp")" && [ -n "$cwd" ] && [ "$cwd" != "$PWD" ]; then
	cd "$cwd"
    fi
    rm -f "$tmp"
}
alias dd='rngr'

function ya() {
    local tmp="$(mktemp -t "yazi-cwd.XXXXX")"
    yazi "$@" --cwd-file="$tmp"
    if cwd="$(cat "$tmp")" && [ -n "$cwd" ] && [ "$cwd" != "$PWD" ]; then
	cd "$cwd"
    fi
    rm -f "$tmp"
}
alias d='ya'

function open {
	if [ -z "$1" ]; then
		explorer.exe .
	else
		explorer.exe "$1"
	fi
}

alias ll='echo -e "" && eza -lA --git --git-repos --icons --group-directories-first --no-quotes'
alias l='echo -e "" && eza -lA --git --git-repos --icons --group-directories-first --no-quotes --no-permissions --no-filesize --no-user --no-time'

function cd() {
    builtin cd "$@" && l
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

function lnk() {
    orig_file="$1"
    dest_file="$2"

    if [ ! -d "$(dirname "$dest_file")" ]; then
        mkdir -p "$(dirname "$dest_file")"
    fi

    rel1=$(rel_path $orig_file)
	  rel2=$(rel_path $dest_file)


    if [ -e "$dest_file" ]; then
        mv "$dest_file" "$dest_file.bak"
        print_in_bright_black "\n  Backing up $rel2 to"
        print_in_red " $rel2.bak\n"
    fi

    ln -s "$orig_file" "$dest_file"
    print_in_blue "\n  $rel1"
    print_in_bright_black " -> "
    print_in_cyan "$rel2\n"
}

# function lnk() {
#     orig_file="$DOTFILES/$1"
#     if [ -n "$2" ]; then
#         dest_file="$HOME/$2"
#     else
#         if [[ $1 == config/* ]]; then
#             dest_file="$HOME/.${1}"
#         else
#             dest_file="$HOME/$1"
#         fi
#     fi
#
#     mkdir -p "$(dirname "$orig_file")"
#     mkdir -p "$(dirname "$dest_file")"
#
#     rel1=$(rel_path $orig_file)
# 	  rel2=$(rel_path $dest_file)
#
#
#     if [ -e "$dest_file" ]; then
#         mv "$dest_file" "$dest_file.bak"
#         print_in_bright_black "\n  Backing up $rel2 to"
#         print_in_red " $rel2.bak\n"
#     fi
#
#     ln -s "$orig_file" "$dest_file"
#     print_in_blue "\n  $rel1"
#     print_in_bright_black " -> "
#     print_in_cyan "$rel2\n"
# }

function 256color() {
	for code in {000..255}; do
		print -nP -- "%F{$code}$code %f";
		if [ $((${code} % 16)) -eq 15 ]; then
			echo ""
		fi
	done
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

# Runs when tab is pressed after ,
function _fzf_comprun() {
    local command=$1
    shift

    case "$command" in
    cd) fzf "$@" --preview 'exa -TFl --group-directories-first --icons --git -L 2 --no-user {}' ;;
    nvim) fzf --preview 'bat --color=always --style=numbers --line-range=:500 {}' ;;
    vim) fzf --preview 'bat --color=always --style=numbers --line-range=:500 {}' ;;
    *) fzf "$@" ;;
    esac
}

# colorized man output
# function man() {
#     env \
#         LESS_TERMCAP_mb=$(printf "\e[1;31m") \
#         LESS_TERMCAP_md=$(printf "\e[1;36m") \
#         LESS_TERMCAP_me=$(printf "\e[0m") \
#         LESS_TERMCAP_se=$(printf "\e[0m") \
#         LESS_TERMCAP_so=$(printf "\e[1;44;33m") \
#         LESS_TERMCAP_ue=$(printf "\e[0m") \
#         LESS_TERMCAP_us=$(printf "\e[1;32m") \
#         PAGER="${commands[less]:-$PAGER}" \
#         _NROFF_U=1 \
#         PATH="$HOME/bin:$PATH" \
#         man "$@"
# }

# show colors and codes
function color() {
    local fgc bgc vals seq0

    printf "Color escapes are %s\n" '\e[${value};...;${value}m'
    printf "Values 30..37 are \e[33mforeground colors\e[m\n"
    printf "Values 40..47 are \e[43mbackground colors\e[m\n"
    printf "Value  1 gives a  \e[1mbold-faced look\e[m\n\n"

    # foreground colors
    for fgc in {30..37}; do
        # background colors
        for bgc in {40..47}; do
            fgc=${fgc#37} # white
            bgc=${bgc#40} # black

            vals="${fgc:+$fgc;}${bgc}"
            vals=${vals%%;}

            seq0="${vals:+\e[${vals}m}"
            printf "  %-9s" "${seq0:-(default)}"
            printf " ${seq0}TEXT\e[m"
            printf " \e[${vals:+${vals+$vals;}}1mBOLD\e[m"
        done
        echo
        echo
    done
}
