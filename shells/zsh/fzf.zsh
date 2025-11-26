BOLD="$(tput bold 2>/dev/null || printf '')"
UNDERLINE="$(tput smul 2>/dev/null || printf '')"
ITALIC="$(tput sitm 2>/dev/null || printf '')"
DIM="$(tput dim 2>/dev/null || printf '')"
INVERT="$(tput rev 2>/dev/null || printf '')"
BLINK="$(tput blink 2>/dev/null || printf '')"
INVIS="$(tput invis 2>/dev/null || printf '')"
GREY="$(tput setaf 7 2>/dev/null || printf '')"
BLACK="$(tput setaf 8 2>/dev/null || printf '')"
RED="$(tput setaf 1 2>/dev/null || printf '')"
GREEN="$(tput setaf 2 2>/dev/null || printf '')"
YELLOW="$(tput setaf 3 2>/dev/null || printf '')"
BLUE="$(tput setaf 4 2>/dev/null || printf '')"
DARKBLUE="$(tput setaf 12 2>/dev/null || printf '')"
MAGENTA="$(tput setaf 5 2>/dev/null || printf '')"
CYAN="$(tput setaf 6 2>/dev/null || printf '')"
NO_COLOR="$(tput sgr0 2>/dev/null || printf '')"

if cmd_exists fd; then
  export FZF_DEFAULT_COMMAND='fd --type f --strip-cwd-prefix --hidden --exclude .git'
fi

fzdef() {
_FZF_OPTS_="\
--style=default \
--layout=reverse \
--height=~90% \
--border=none \
--info=hidden \
--prompt=' 󰅂 ' \
--pointer='▎' \
--marker='▎' \
--gutter='▎' \
--gutter-raw='▎' \
--no-separator \
--no-scrollbar"

_FZF_BINDS_="\
Ctrl-X:toggle-preview,\
up:up-match,\
down:down-match,\
alt-r:toggle-raw"

zource "$THEMEDIR/fzf.zsh"
_FZF_PREVIEW_POS_='bottom:hidden:50%:border-sharp'
_PREVIEW_="preview.zsh"

export _FZF_OPTS_ _FZF_BINDS_ _FZF_COLORS_ _FZF_PREVIEW_POS_ _PREVIEW_

export FZF_DEFAULT_OPTS="$_FZF_OPTS_ --bind=$_FZF_BINDS_ --color=$_FZF_COLORS_ --preview-window=$_FZF_PREVIEW_POS_ --preview='$_PREVIEW_ {}'"
}

fzdef



  # _fz_write_rc() {
  #   local rc=~/.fzfrc
  #   if [[ -f $rc ]]; then
  #   print -r -- "$FZF_DEFAULT_OPTS" | sed 's/ --/\n--/g' >! "$rc"
  # else
  #   print -r -- "$FZF_DEFAULT_OPTS" | sed 's/ --/\n--/g' > "$rc"
  #   fi
  #   echo "fzopt: wrote $rc"
  # }

