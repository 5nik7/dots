# Core-owned metadata-help branding; does not execute the Anodize extension.
# Default text uses Bash builtins, plus optional stty for actual terminal size.
dots::anodize_logo_error() {
  # Valid options avoid reentering the error path; no graphics for diagnostics.
  local error_layout=${layout:-${ANODIZE_LOGO_LAYOUT:-auto}}
  case $error_layout in auto|horizontal|stacked|icon) ;; *) error_layout=auto ;; esac
  dots::anodize_logo --logo=text --logo-layout="$error_layout" >&2
  dots_error "$*"
}

# Dynamic output variables asset_lines/asset_width belong to the caller.
dots::anodize_text_asset() {
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
  local asset_width best_width=-1 number sample='⣿' encoding=${PYTHONIOENCODING:-utf-8} unicode=1
  encoding=${encoding%%:*}
  case ${encoding,,} in utf8|utf-8) ;; *) unicode=0 ;; esac
  if [[ -t 1 && ${TERM:-dumb} != dumb && ${DOTS_ICONS:-auto} != never && ${#sample} == 1 && $unicode == 1 ]]; then
    case $layout in
      auto) candidates=(horizontal stacked) ;;
      horizontal|stacked) candidates=("$layout") ;;
    esac
    for file in "${candidates[@]}"; do
      if dots::anodize_text_asset "$DOTS_LIB_DIR/anodize/assets/$file.txt" "$width" "$height"; then
        lines=("${asset_lines[@]}"); break
      fi
    done
    if ((${#lines[@]} == 0)); then
      for file in "$DOTS_LIB_DIR"/anodize/assets/logo-*.txt; do
        number=${file##*/logo-}; number=${number%.txt}
        [[ $number =~ ^[0-9]+$ && ! $number =~ ^0+$ ]] || continue
        if dots::anodize_text_asset "$file" "$width" "$height" && (( asset_width > best_width )); then
          lines=("${asset_lines[@]}"); best_width=$asset_width
        fi
      done
    fi
    if ((${#lines[@]} == 0)) && dots::anodize_text_asset "$DOTS_LIB_DIR/anodize/assets/logo.txt" "$width" "$height"; then
      lines=("${asset_lines[@]}")
    fi
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
