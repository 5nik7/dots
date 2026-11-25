# Only stable generated data goes here; session activation remains immediate.
zmodload zsh/stat
zmodload -F zsh/files b:zf_mkdir b:zf_mv b:zf_rm

# Return one validated snapshot. Replacing the cache in another shell cannot
# change the bytes the current shell subsequently sources.
_dots_generated_template() {
  local name=$1 executable=$2
  shift 2
  local resolved=${commands[$executable]:-$executable}
  [[ -x $resolved ]] || return 1
  resolved=${resolved:A}
  local -A info
  zstat -H info -- "$resolved" 2>/dev/null || return 1
  local signature="${(q)resolved}:${info[device]}:${info[inode]}:${info[size]}:${info[mtime]}:${info[ctime]}:${(j: :)${(q)@}}"
  local directory="$XDG_CACHE_HOME/dots/zsh/${DOTS_PLATFORM:-linux}-$ZSH_VERSION"
  local target="$directory/$name.zsh" content temporary magic
  if [[ $name == uv || $name == starship ]]; then
    (( ! ${+functions[$executable]} )) || return 1
    IFS= read -r -u 0 -k 4 magic < "$resolved" && [[ $magic == $'\177ELF' ]] || return 1
  fi
  [[ -d $directory ]] || (umask 077; zf_mkdir -p -- "$directory") 2>/dev/null || return 1
  [[ -O $directory && ! -L $directory ]] && zstat -H info -- "$directory" 2>/dev/null &&
      (( (info[mode] & 8#22) == 0 )) || return 1
  if [[ -f $target && ! -L $target && -O $target ]] && zstat -H info -- "$target" 2>/dev/null &&
      (( (info[mode] & 8#77) == 0 )); then
    content=$(<"$target")
    if [[ ${content%%$'\n'*} == "# $signature" ]]; then REPLY=$content; return 0; fi
  fi
  # umask is scoped to the generator's subshell, never the interactive shell.
  temporary="$target.tmp.$$.${RANDOM}"
  if (umask 077; {
        print -r -- "# $signature"
        case $name in
          uv) builtin cd -- "$directory" && command env -i HOME="$PWD" "$resolved" --no-config "$@" ;;
          starship) builtin cd -- "$directory" && command env -i HOME="$PWD" "$resolved" "$@" ;;
          *) "$resolved" "$@" ;;
        esac
      } >| "$temporary") 2>/dev/null; then
    content=$(<"$temporary")
    if [[ $content == *$'\n'?* ]] && command zsh -dfn "$temporary" 2>/dev/null; then
      zf_mv -f -- "$temporary" "$target" || { zf_rm -f -- "$temporary"; return 1; }
      REPLY=$content
      return 0
    fi
  fi
  zf_rm -f -- "$temporary" 2>/dev/null
  return 1
}

_dots_source_generated() {
  local REPLY
  if _dots_generated_template "$@"; then source /dev/stdin <<< "$REPLY"
  else
    # Preserve availability if the cache cannot be written. Generator failures
    # are not evaluated; successful uncached output still works this session.
    local name=$1 output
    shift
    if output=$("$@") && [[ -n $output ]] &&
        (print -r -- "$output" | command zsh -dfn 2>/dev/null); then
      eval "$output"
    else return 1
    fi
  fi
}

# Vivid output is data, not shell code. Include all documented lookup locations
# for the selected theme and filetype database, including missing-file markers.
_dots_vivid_colors() {
  local selected=$1 executable=${commands[vivid]:-} candidate base first=''
  [[ -n $executable ]] || return 1
  local -a inputs=("${executable:A}")
  [[ $selected != */* ]] || inputs+=("${selected:A}")
  for base in "$XDG_CONFIG_HOME/vivid" "$HOME/.config/vivid" \
      /usr/share/vivid "${PREFIX:-/usr}/share/vivid"; do
    [[ $selected == */* ]] || inputs+=("$base/themes/$selected.yml")
    inputs+=("$base/filetypes.yml")
  done
  local signature="${(q)selected}" directory="$XDG_CACHE_HOME/dots/zsh/${DOTS_PLATFORM:-linux}-$ZSH_VERSION"
  local -A info
  for candidate in "${inputs[@]}"; do
    signature+=":${(q)candidate}"
    if zstat -H info -- "$candidate" 2>/dev/null; then
      signature+=":${info[device]}:${info[inode]}:${info[size]}:${info[mtime]}:${info[ctime]}"
    else signature+=':missing'
    fi
  done
  local target="$directory/vivid.colors" temporary="$directory/vivid.tmp.$$.${RANDOM}" value
  if [[ -r $target ]]; then
    { IFS= read -r first; IFS= read -r value; } < "$target"
    if [[ $first == "$signature" && -n $value ]]; then REPLY=$value; return 0; fi
  fi
  value=$("$executable" generate "$selected") || return
  REPLY=$value
  [[ -n $value ]] || return 1
  # Failure to persist does not prevent a valid theme from working now.
  if zf_mkdir -p -- "$directory"; then
    (umask 077; print -rl -- "$signature" "$value" >| "$temporary") &&
      zf_mv -f -- "$temporary" "$target"
  fi
  [[ -e $temporary ]] && zf_rm -f -- "$temporary"
  REPLY=$value
  return 0
}
