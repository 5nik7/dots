# Core-owned metadata-help branding; does not execute the Anodize extension.
# Default text uses Bash builtins, plus optional stty for actual terminal size.
dots::anodize_logo_error() {
  printf '/\\ ANODIZE\n' >&2
  dots_error "$*"
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
      --logo-layout:auto|--logo-layout:horizontal|--logo-layout:stacked|--logo-layout:icon) layout=$value ;;
      --logo:*) dots::anodize_logo_error 'Expected --logo=text|auto|kitty|chafa'; return 2 ;;
      *) dots::anodize_logo_error 'Expected --logo-layout=auto|horizontal|stacked|icon'; return 2 ;;
    esac
  done
  case $mode in text|auto|kitty|chafa) ;; *) mode=text ;; esac
  case $layout in auto|horizontal|stacked|icon) ;; *) layout=auto ;; esac
  dots::style
  if [[ $mode != text && -t 1 && ${TERM:-dumb} != dumb && $DOTS_UI_RESET ]] && command -v python3 >/dev/null 2>&1; then
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
  width=$((10#$columns - 1)) height=$((10#$rows / 3))
  (( width > 0 )) || width=1
  (( height > 0 )) || height=1
  (( height <= 8 )) || height=8
  if [[ ! -t 1 || ${TERM:-dumb} == dumb ]] || (( height < 6 || width < 19 )); then
    layout=compact
  elif [[ $layout == auto ]]; then
    if (( 10#$columns >= 80 )); then layout=horizontal; else layout=stacked; fi
  fi
  [[ $layout != horizontal ]] || (( width >= 39 )) || layout=stacked
  [[ $layout != stacked ]] || (( height >= 8 )) || layout=icon
  local -a lines=()
  file=$DOTS_LIB_DIR/anodize/assets/$layout.txt
  if [[ $layout != compact && -r $file ]]; then
    while IFS='' read -r line || [[ -n $line ]]; do lines+=("$line"); done < "$file"
    ((${#lines[@]} <= height)) || lines=()
    for line in "${lines[@]}"; do
      if ((${#line} > width)); then lines=(); break; fi
    done
  fi
  if ((${#lines[@]} == 0)); then
    if (( width >= 16 && height >= 3 )); then
      lines=("  /\\" ' /_ \   ANODIZE' "/_/\\_\\")
    elif (( width >= 11 )); then lines=(' /\ ANODIZE')
    elif (( width >= 2 )); then lines=("/\\")
    else lines=('A'); fi
  fi
  for line in "${lines[@]}"; do
    if [[ $DOTS_UI_RESET ]]; then printf '\e[95m%s%s\n' "$line" "$DOTS_UI_RESET"
    else printf '%s\n' "$line"; fi
  done
}
