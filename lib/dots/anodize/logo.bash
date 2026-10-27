# Core-owned metadata-help branding; does not execute the Anodize extension.
# Default text uses Bash builtins, plus optional stty for actual terminal size.
dots::anodize_logo_error() {
  # Valid options avoid reentering the error path; no graphics for diagnostics.
  local error_layout=${layout:-${ANODIZE_LOGO_LAYOUT:-auto}}
  case $error_layout in auto|base|horizontal|stacked|icon) ;; *) error_layout=auto ;; esac
  [[ $error_layout != auto ]] || error_layout=base
  dots::anodize_logo --logo=text --logo-layout="$error_layout" >&2
  dots_error "$*"
}

# Dynamic output variables asset_lines/asset_width belong to the caller.
dots::anodize_text_asset() {
  local LC_ALL=C.UTF-8
  local file=$1 width=$2 height=$3 line visible='' cells='^[ -~⠀-⣿]*$'
  asset_lines=() asset_width=0
  [[ -r $file && -f $file ]] || return 1
  while IFS='' read -r line || [[ -n $line ]]; do
    [[ $line =~ $cells ]] || return 1
    (( ${#line} <= width && ${#asset_lines[@]} < height )) || return 1
    asset_lines+=("$line")
    (( ${#line} <= asset_width )) || asset_width=${#line}
    visible+=${line//[ ⠀]/}
  done < "$file"
  [[ -n $visible ]]
}

# Match text_gradient.py without Python, shell startup, or theme resolution.
# lines/text_layout are the caller's selected, validated artwork.
dots::anodize_gradient() {
  local LC_ALL=C.UTF-8
  local file=${XDG_STATE_HOME:-$HOME/.local/state}/dots/current/theme/shell.tsv
  local data='' row key value hint='' info='' accent=''
  [[ -f $file && -r $file && ! -L $file ]] || return 1
  IFS= read -r -N 2097153 data 2>/dev/null < "$file" || :
  (( ${#data} <= 2097152 )) || return 1
  while IFS= read -r row || [[ -n $row ]]; do
    case $row in hint$'\thex\t'*|info$'\thex\t'*|accent$'\thex\t'*) ;; *) continue ;; esac
    key=${row%%$'\t'*}; value=${row#*$'\thex\t'}
    [[ $value =~ ^#[a-fA-F0-9]{6}$ ]] || return 1
    case $key in
      hint) [[ ! $hint ]] || return 1; hint=$value ;;
      info) [[ ! $info ]] || return 1; info=$value ;;
      accent) [[ ! $accent ]] || return 1; accent=$value ;;
    esac
  done <<< "$data"
  [[ $hint && $info && $accent ]] || return 1
  local -a start=() middle=() end=() rgb=()
  local -a xmin=(1000000 1000000) ymin=(1000000 1000000) xmax=(-1 -1) ymax=(-1 -1)
  local -a low=(1000000000 1000000000) high=(-1 -1)
  local x y group char score span step dx dy i code previous part
  for i in 1 3 5; do
    start+=("$((16#${hint:i:2}))"); middle+=("$((16#${info:i:2}))"); end+=("$((16#${accent:i:2}))")
  done
  for ((y=0; y<${#lines[@]}; y++)); do
    for ((x=0; x<${#lines[y]}; x++)); do
      char=${lines[y]:x:1}; [[ $char != ' ' && $char != '⠀' ]] || continue
      group=0
      if [[ $text_layout == horizontal && $x -ge 16 || $text_layout == stacked && $y -ge 9 ]]; then group=1; fi
      (( x >= xmin[group] )) || xmin[group]=$x
      (( x <= xmax[group] )) || xmax[group]=$x
      (( y >= ymin[group] )) || ymin[group]=$y
      (( y <= ymax[group] )) || ymax[group]=$y
    done
  done
  for ((y=0; y<${#lines[@]}; y++)); do
    for ((x=0; x<${#lines[y]}; x++)); do
      char=${lines[y]:x:1}; [[ $char != ' ' && $char != '⠀' ]] || continue
      group=0
      if [[ $text_layout == horizontal && $x -ge 16 || $text_layout == stacked && $y -ge 9 ]]; then group=1; fi
      dx=$((xmax[group]-xmin[group])); (( dx > 0 )) || dx=1
      dy=$((ymax[group]-ymin[group])); (( dy > 0 )) || dy=1
      score=$(((x-xmin[group])*dy+(ymax[group]-y)*dx))
      (( score >= low[group] )) || low[group]=$score
      (( score <= high[group] )) || high[group]=$score
    done
  done
  for ((y=0; y<${#lines[@]}; y++)); do
    previous='' part=''
    for ((x=0; x<${#lines[y]}; x++)); do
      char=${lines[y]:x:1}
      if [[ $char != ' ' && $char != '⠀' ]]; then
        group=0
        if [[ $text_layout == horizontal && $x -ge 16 || $text_layout == stacked && $y -ge 9 ]]; then group=1; fi
        dx=$((xmax[group]-xmin[group])); (( dx > 0 )) || dx=1
        dy=$((ymax[group]-ymin[group])); (( dy > 0 )) || dy=1
        step=$((2*((x-xmin[group])*dy+(ymax[group]-y)*dx-low[group])))
        span=$((high[group]-low[group])); (( span > 0 )) || span=1
        if (( step <= span )); then
          for ((i=0; i<3; i++)); do rgb[i]=$(((start[i]*(span-step)+middle[i]*step+span/2)/span)); done
        else
          step=$((step-span))
          for ((i=0; i<3; i++)); do rgb[i]=$(((middle[i]*(span-step)+end[i]*step+span/2)/span)); done
        fi
        printf -v code '\e[38;2;%d;%d;%dm' "${rgb[@]}"
        [[ $code == "$previous" ]] || part+=$code
        previous=$code
      fi
      part+=$char
    done
    [[ ! $previous ]] || part+=$DOTS_UI_RESET
    printf '%s\n' "$part"
  done
  return 0
}

dots::anodize_logo() {
  local mode=${ANODIZE_LOGO:-text} layout=${ANODIZE_LOGO_LAYOUT:-auto} token value status
  while (($#)); do
    token=$1; shift
    [[ $token != -- ]] || break
    case $token in
      --logo|--logo-layout)
        if (($# == 0)); then dots::anodize_logo_error "$token requires a value"; return 2; fi
        value=$1; shift ;;
      --logo=*|--logo-layout=*) value=${token#*=}; token=${token%%=*} ;;
      *) continue ;;
    esac
    case $token:$value in
      --logo:text|--logo:auto|--logo:kitty|--logo:chafa) mode=$value ;;
      --logo-layout:auto|--logo-layout:base|--logo-layout:horizontal|--logo-layout:stacked|--logo-layout:icon) layout=$value ;;
      --logo:*) dots::anodize_logo_error 'Expected --logo=text|auto|kitty|chafa'; return 2 ;;
      *) dots::anodize_logo_error 'Expected --logo-layout=auto|base|horizontal|stacked|icon'; return 2 ;;
    esac
  done
  case $mode in text|auto|kitty|chafa) ;; *) mode=text ;; esac
  case $layout in auto|base|horizontal|stacked|icon) ;; *) layout=auto ;; esac
  dots::style
  if [[ $mode != text && -t 1 && ${TERM:-dumb} != dumb && ${DOTS_ICONS:-auto} != never && $DOTS_UI_RESET ]] && command -v python3 >/dev/null 2>&1; then
    ANODIZE_LOGO=$mode ANODIZE_LOGO_LAYOUT=$layout python3 -B "$DOTS_LIB_DIR/anodize/logo.py"
    status=$?
    (( status != 0 )) || return 0
    (( status != 130 )) || return 130
  fi
  local columns=${COLUMNS:-80} rows=${LINES:-24} size width height line file tty_fd
  if [[ -t 1 ]] && command -v stty >/dev/null 2>&1; then
    exec {tty_fd}>&1
    size=$(stty size <&"$tty_fd" 2>/dev/null) || size=''
    exec {tty_fd}>&-
    if [[ $size =~ ^([1-9][0-9]*)\ ([1-9][0-9]*)$ ]]; then
      rows=${BASH_REMATCH[1]} columns=${BASH_REMATCH[2]}
    fi
  fi
  [[ $columns =~ ^[0-9]{1,6}$ ]] && (( 10#$columns > 0 )) || columns=80
  [[ $rows =~ ^[0-9]{1,6}$ ]] && (( 10#$rows > 0 )) || rows=24
  width=$((10#$columns - 1)) height=$((10#$rows / 2))
  (( width > 0 )) || width=1
  (( height > 0 )) || height=1
  (( height <= 16 )) || height=16
  local -a lines=() asset_lines=() candidates=()
  local asset_width best_width=-1 number text_layout=base
  # LOGO2 is optional for wide help; LOGO1 is the unconditional fallback.
  # Explicit stacked/icon layouts alone may select older, larger artwork.
  height=16
  case $layout in
    auto|horizontal) candidates=(horizontal) ;;
    stacked) candidates=(stacked) ;;
  esac
  for file in "${candidates[@]}"; do
    if dots::anodize_text_asset "$DOTS_LIB_DIR/anodize/assets/$file.txt" "$width" "$height"; then
      lines=("${asset_lines[@]}"); text_layout=$file; break
    fi
  done
  if ((${#lines[@]} == 0)) && [[ $layout == icon || $layout == stacked ]]; then
    for file in "$DOTS_LIB_DIR"/anodize/assets/logo-*.txt; do
      number=${file##*/logo-}; number=${number%.txt}
      [[ $number =~ ^[0-9]+$ && ! $number =~ ^0+$ ]] || continue
      if dots::anodize_text_asset "$file" "$width" "$height" && (( asset_width > best_width )); then
        lines=("${asset_lines[@]}"); best_width=$asset_width; text_layout=icon
      fi
    done
  fi
  if ((${#lines[@]} == 0)); then
    lines=(
      '⠀⠀⠀⠀⠀⠀⠀⣰⡄⠀⠀⠀⠀⠀⠀'
      '⠀⠀⠀⠀⠀⢀⣼⣿⣿⣄⠀⠀⠀⠀⠀'
      '⠀⠀⠀⠀⠠⢾⡿⠃⠘⣿⣆⠀⠀⠀⠀'
      '⠀⠀⠀⣰⣷⣦⣤⣀⠀⠘⣿⣦⠀⠀⠀'
      '⠀⠀⣴⣿⡟⠙⠻⢿⣿⣶⣾⣿⣧⡀⠀'
      '⢀⣾⣿⠏⠀⠀⠀⠀⠀⠉⠛⠿⣿⣷⡀'
    )
  fi
  if [[ $DOTS_UI_RESET ]] && dots::anodize_gradient; then return 0; fi
  for line in "${lines[@]}"; do
    if [[ $DOTS_UI_RESET ]]; then printf '\e[95m%s%s\n' "$line" "$DOTS_UI_RESET"
    else printf '%s\n' "$line"; fi
  done
}
