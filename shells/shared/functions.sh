# Shared interactive Bash/Zsh commands. Script utilities live in bin/lib/common.sh.
# Native bootstrap, completion engines and editor hooks stay in shell adapters.
# Sources are runtime checkout paths; FZF expands its preview in a child shell.
# shellcheck disable=SC1091,SC2016,SC2119,SC2120
# Suspend alias expansion while parsing definitions, then restore the caller's
# setting below. This permits name() syntax even when a name is already aliased.
_dots_shared_alias_mode=''
if [[ -n ${ZSH_VERSION:-} ]]; then
  if [[ -o aliases ]]; then
    _dots_shared_alias_mode=zsh
    builtin unsetopt aliases
  fi
elif builtin shopt -q expand_aliases; then
  _dots_shared_alias_mode=bash
  builtin shopt -u expand_aliases
fi

# Default to the Git worktree's name/root; explicit names retain the caller's cwd.
# Inside tmux switch the current client instead of nesting another client.
t() {
  local name=${1-Work} directory=$PWD project result
  if (( $# > 1 )) || [[ -z $name || $name == *[[:cntrl:].:]* ]]; then
    printf 'Usage: t [session-name] (nonempty; no control characters, colon or dot)\n' >&2
    return 2
  fi
  command -v tmux >/dev/null 2>&1 || {
    printf 't: tmux not found\n' >&2
    return 127
  }
  if (( $# == 0 )) && project=$(command git rev-parse --show-toplevel 2>/dev/null) && [[ -d $project ]]; then
    directory=$project
    name=${project##*/}
    # Only inferred names are normalized: tmux forbids dots/colons in names.
    name=${name//[[:cntrl:].:]/-}
    name=${name:-Work}
  fi
  if [[ -z ${TMUX:-} ]]; then
    command tmux new-session -A -s "$name" -c "$directory"
    return $?
  fi
  # '=' prevents tmux's prefix/glob target matching, including for dash names.
  if ! command tmux has-session -t "=$name" 2>/dev/null; then
    if command tmux new-session -d -s "$name" -c "$directory"; then
      :
    else
      result=$?
      # Another client may have created it since our first check. Keep the
      # creation diagnostic, and its failure status unless that exact name exists.
      command tmux has-session -t "=$name" 2>/dev/null || return "$result"
    fi
  fi
  command tmux switch-client -t "=$name"
}

# Create a new worktree and branch from within current git directory.
ga() {
  if [[ -z "$1" ]]; then
    echo "Usage: ga [branch name]"
    return 1
  fi

  local branch="$1"
  local base
  base="$(basename "$PWD")"
  local wt_path="../${base}--${branch}"

  git worktree add -b "$branch" "$wt_path" || return
  if has mise; then mise trust "$wt_path" || return; fi
  builtin cd -- "$wt_path" || return
}

# Remove worktree and branch from within active worktree directory.
gd() {
  if gum confirm "Remove worktree and branch?"; then
    local cwd base branch root worktree

    cwd="$(pwd)"
    worktree="$(basename "$cwd")"

    # split on first `--`
    root="${worktree%%--*}"
    branch="${worktree#*--}"

    # Protect against accidentally nuking a non-worktree directory
    if [[ "$root" != "$worktree" ]]; then
      builtin cd -- "../$root" || return
      git worktree remove "$cwd" --force || return 1
      git branch -D "$branch"
    fi
  fi
}

compress() { tar -czf "${1%/}.tar.gz" "${1%/}"; }

ls_repos() {
  command find . -mindepth 2 -type d -name .git -prune -print | while IFS= read -r directory; do
    printf '%s\n' "${directory%/.git}"
  done
}

gethost() {
  local host current_host=${HOST:-${HOSTNAME:-}}
  if [[ -n "$current_host" ]]; then
    if [[ "$current_host" == "localhost" ]]; then
      if [[ -n "$distro" ]]; then
        host="$distro"
      fi
    else
      if [[ "${is_wsl:-false}" == true ]]; then
        host="$current_host (WSL)"
      else
        host="$current_host"
      fi
    fi
  fi
  echo "$host"
}

in_git() {
  git rev-parse --is-inside-work-tree >/dev/null 2>&1
}

gitcheck() {
  local verbose=0
  if [[ $1 == '-v' ]]; then
    verbose=1
    shift
  fi
  if mygit; then
    local changed
    changed=$(git status -s | awk '{print $2}')
    if [[ -n "$changed" ]]; then
      if ((verbose)); then
        echo "$changed"
      fi
      return 0
    else
      return 1
    fi
  fi
}

gitmodified() {
  if mygit; then
    local modified
    modified=$(git status -s | grep -E '^\s*M\s' | awk '{print $2}')
    if [[ -n "$modified" ]]; then
      echo "$modified"
      return 0
    else
      return 1
    fi
  fi
}

gitdeleted() {
  if mygit; then
    local deleted
    deleted=$(git status -s | grep -E '^\s*D\s' | awk '{print $2}')
    if [[ -n "$deleted" ]]; then
      echo "$deleted"
      return 0
    else
      return 1
    fi
  fi
}

gituntracked() {
  if mygit; then
    local untracked
    untracked=$(git status -s | grep '??' | awk '{print $2}')
    if [[ -n "$untracked" ]]; then
      echo "$untracked"
      return 0
    else
      return 1
    fi
  fi
}

gitsubmodule() {
  if mygit; then
    local deleted
    deleted=$(git status -s | grep -E '^\s*m\s' | awk '{print $2}')
    if [[ -n "$deleted" ]]; then
      echo "$deleted"
      return 0
    else
      return 1
    fi
  fi
}

submodules() {
  local recurse=0
  if in_git; then
    if [[ $1 == '-r' ]]; then
      recurse=1
      shift
    fi
    if ((recurse)); then
      git submodule status --recursive | awk '{print $2}'
    else
      git submodule status | awk '{print $2}'
    fi
  else
    return 1
  fi
}

# print a colorized diff
colordiff() {
  local _diff_red
  _diff_red=$(tput setaf 1 2>/dev/null)
  local _diff_green
  _diff_green=$(tput setaf 2 2>/dev/null)
  local _diff_cyan
  _diff_cyan=$(tput setaf 6 2>/dev/null)
  local _diff_reset
  _diff_reset=$(tput sgr0 2>/dev/null)

  diff -u "$@" | awk "
	/^\-/ {
		printf(\"%s\", \"$_diff_red\");
	}
	/^\+/ {
		printf(\"%s\", \"$_diff_green\");
	}
	/^@/ {
		printf(\"%s\", \"$_diff_cyan\");
	}

	{
		print \$0 \"$_diff_reset\";
	}"

  # Expand both arrays before a command can replace the pipeline status.
  local result="${pipestatus[1]:-${PIPESTATUS[0]}}"
  return "$result"
}

ls_colors() {
  local i
  for i in {0..255}; do
    printf "\x1b[38;5;${i}mcolor %d\n" "$i"
  done
  tput sgr0
}

palette() {
  local i
  for ((i=0; i<256; i++)); do
    printf '\033[38;5;%dm%03d\033[0m ' "$i" "$i"
    (( (i+1) % 16 )) || printf '\n'
  done
}

aptget_check() {
  apt-get -s upgrade | grep -P "\d\K upgraded"
}

fzpi() {
  pacman -Slq | fzf -q "$1" -m --preview 'pacman -Si {1}' | xargs -ro pacman -S
}

fzpr() {
  pacman -Qq | fzf -q "$1" -m --preview 'pacman -Qi {1}' | xargs -ro pacman -Rns
}

femoji() {
  local emojis selected_emoji
  emojis=$(curl -sSL 'https://git.io/JXXO7')
  selected_emoji=$(printf '%s\n' "$emojis" | fzf)
  printf '%s\n' "$selected_emoji"
}

truecolor-rainbow() {
  local i r g b
  for ((i = 0; i < 77; i++)); do
    r=$((255 - (i * 255 / 76)))
    g=$((i * 510 / 76))
    b=$((i * 255 / 76))
    ((g > 255)) && g=$((510 - g))
    printf '\033[48;2;%d;%d;%dm ' "$r" "$g" "$b"
  done
  tput sgr0
  echo
}

showcolors256() {
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
      $showcolor $((row * 8 + col)) "$row"
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
      $showcolor $((row * 12 + col + 232)) "$row"
    done
    echo
  done
  echo
}

_showcolor256_fg() {
  local code
  code=$(printf %03d "$1")
  echo -ne "\033[38;5;${code}m"
  echo -nE " $code "
  echo -ne "\033[0m"
}

_showcolor256_bg() {
  if (($2 % 2 == 0)); then
    echo -ne "\033[1;37m"
  else
    echo -ne "\033[0;30m"
  fi
  local code
  code=$(printf %03d "$1")
  echo -ne "\033[48;5;${code}m"
  echo -nE " $code "
  echo -ne "\033[0m"
}

showcolors16() {
  _showcolor "\033[0;30m" "\033[1;30m" "\033[40m" "\033[100m"
  _showcolor "\033[0;31m" "\033[1;31m" "\033[41m" "\033[101m"
  _showcolor "\033[0;32m" "\033[1;32m" "\033[42m" "\033[102m"
  _showcolor "\033[0;33m" "\033[1;33m" "\033[43m" "\033[103m"
  _showcolor "\033[0;34m" "\033[1;34m" "\033[44m" "\033[104m"
  _showcolor "\033[0;35m" "\033[1;35m" "\033[45m" "\033[105m"
  _showcolor "\033[0;36m" "\033[1;36m" "\033[46m" "\033[106m"
  _showcolor "\033[0;37m" "\033[1;37m" "\033[47m" "\033[107m"
}

_showcolor() {
  local code
  for code in "$@"; do
    echo -ne "$code"
    echo -nE "   $code"
    echo -ne "   \033[0m  "
  done
  echo
}

256color() { palette "$@"; }

fixpath() {
  local remaining=$PATH entry found result='' separator='' duplicate
  local -a entries=()
  while :; do
    entry=${remaining%%:*}
    duplicate=0
    for found in "${entries[@]}"; do
      if [[ $found == "$entry" ]]; then duplicate=1; break; fi
    done
    if (( ! duplicate )); then
      entries+=("$entry"); result+="$separator$entry"; separator=:
    fi
    [[ $remaining == *:* ]] || break
    remaining=${remaining#*:}
  done
  export PATH=$result
}

cleanvim() {
  mv ~/.config/nvim{,.bak}
  mv ~/.local/share/nvim{,.bak}
  mv ~/.local/state/nvim{,.bak}
  mv ~/.cache/nvim{,.bak}
}

ssl-download-certificate() {
  local host=$1
  local port=${2:-443}
  openssl s_client -showcerts -connect "${host}:${port}" </dev/null 2>/dev/null | openssl 'x509' -outform 'PEM' >"${host}:${port}.pem"
}

ssh-key-set() {
  ssh-add -D
  ssh-add "$HOME/.ssh/${1:-id_rsa}"
}

ssh-key-info() {
  ssh-keygen -l -f "$HOME/.ssh/${1:-id_rsa}"
}

fname() {
  basename "$@" | sed 's/\(.*\)\..*/\1/'
}

fext() {
  local filename
  filename=$(basename -- "$1") || return
  echo "${filename##*.}"
}

dat() {
  rich --text-full -y -e -d 1 -m "$@"
}

# Platform-independent interfaces
interfaces() {
  node <<-EOF
	var os = require('os');
	var i = os.networkInterfaces();
	Object.keys(i).forEach(function(name) {
		i[name].forEach(function(int) {
			if (int.family === 'IPv4') {
				console.log('%s: %s', name, int.address);
			}
		});
	});
	EOF
}

# Calculate CPU load / Core Count
load() {
  node -p <<-EOF
	var os = require('os');
	var c = os.cpus().length;
	os.loadavg().map(function(l) {
		return (l/c).toFixed(2);
	}).join(' ');
	EOF
}

# Platform-independent memory usage
meminfo() {
  node <<-EOF
	var os = require('os');
	var free = os.freemem();
	var total = os.totalmem();
	var used = total - free;
	console.log('memory: %dmb / %dmb (%d%%)',
	    Math.round(used / 1024 / 1024),
	    Math.round(total / 1024 / 1024),
	    Math.round(used * 100 / total));
	EOF
}

htmldecode() {
  local value=$*
  value=${value//+/ }
  value=${value//&#x/\\x}
  value=${value//;/}
  printf '%b\n' "$value"
}
urldecode() {
  local value=$*
  value=${value//+/ }
  printf '%b\n' "${value//\%/\\x}"
}

expandurl() { curl -sIL -- "$1" | awk '/^Location/ || /^Localização/ {print $2}'; }
calc() { printf '%s\n' "scale=2;$*" | bc; }
findfiles() { find . -type f -iname "*${*}*"; }
gsend() { git commit -am "$1" && git push; }
gst() { git status; }
decToBin() { echo "ibase=10; obase=2; $1" | bc; }
decTohex() { bc <<<"obase=16; $1"; }
biggest() { du -k -- ./* | sort -nr | cut -f2 | head -20 | xargs -d "\n" du -sh; }
top10() { history | awk '{print $2}' | sort | uniq -c | sort -rn | head; }
beep() { echo -e -n \\a; }
dict() { curl "dict://dict.org/d:${1%%/}"; }

getextension() {
  echo "Full filename: $(basename -- "$1")"
  echo "Extension: ${1##*.}"
  echo "without extension: ${1%.*}"
}

geturls() {
  # source: http://stackoverflow.com/questions/2804467/spider-a-website-and-return-urls-only
  [[ $# == 1 ]] || { printf 'Usage: geturls <url>\n' >&2; return 2; }
  wget -q "$1" -O - |
    tr "\t\r\n'" '   "' |
    grep -i -o '<a[^>]\+href[ ]*=[ \t]*"\(ht\|f\)tps\?:[^"]\+"' |
    sed -e 's/^.*"\([^"]\+\)".*$/\1/g'
}

backup() {
  [[ $# == 1 && -n $1 ]] || { printf 'Usage: backup <file>\n' >&2; return 2; }
  local file=$1 timestamp backupdir=$HOME/backups
  timestamp=$(date '+%Y-%m-%d-%H:%M:%S') || return
  command mkdir -p -- "$backupdir" || return
  command cp -a -- "$file" "$backupdir/${file##*/}.$timestamp"
}

add_ls_colors() { export LS_COLORS="${LS_COLORS:+$LS_COLORS:}$1"; }

rlp() {
  if [[ -n ${ZSH_VERSION:-} ]]; then
    source "$DOTS/shells/zsh/zshrc" || return
    ok 'ZSH RELOADED'
  else
    source "$DOTS/shells/bash/.bashrc" || return
    ok 'BASH RELOADED'
  fi
}

mkcd() { source "$DOTS/scripts/mkcd" "$@"; }
gup() {
  local msg='Sync repository tree'
  (( $# == 0 )) || msg="$*"
  command git-it publish --all --yes -m "$msg"
}
zd() {
  if (( $# == 0 )); then builtin cd -- "$HOME" || return
  elif [[ -d $1 ]]; then builtin cd -- "$1" || return
  else
    z "$@" || { printf 'Error: Directory not found\n' >&2; return 1; }
    printf '\U000F17A9 '; pwd
  fi
}
y() {
  local tmp cwd result
  tmp=$(mktemp "${TMPDIR:-/tmp}/yazi-cwd.XXXXXX") || return
  command yazi "$@" --cwd-file="$tmp"
  result=$?
  IFS= read -r cwd < "$tmp" || :
  if [[ $result == 0 && -n $cwd && $cwd != "$PWD" && -d $cwd ]]; then
    builtin cd -- "$cwd" || result=$?
  fi
  command rm -f -- "$tmp"
  return "$result"
}
yap() {
  (( $# )) || { printf 'ERROR: The first argument must be a project\n' >&2; return 64; }
  local yaziProject=$1 yaziId=$RANDOM
  shift
  ( (sleep 0.1; YAZI_ID=$yaziId ya emit plugin projects "load $yaziProject") &)
  y --client-id "$yaziId" "$@"
}
sff() {
  (( $# == 1 )) || { printf 'Usage: sff <destination> (e.g. sff host:/tmp/)\n' >&2; return 1; }
  local file
  file=$(find . -type f -printf '%T@\t%p\n' | sort -rn | cut -f2- | _dots_file_picker) &&
    [[ -n $file ]] && scp -- "$file" "$1"
}
n() { if (( $# == 0 )); then command nvim .; else command nvim "$@"; fi; }
reload-completion() {
  if [[ -n ${ZSH_VERSION:-} ]]; then _dots_zsh_reload_completion "$@"
  else _dots_bash_reload_completion "$@"; fi
}
reload-completions() {
  if [[ -n ${ZSH_VERSION:-} ]]; then _dots_zsh_reload_completions "$@"
  else _dots_bash_reload_completions "$@"; fi
}
eff() {
  local file
  file=$(_dots_file_picker) || return
  [[ -n $file ]] || return 1
  "$EDITOR" "$file"
}

_dots_file_picker() {
  if [[ $TERM == xterm-kitty ]]; then
    command fzf --preview 'case $(file --mime-type -b {}) in image/*) kitty icat --clear --transfer-mode=memory --stdin=no --place=${FZF_PREVIEW_COLUMNS}x${FZF_PREVIEW_LINES}@0x0 {} ;; *) bat --style=numbers --color=always {} ;; esac' "$@"
  else
    command fzf --preview 'bat --style=numbers --color=always {}' "$@"
  fi
}

_dots_paint() {
  err 'pastel not found; install pastel to use paint'
  return 127
}

case $_dots_shared_alias_mode in
  zsh) builtin setopt aliases ;;
  bash) builtin shopt -s expand_aliases ;;
esac
builtin unset _dots_shared_alias_mode
