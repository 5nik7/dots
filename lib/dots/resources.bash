# Lazy, data-only resource styling for Bash human views. No per-path processes.
# shellcheck shell=bash disable=SC2034
_dots_resource_lib=${BASH_SOURCE[0]%/*}
dots::_resource_load() {
  [[ ${_DOTS_RESOURCE_READY:-} ]] && return 0
  _DOTS_RESOURCE_READY=1
  declare -ga _DOTS_RESOURCE_ROWS=() _DOTS_RESOURCE_ICONS=()
  declare -gA _DOTS_RESOURCE_TYPES=()
  declare -gA _DOTS_RESOURCE_SUFFIX_CODE=() _DOTS_RESOURCE_SUFFIX_ORDER=() _DOTS_RESOURCE_SUFFIX_SIZES=()
  declare -gA _DOTS_RESOURCE_MIME_CODE=() _DOTS_RESOURCE_MIME_ORDER=()
  local root=${XDG_STATE_HOME:-$HOME/.local/state}/dots/current/theme data='' header group key code mode extra valid=1 line
  if [[ -f $root/file-styles.tsv && ! -L $root/file-styles.tsv ]]; then
    IFS= read -r -N 2097153 data < "$root/file-styles.tsv" || :
    data=${data%$'\n'}
    if (( ${#data} <= 2097152 )); then
      {
        IFS= read -r header
        [[ $header == $'dots-file-styles\t1' ]] || valid=0
        while IFS=$'\t' read -r group key code mode extra; do
          if [[ ! $group =~ ^(type|extension|mime|suffix|default_mime)$ || ! $key ||
                ! $code =~ ^[0-9\;]{1,128}$ || ! $mode =~ ^(-|exact|fold)$ || $extra || $key == *[$'\001'-$'\037'$'\177']* ]]; then
            valid=0; break
          fi
          if [[ $group == type && ! $key =~ ^[a-z][a-z0-9_]*$ ]]; then valid=0; break; fi
          _DOTS_RESOURCE_ROWS+=("$group" "$key" "$code" "$mode")
        done
      } <<< "$data"
    else valid=0; fi
    (( valid )) || _DOTS_RESOURCE_ROWS=()
  fi
  if ((${#_DOTS_RESOURCE_ROWS[@]} == 0)) && [[ -f $root/ls_colors && ! -L $root/ls_colors ]]; then
    data=''; IFS= read -r -N 2097153 data < "$root/ls_colors" || :
    if (( ${#data} <= 2097152 )); then
      local -a entries=() suffixes=()
      local -A kinds=([fi]=file [di]=dir [ln]=symlink [or]=broken_symlink [mi]=missing [ex]=executable [pi]=fifo [so]=socket [bd]=block_device [cd]=character_device)
      local -A latest=() groups=() exact=() shadow=()
      local -a members=()
      local i folded newer older a b folded_match
      data=${data%$'\n'}; IFS=: read -r -a entries <<< "$data"
      for ((i=${#entries[@]}-1; i>=0; i--)); do
        line=${entries[i]}; key=${line%%=*}; code=${line#*=}
        [[ $line == *=* && $key != *\\* && $key != *'^'* && $code =~ ^[0-9\;]{1,128}$ ]] || continue
        if [[ ${kinds[$key]:-} ]]; then
          [[ ${_DOTS_RESOURCE_TYPES[${kinds[$key]}]+yes} ]] || _DOTS_RESOURCE_TYPES[${kinds[$key]}]=$code
        elif [[ $key == \** ]]; then
          key=${key:1}; [[ $key && ! ${latest[$key]+yes} ]] || continue
          latest[$key]=$code; folded=${key,,}
          groups[$folded]+=" ${#suffixes[@]}"
          suffixes+=("$key" "$code")
        fi
      done
      for folded in "${!groups[@]}"; do
        read -r -a members <<< "${groups[$folded]}"
        for ((a=0; a<${#members[@]}; a++)); do
          newer=${members[a]}; [[ ! ${shadow[$newer]:-} ]] || continue
          folded_match=0
          for ((b=a+1; b<${#members[@]}; b++)); do
            older=${members[b]}; [[ ! ${shadow[$older]:-} ]] || continue
            if (( folded_match )); then shadow[$older]=1
            elif [[ ${suffixes[newer+1]} == "${suffixes[older+1]}" ]]; then
              shadow[$older]=1; folded_match=1
            else exact[$newer]=1; exact[$older]=1; fi
          done
        done
      done
      for ((i=0; i<${#suffixes[@]}; i+=2)); do
        [[ ! ${shadow[$i]:-} ]] || continue
        key=${suffixes[i]}; mode='fold'
        [[ ! ${exact[$i]:-} ]] || mode=exact
        _DOTS_RESOURCE_ROWS+=(suffix "$key" "${suffixes[i+1]}" "$mode")
      done
    fi
  fi
  local i
  for ((i=0; i<${#_DOTS_RESOURCE_ROWS[@]}; i+=4)); do
    group=${_DOTS_RESOURCE_ROWS[i]}; key=${_DOTS_RESOURCE_ROWS[i+1]}; code=${_DOTS_RESOURCE_ROWS[i+2]}; mode=${_DOTS_RESOURCE_ROWS[i+3]}
    case $group in
      type) _DOTS_RESOURCE_TYPES[$key]=$code ;;
      extension|suffix)
        _DOTS_RESOURCE_SUFFIX_SIZES[${#key}]=1
        [[ $mode == exact ]] || { mode='fold'; key=${key,,}; }
        key=$mode:$key
        if [[ ! ${_DOTS_RESOURCE_SUFFIX_CODE[$key]+yes} ]]; then
          _DOTS_RESOURCE_SUFFIX_CODE[$key]=$code; _DOTS_RESOURCE_SUFFIX_ORDER[$key]=$i
        fi ;;
      mime|default_mime)
        if [[ ! ${_DOTS_RESOURCE_MIME_CODE[$key]+yes} ]]; then
          _DOTS_RESOURCE_MIME_CODE[$key]=$code; _DOTS_RESOURCE_MIME_ORDER[$key]=$i
        fi ;;
    esac
  done
  if [[ -f $_dots_resource_lib/resources.tsv ]]; then
    while IFS=$'\t' read -r group key code mode extra; do
      [[ $group != \#* && $key && $code && $mode ]] || continue
      if [[ $extra ]]; then dots::icon "$code" "$extra"; code=$REPLY; fi
      _DOTS_RESOURCE_ICONS+=("$group" "$key" "$code" "$mode")
    done < "$_dots_resource_lib/resources.tsv"
  fi
}

# Sets plain text, style and colored REPLY separately so callers can wrap safely.
# Arguments: actual path, optional display path, optional known kind, optional MIME.
dots::resource() {
  local actual=$1 shown=${2-$1} kind=${3:-} mime=${4:-} icon='' code=95 guessed='' name=${1##*/}
  local i group key value inferred size folded best
  dots::style
  if ! dots::human || [[ ! $DOTS_UI_RESET && $DOTS_UI_INFO == '[i]' ]]; then
    dots::text "$shown"; DOTS_RESOURCE_TEXT=$REPLY DOTS_RESOURCE_STYLE=''; return
  fi
  dots::_resource_load
  if [[ ! $kind ]]; then
    if [[ -L $actual ]]; then kind=symlink; [[ -e $actual ]] || kind=broken_symlink
    elif [[ -d $actual ]]; then kind=dir
    elif [[ -p $actual ]]; then kind=fifo
    elif [[ -S $actual ]]; then kind=socket
    elif [[ -b $actual ]]; then kind=block_device
    elif [[ -c $actual ]]; then kind=character_device
    elif [[ ! -e $actual ]]; then kind=missing
    elif [[ -x $actual ]]; then kind=executable
    else kind='file'; fi
    if [[ ${_DOTS_RESOURCE_TYPES[$kind]:-x} == 0 || ${_DOTS_RESOURCE_TYPES[$kind]:-x} == 00 ]]; then
      case $kind in executable) kind='file';; broken_symlink) kind=symlink;; esac
    fi
  fi
  case $kind in dir) code='1;94';; symlink) code=96;; broken_symlink) code=91;; executable) code=92;; fifo|block_device|character_device) code=93;; esac
  code=${_DOTS_RESOURCE_TYPES[$kind]:-$code}
  for ((i=0; i<${#_DOTS_RESOURCE_ICONS[@]}; i+=4)); do
    group=${_DOTS_RESOURCE_ICONS[i]}; key=${_DOTS_RESOURCE_ICONS[i+1]}; value=${_DOTS_RESOURCE_ICONS[i+2]}; inferred=${_DOTS_RESOURCE_ICONS[i+3]}
    if [[ $group == kind && $key == "$kind" ]]; then icon=$value; fi
    if [[ $kind == file || $kind == missing ]]; then
      if [[ $group == name && $name == "$key" || $group == suffix && ${name,,} == *"${key,,}" ]]; then
        icon=$value; guessed=$inferred; break
      fi
    fi
  done
  mime=${mime:-$guessed}
  if [[ $kind == file || $kind == missing ]]; then
    if [[ $mime && ! $guessed ]]; then
      for ((i=0; i<${#_DOTS_RESOURCE_ICONS[@]}; i+=4)); do
        key=${_DOTS_RESOURCE_ICONS[i+1]}
        if [[ ${_DOTS_RESOURCE_ICONS[i]} == mime && ( $mime == "$key" || $key == */\* && ${mime%/*} == "${key%/*}" ) ]]; then icon=${_DOTS_RESOURCE_ICONS[i+2]}; break; fi
      done
    fi
    # Preserve table priority across suffix and MIME groups without scanning all
    # rules for each row. A filename has only a few possible suffix lengths.
    best=2147483647; folded=${name,,}
    for size in "${!_DOTS_RESOURCE_SUFFIX_SIZES[@]}"; do
      (( size <= ${#name} )) || continue
      for key in "exact:${name: -size}" "fold:${folded: -size}"; do
        if [[ ${_DOTS_RESOURCE_SUFFIX_ORDER[$key]+yes} ]] && (( ${_DOTS_RESOURCE_SUFFIX_ORDER[$key]} < best )); then
          best=${_DOTS_RESOURCE_SUFFIX_ORDER[$key]}; code=${_DOTS_RESOURCE_SUFFIX_CODE[$key]}
        fi
      done
    done
    if [[ $mime ]]; then
      for key in "$mime" "${mime%/*}/*"; do
        if [[ ${_DOTS_RESOURCE_MIME_ORDER[$key]+yes} ]] && (( ${_DOTS_RESOURCE_MIME_ORDER[$key]} < best )); then
          best=${_DOTS_RESOURCE_MIME_ORDER[$key]}; code=${_DOTS_RESOURCE_MIME_CODE[$key]}
        fi
      done
    fi
  fi
  dots::text "$shown"; DOTS_RESOURCE_TEXT=$REPLY
  if [[ $DOTS_UI_INFO != '[i]' ]]; then [[ ! $icon ]] || DOTS_RESOURCE_TEXT="$icon $DOTS_RESOURCE_TEXT"; fi
  DOTS_RESOURCE_STYLE=''
  [[ ! $DOTS_UI_RESET ]] || printf -v DOTS_RESOURCE_STYLE '\e[%sm' "$code"
  REPLY=$DOTS_RESOURCE_STYLE$DOTS_RESOURCE_TEXT$DOTS_UI_RESET
}

# Optional sixth argument styles the label independently from the resource.
dots::resource_row() {
  local label=$1 actual=$2 shown=${3-} kind=${4:-} mime=${5:-} label_style=${6-${DOTS_UI_BLUE:-}}
  if [[ $# -lt 3 ]]; then dots::path "$actual"; shown=$REPLY; fi
  dots::resource "$actual" "$shown" "$kind" "$mime"
  [[ $# -ge 6 ]] || label_style=$DOTS_UI_BLUE
  [[ $DOTS_UI_RESET ]] || label_style=''
  if dots::human && [[ ${_DOTS_FORMATTING[label_width]+set} ]]; then
    dots::aligned_row "$label" "$DOTS_RESOURCE_TEXT" "$label_style" "$DOTS_RESOURCE_STYLE"
    return
  fi
  local text=$DOTS_RESOURCE_TEXT color=$DOTS_RESOURCE_STYLE columns=${COLUMNS:-80} width=26 room part='' char i size used=0 prefix prefix_width
  [[ $columns =~ ^[0-9]+$ ]] || columns=80
  columns=$((10#$columns)); (( columns >= 20 )) || columns=20
  dots::text "$label"; label=$REPLY
  if (( columns < 60 || ${#label} > width )) || [[ $label == *[!\ -~]* ]]; then
    dots::line "$label" "$label_style" 2 "$columns"
    prefix='      '; prefix_width=6
  else
    printf -v prefix '  %s%-26s%s ' "$label_style" "$label" "$DOTS_UI_RESET"
    prefix_width=29
  fi
  room=$((columns-prefix_width)); (( room >= 8 )) || room=8
  for ((i=0; i<${#text}; i++)); do
    char=${text:i:1}; size=1; [[ $char == [\ -~] ]] || size=2
    if (( used+size > room && used )); then
      dots::breakline "$part" "$room"
      printf '%s%s%s%s\n' "$prefix" "$color" "$REPLY" "$DOTS_UI_RESET"
      printf -v prefix '%*s' "$prefix_width" ''; part=$DOTS_LINE_TAIL used=$DOTS_LINE_CELLS
    fi
    part+=$char; ((used+=size))
  done
  printf '%s%s%s%s\n' "$prefix" "$color" "$part" "$DOTS_UI_RESET"
}