fzopt() {
  # -------------------------
  # Help / usage
  # -------------------------
  if [[ $# -eq 0 || $1 == help || $1 == -h || $1 == --help ]]; then
    cat <<'EOF'
Usage:
  fzopt <key> <value> [<key> <value> ...]
  fzopt color   <color-key> <color-value> [color <color-key> <color-value> ...]
  fzopt bind    <key> <action>            [bind  <key> <action>            ...]
  fzopt uncolor <color-key> [color-key ...]
  fzopt unbind  <key>       [key ...]
  fzopt dump
  fzopt write-rc

Examples:
  fzopt style full
  fzopt height "~80%" style minimal
  fzopt color prompt "#ff0000"
  fzopt bind ctrl-p toggle-preview
  fzopt uncolor prompt gutter
  fzopt unbind ctrl-p ctrl-x
  fzopt dump
  fzopt write-rc   # writes pretty ~/.fzfrc from $FZF_DEFAULT_OPTS

Notes:
  • Only known fzf options are allowed.
  • Only known --color subkeys are allowed.
  • prompt/pointer/marker/gutters/*-label/preview are always written as --key='value'.
EOF
    return 0
  fi

  if [[ -z $FZF_DEFAULT_OPTS ]]; then
    echo "fzopt: FZF_DEFAULT_OPTS is empty" >&2
    return 1
  fi

  # Strip one pair of outer double quotes if present:  "...."
  if [[ $FZF_DEFAULT_OPTS == \"*\" ]]; then
    FZF_DEFAULT_OPTS=${FZF_DEFAULT_OPTS#\"}
    FZF_DEFAULT_OPTS=${FZF_DEFAULT_OPTS%\"}
  fi

  local -a args words
  args=("$@")

  # Use zsh tokenizer so quotes are respected
  words=(${(z)FZF_DEFAULT_OPTS})

  # -------------------------
  # Valid option lists
  # -------------------------
  local -a _fz_valid_opts=(
    color bind style height min-height layout margin padding border border-label border-label-pos
    gutter gutter-raw pointer marker scrollbar list-border list-label list-label-pos
    prompt info info-command input-border input-label input-label-pos header header-lines
    header-first header-border header-label header-label-pos header-lines-border footer
    footer-border footer-label footer-label-pos
    preview preview-border preview-label preview-label-pos preview-window
  )

  # Valid color subkeys (from your list)
  local -a _fz_color_keys=(
    fg list-fg selected-fg preview-fg bg list-bg selected-bg preview-bg input-bg header-bg footer-bg hl fg+ bg+ gutter hl+ query info border scrollbar separator preview-border preview-scrollbar input-border header-border footer-border label list-label preview-label input-label header-label footer-label prompt pointer marker spinner header footer
  )

  # These are always rendered as: --key='value'
  local -a _fz_stringy_keys=(
    prompt pointer marker gutter gutter-raw
    border-label list-label input-label header-label preview-label footer-label
    preview
  )

  _fz_is_valid_key() {
    local key=$1
    if [[ $key == no-* ]]; then
      local base=${key#no-}
      (( ${_fz_valid_opts[(I)$base]} )) && return 0
    fi
    (( ${_fz_valid_opts[(I)$key]} )) && return 0
    return 1
  }

  _fz_is_valid_color_key() {
    local ckey=$1
    (( ${_fz_color_keys[(I)$ckey]} )) && return 0
    return 1
  }

  # -------------------------
  # dump / write-rc (read-only)
  # -------------------------
  _fz_dump() {
    print -r -- "$FZF_DEFAULT_OPTS" | sed 's/ --/\n--/g'
  }

  _fz_write_rc() {
    local rc=~/.fzfrc
    print -r -- "$FZF_DEFAULT_OPTS" | sed 's/ --/\n--/g' > "$rc"
    echo "fzopt: wrote $rc"
  }

  if [[ $1 == dump ]]; then
    _fz_dump
    return 0
  elif [[ $1 == write-rc ]]; then
    _fz_write_rc
    return 0
  fi

  # -------------------------
  # Stringy options: canonical "--key='value'"
  # -------------------------
  _fzopt_set_stringy() {
    local key=$1 val=$2
    if ! _fz_is_valid_key "$key"; then
      echo "fzopt: '$key' is not a valid fzf option" >&2
      return 1
    fi

    local -a new
    local i changed=0

    for (( i=1; i<=${#words}; ++i )); do
      local w=${words[i]}

      # Handle:
      #   --key value
      #   --key=value
      #   --key='value with spaces'
      if [[ $w == --$key ]]; then
        if (( i+1 <= ${#words} )) && [[ ${words[i+1]} != --* ]]; then
          (( i++ ))  # skip old value token
        fi
        new+=("--$key='$val'")
        changed=1
      elif [[ $w == --$key=* ]]; then
        new+=("--$key='$val'")
        changed=1
      else
        new+=("$w")
      fi
    done

    (( !changed )) && new+=("--$key='$val'")

    words=("${new[@]}")

    # Extra cleanup for preview: remove any stray "{}'" token from older broken values
    if [[ $key == preview ]]; then
      local -a cleaned; local t
      for t in "${words[@]}"; do
        [[ $t == "{}'" ]] && continue
        cleaned+=("$t")
      done
      words=("${cleaned[@]}")
    fi

    FZF_DEFAULT_OPTS="${(j: :)words}"
  }

  # -------------------------
  # Normal options: --key value / --key=value
  # -------------------------
  _fzopt_set_normal() {
    local key=$1 val=$2
    if ! _fz_is_valid_key "$key"; then
      echo "fzopt: '$key' is not a valid fzf option" >&2
      return 1
    fi

    local -a new
    local i changed=0

    for (( i=1; i<=${#words}; ++i )); do
      local w=${words[i]}
      case $w in
        "--$key")
          new+=("--$key=$val")
          (( i++ ))  # skip old value
          changed=1
          ;;
        "--$key="*)
          new+=("--$key=$val")
          changed=1
          ;;
        *)
          new+=("$w")
          ;;
      esac
    done

    (( !changed )) && new+=("--$key=$val")

    words=("${new[@]}")
    FZF_DEFAULT_OPTS="${(j: :)words}"
  }

  # -------------------------
  # --color sub-options
  # -------------------------
  _fzcolor_set() {
    local ckey=$1 cval=$2

    if ! _fz_is_valid_color_key "$ckey"; then
      echo "fzopt: '$ckey' is not a valid --color key" >&2
      return 1
    fi

    local i
    for i in {1..$#words}; do
      if [[ ${words[i]} == --color || ${words[i]} == --color=* ]]; then
        local color_list
        if [[ ${words[i]} == --color ]]; then
          color_list=${words[i+1]}
        else
          color_list=${words[i]#--color=}
        fi

        local -a parts
        local j found=0
        parts=("${(@s:,:)color_list}")

        for j in {1..$#parts}; do
          if [[ ${parts[j]} == ${ckey}:* ]]; then
            parts[j]="${ckey}:${cval}"
            found=1
          fi
        done
        (( !found )) && parts+=("${ckey}:${cval}")

        if [[ ${words[i]} == --color ]]; then
          words[i+1]="${(j:,:)parts}"
        else
          words[i]="--color=${(j:,:)parts}"
        fi

        FZF_DEFAULT_OPTS="${(j: :)words}"
        return 0
      fi
    done

    # no --color yet
    words+=("--color=${ckey}:${cval}")
    FZF_DEFAULT_OPTS="${(j: :)words}"
    return 0
  }

  _fzcolor_unset() {
    [[ $# -eq 0 ]] && return 0
    local -A rm; local k
    for k in "$@"; do
      if _fz_is_valid_color_key "$k"; then
        rm[$k]=1
      else
        echo "fzopt: '$k' is not a valid --color key (ignored)" >&2
      fi
    done

    local i
    for i in {1..$#words}; do
      if [[ ${words[i]} == --color || ${words[i]} == --color=* ]]; then
        local color_list
        if [[ ${words[i]} == --color ]]; then
          color_list=${words[i+1]}
        else
          color_list=${words[i]#--color=}
        fi

        local -a parts new_parts
        local j
        parts=("${(@s:,:)color_list}")

        for j in {1..$#parts}; do
          local ckey=${parts[j]%%:*}
          [[ -n ${rm[$ckey]} ]] && continue
          new_parts+=("${parts[j]}")
        done

        if (( ${#new_parts} )); then
          if [[ ${words[i]} == --color ]]; then
            words[i+1]="${(j:,:)new_parts}"
          else
            words[i]="--color=${(j:,:)new_parts}"
          fi
        else
          local -a tmp; local t
          if [[ ${words[i]} == --color ]]; then
            for t in {1..$#words}; do
              (( t == i || t == i+1 )) && continue
              tmp+=("${words[t]}")
            done
          else
            for t in {1..$#words}; do
              (( t == i )) && continue
              tmp+=("${words[t]}")
            done
          fi
          words=("${tmp[@]}")
        fi

        FZF_DEFAULT_OPTS="${(j: :)words}"
        return 0
      fi
    done
  }

  # -------------------------
  # --bind sub-options
  # -------------------------
  _fzbind_set() {
    local bkey=$1 bval=$2
    local i

    for i in {1..$#words}; do
      if [[ ${words[i]} == --bind || ${words[i]} == --bind=* ]]; then
        local bind_list
        if [[ ${words[i]} == --bind ]]; then
          bind_list=${words[i+1]}
        else
          bind_list=${words[i]#--bind=}
        fi

        if [[ $bind_list == \'* ]]; then
          bind_list=${bind_list#\'}
          bind_list=${bind_list%\'}
        fi

        local -a parts
        local j found=0
        parts=("${(@s:,:)bind_list}")

        for j in {1..$#parts}; do
          local cur_key=${parts[j]%%:*}
          if [[ $cur_key == $bkey ]]; then
            parts[j]="${bkey}:${bval}"
            found=1
          fi
        done
        (( !found )) && parts+=("${bkey}:${bval}")

        bind_list="${(j:,:)parts}"

        if [[ ${words[i]} == --bind ]]; then
          words[i+1]="$bind_list"
        else
          words[i]="--bind=$bind_list"
        fi

        FZF_DEFAULT_OPTS="${(j: :)words}"
        return 0
      fi
    done

    words+=("--bind" "${bkey}:${bval}")
    FZF_DEFAULT_OPTS="${(j: :)words}"
    return 0
  }

  _fzbind_unset() {
    [[ $# -eq 0 ]] && return 0
    local -A rm; local k
    for k in "$@"; do rm[$k]=1; done

    local i
    for i in {1..$#words}; do
      if [[ ${words[i]} == --bind || ${words[i]} == --bind=* ]]; then
        local bind_list
        if [[ ${words[i]} == --bind ]]; then
          bind_list=${words[i+1]}
        else
          bind_list=${words[i]#--bind=}
        fi

        if [[ $bind_list == \'* ]]; then
          bind_list=${bind_list#\'}
          bind_list=${bind_list%\'}
        fi

        local -a parts new_parts
        local j
        parts=("${(@s:,:)bind_list}")

        for j in {1..$#parts}; do
          local cur_key=${parts[j]%%:*}
          [[ -n ${rm[$cur_key]} ]] && continue
          new_parts+=("${parts[j]}")
        done

        if (( ${#new_parts} )); then
          bind_list="${(j:,:)new_parts}"
          if [[ ${words[i]} == --bind ]]; then
            words[i+1]="$bind_list"
          else
            words[i]="--bind=$bind_list"
          fi
        else
          local -a tmp; local t
          if [[ ${words[i]} == --bind ]]; then
            for t in {1..$#words}; do
              (( t == i || t == i+1 )) && continue
              tmp+=("${words[t]}")
            done
          else
            for t in {1..$#words}; do
              (( t == i )) && continue
              tmp+=("${words[t]}")
            done
          fi
          words=("${tmp[@]}")
        fi

        FZF_DEFAULT_OPTS="${(j: :)words}"
        return 0
      fi
    done
  }

  # -------------------------
  # main arg loop
  # -------------------------
  local i=1
  while (( i <= $#args )); do
    case ${args[i]} in
      color)
        (( i + 2 > $#args )) && {
          echo "fzopt: 'color' requires <color-key> <color-value>" >&2
          return 1
        }
        _fzcolor_set "${args[i+1]}" "${args[i+2]}" || return 1
        (( i += 3 ))
        ;;
      bind)
        (( i + 2 > $#args )) && {
          echo "fzopt: 'bind' requires <key> <action>" >&2
          return 1
        }
        _fzbind_set "${args[i+1]}" "${args[i+2]}" || return 1
        (( i += 3 ))
        ;;
      uncolor)
        (( i + 1 > $#args )) && {
          echo "fzopt: 'uncolor' requires at least one <color-key>" >&2
          return 1
        }
        local -a to_rm_color=()
        (( i++ ))
        while (( i <= $#args )) && [[ ${args[i]} != color && ${args[i]} != bind && ${args[i]} != unbind && ${args[i]} != uncolor ]]; do
          to_rm_color+=("${args[i]}")
          (( i++ ))
        done
        _fzcolor_unset "${to_rm_color[@]}"
        ;;
      unbind)
        (( i + 1 > $#args )) && {
          echo "fzopt: 'unbind' requires at least one <key>" >&2
          return 1
        }
        local -a to_rm_bind=()
        (( i++ ))
        while (( i <= $#args )) && [[ ${args[i]} != color && ${args[i]} != bind && ${args[i]} != unbind && ${args[i]} != uncolor ]]; do
          to_rm_bind+=("${args[i]}")
          (( i++ ))
        done
        _fzbind_unset "${to_rm_bind[@]}"
        ;;
      *)
        (( i + 1 > $#args )) && {
          echo "fzopt: normal option requires <key> <value>" >&2
          return 1
        }
        local key=${args[i]}
        local val=${args[i+1]}
        if (( ${_fz_stringy_keys[(I)$key]} )); then
          _fzopt_set_stringy "$key" "$val" || return 1
        else
          _fzopt_set_normal "$key" "$val" || return 1
        fi
        (( i += 2 ))
        ;;
    esac
  done
}

# vim: set noet ft=zsh tw=4 sw=4 ff=unix
