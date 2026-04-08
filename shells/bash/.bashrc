# ~/.bashrc: executed by bash(1) for non-login shells.
# If not running interactively, don't do anything
# [ -z "$PS1" ] && return
[[ $- != *i* ]] && return

[ -f "$COLORS" ] && source "$COLORS"
[ -f "$UTIL" ] && source "$UTIL"

LANG=en_US.UTF-8
export LANG

INPUTRC=~/.inputrc

if has nvim; then
  EDITOR='nvim'
elif has vim; then
  EDITOR='vim'
elif had vi; then
  EDITOR='vi'
elif had code; then
  EDITOR='code'
else
  EDITOR='nano'
fi

# avoid ctrl-s freeze your terminal
stty stop ""

so ~/.bash_aliases

htmldecode() {
  : "${*//+/ }"
  echo -e "${_//&#x/\x}" | tr -d ';'
}
urldecode() {
  : "${*//+/ }"
  echo -e "${_//%/\\x}"
}

set bell-style none

shopt -s histverify   # verifica comandos do histórico
shopt -s checkwinsize # ajusta janela redimensionada
# Shell Options
shopt -s hostcomplete
shopt -s extglob
[ ${BASH_VERSINFO[0]} -ge 4 ] && shopt -s globstar
shopt -s cdspell # fix wrong type keys
shopt -s dirspell
shopt -s autocd

HISTFILESIZE=10000

export HISTCONTROL=ignoredups
# ... and ignore same sucessive entries.
export HISTCONTROL=ignoreboth
export HISTIGNORE="&:ls:pwd:[bf]g:ssh *:exit"
# export HISTCONTROL=$HISTCONTROL${HISTCONTROL+,}ignoredups
# export HISTIGNORE=$'[ \t]*:&:[fb]g:exit'

LANG=en_US.UTF-8
export LANG

# convert text to lowcase
lower() { echo "${@}" | awk '{print tolower($0)}'; }
upper() { echo "${@}" | awk '{print toupper($0)}'; }
expandurl() { curl -sIL $1 | awk '/^Location/ || /^Localização/ {print $2}'; }
calc() { echo "scale=2;$@" | bc; }
ff() { find . -type f -iname '*'"$@"'*'; }
mkcd() { mkdir -p "$@" && cd $_; }
gsend() { git commit -am "$1" && git push; }
gst() { git status; }
decToBin() { echo "ibase=10; obase=2; $1" | bc; }
decTohex() { bc <<<"obase=16; $1"; }
biggest() { du -k * | sort -nr | cut -f2 | head -20 | xargs -d "\n" du -sh; }
top10() { history | awk '{print $2}' | sort | uniq -c | sort -rn | head; }
beep() { echo -e -n \\a; }
dict() { curl "dict://dict.org/d:${1%%/}"; }

export LS_COLORS=$LS_COLORS:"*.wmv=01;35":"*.wma=01;35":"*.flv=01;35":"*.m4a=01;35":"*.mp3=01;35":"*.mp4=01;35"

function add_ls_colors { export LS_COLORS="$LS_COLORS:$1"; }
#export LS_COLORS=
add_ls_colors "*.ps=00;35:*.eps=00;35:*.pdf=00;35:*.svg=00;35"
add_ls_colors "*.jpg=00;35:*.png=00;35:*.gif=00;35"
add_ls_colors "*.bmp=00;35:*.ppm=00;35:*.tga=00;35"
add_ls_colors "*.xbm=00;35:*.xpm=00;35:*.tif=00;35"
add_ls_colors "*.png=00;35:*.mpg=00;35:*.avi=00;35"
## Archive files
add_ls_colors "*.tar=00;31:*.tgz=00;31:*.arj=00;31"
add_ls_colors "*.taz=00;31:*.lzh=00;31:*.zip=00;31"
add_ls_colors "*.z=00;31:*.Z=00;31:*.gz=00;31"
add_ls_colors "*.bz2=00;31:*.deb=00;31:*.rpm=00;31"
## Fixes
add_ls_colors "*.com=00;00:"

# set variable identifying the chroot you work in (used in the prompt below)
if [ -z "$debian_chroot" ] && [ -r /etc/debian_chroot ]; then
  debian_chroot=$(cat /etc/debian_chroot)
fi

if [[ "$(id -un)" != "root" ]]; then
  PS1='`[ $? = 0 ] && echo "\[\033[01;34m\]✔\[\033[00m\]"\
    || echo "\[\033[01;31m\]✘\[\033[00m\]"` [\A] \[\033[01;32m\]\u:\[\033[01;34m\]\w\[\033[00m\]\$ '
else
  # prompt para o root
  #PS1='\[\033[01;31m\]\u@\h\[\033[00m\]:\[\033[01;34m\]\w\[\033[00m\]\$ '
  PS1='`[ $? = 0 ] && echo "\[\033[01;34m\]✔\[\033[00m\]" ||\
    echo "\[\033[01;31m\]✘\[\033[00m\]"` [\A] \[\033[01;31m\]\u\[\033[00m\]:\[\033[01;34m\]\w\[\033[00m\]\$ '
fi

export prompt_command='echo -ne "\033]0;"`hostname -i`"\007"'

getextension() {
  echo "Full filename: $(basename ${1})"
  echo "Extension: ${1##*.}"
  echo "without extension: ${1%.*}"
}

geturls() {
  # source: http://stackoverflow.com/questions/2804467/spider-a-website-and-return-urls-only
  ${1?"Usage: geturls Link"}
  wget -q "$1" -O - |
    tr "\t\r\n'" '   "' |
    grep -i -o '<a[^>]\+href[ ]*=[ \t]*"\(ht\|f\)tps\?:[^"]\+"' |
    sed -e 's/^.*"\([^"]\+\)".*$/\1/g'
}

backup() {
  file=${1:?"error: I need a file to backup"}

  timestamp=$(date '+%Y-%m-%d-%H:%M:%S')
  backupdir=~/backups

  [ -d ${backupdir} ] || mkdir -p ${backupdir}
  cp -a ${file} ${backupdir}/$(basename ${file}).${timestamp}
  return $?
}

so ~/.fzf.bash
