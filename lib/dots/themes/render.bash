# Omarchy-style palette resolution and literal template rendering.
# Globals are shared with core.bash and state.bash.
# shellcheck disable=SC2034
declare -gA DT_META DT_VALUES DT_COLORS

declare -gA DT_SEMANTIC=()
DT_USER_THEMES=${XDG_CONFIG_HOME:-$HOME/.config}/dots/themes
DT_TEMPLATES=${DOTS_THEME_TEMPLATES:-${DT_LIB%/lib/dots/themes}/default/themed}
DT_USER_TEMPLATES=${XDG_CONFIG_HOME:-$HOME/.config}/dots/themed
dt_find_theme() {
  dt_theme_id "$1" || return 1
  DT_THEME_DIR=$DT_ROOT/$1
  if [[ -f $DT_THEME_DIR/colors.toml && -d $DT_USER_THEMES/$1 ]]; then
    dt_error "duplicate bundled and user theme: $1"; return 1
  fi
  if [[ -d $DT_USER_THEMES/$1 ]]; then DT_THEME_DIR=$DT_USER_THEMES/$1; fi
  [[ -f $DT_THEME_DIR/colors.toml || $1 == pywal16-current ]]
}
dt_colors() {
  local file=$1 line key value n=0
  local pair='^[[:space:]]*([a-zA-Z_][a-zA-Z0-9_]*)[[:space:]]*=[[:space:]]*"([^"\\]*)"[[:space:]]*(#.*)?$'
  local literal="^[[:space:]]*([a-zA-Z_][a-zA-Z0-9_]*)[[:space:]]*=[[:space:]]*'([^']*)'[[:space:]]*(#.*)?$"
  DT_SEMANTIC=() DT_MODE=dark
  if [[ $DT_THEME == pywal16 ]]; then
    for key in "${DT_NAMES[@]}"; do DT_SEMANTIC[$key]=${DT_COLORS[$key]}; done
  else
    [[ -f $file && ! -L $file ]] || { dt_error 'theme colors must be a regular file'; return 1; }
    while IFS= read -r line || [[ $line ]]; do
      (( ++n )); line=${line%$'\r'}
      [[ $line =~ ^[[:space:]]*(#.*)?$ ]] && continue
      [[ $line =~ $pair || $line =~ $literal ]] || { dt_error "$file:$n: invalid color assignment"; return 1; }
      key=${BASH_REMATCH[1]} value=${BASH_REMATCH[2]}
      [[ ! ${DT_SEMANTIC[$key]+yes} && ! $value =~ [[:cntrl:]] ]] || { dt_error "$file:$n: duplicate color or control character"; return 1; }
      if [[ $key == mode ]]; then
        [[ $value == light || $value == dark ]] || return 1
      elif [[ ! $value =~ ^#[a-fA-F0-9]{6}$ ]]; then
        # Omarchy desktop-only decorations (e.g. border gradients) are inert.
        case $key in hyprland_*|active_border_color|inactive_border_color) continue ;; *) dt_error "$file:$n: expected #RRGGBB"; return 1 ;; esac
      fi
      DT_SEMANTIC[$key]=$value
    done < "$file"
  fi
  local -a names=(background red green yellow blue magenta cyan foreground muted bright_red bright_green bright_yellow bright_blue bright_magenta bright_cyan bright_foreground)
  for ((n=0;n<16;n++)); do
    key=${names[n]}
    DT_SEMANTIC[$key]=${DT_SEMANTIC[$key]:-${DT_SEMANTIC[color$n]:-}}
  done
  for key in background foreground; do [[ ${DT_SEMANTIC[$key]:-} ]] || { dt_error "missing $key"; return 1; }; done
  DT_SEMANTIC[accent]=${DT_SEMANTIC[accent]:-${DT_SEMANTIC[blue]:-${DT_SEMANTIC[foreground]}}}
  for key in red green yellow blue magenta cyan; do
    DT_SEMANTIC[$key]=${DT_SEMANTIC[$key]:-${DT_SEMANTIC[accent]}}
    DT_SEMANTIC[bright_$key]=${DT_SEMANTIC[bright_$key]:-${DT_SEMANTIC[$key]}}
  done
  DT_SEMANTIC[muted]=${DT_SEMANTIC[muted]:-${DT_SEMANTIC[foreground]}}
  DT_SEMANTIC[selection]=${DT_SEMANTIC[selection]:-${DT_SEMANTIC[selection_background]:-${DT_SEMANTIC[muted]}}}
  for key in dark_background darker_background lighter_background; do DT_SEMANTIC[$key]=${DT_SEMANTIC[$key]:-${DT_SEMANTIC[background]}}; done
  for key in bright_foreground dark_foreground light_foreground cursor selection_foreground; do DT_SEMANTIC[$key]=${DT_SEMANTIC[$key]:-${DT_SEMANTIC[foreground]}}; done
  DT_SEMANTIC[selection_background]=${DT_SEMANTIC[selection_background]:-${DT_SEMANTIC[selection]}}
  DT_SEMANTIC[orange]=${DT_SEMANTIC[orange]:-${DT_SEMANTIC[yellow]}}
  DT_SEMANTIC[brown]=${DT_SEMANTIC[brown]:-${DT_SEMANTIC[muted]}}
  DT_SEMANTIC[error]=${DT_SEMANTIC[error]:-${DT_SEMANTIC[red]}}
  DT_SEMANTIC[warning]=${DT_SEMANTIC[warning]:-${DT_SEMANTIC[yellow]}}
  DT_SEMANTIC[info]=${DT_SEMANTIC[info]:-${DT_SEMANTIC[blue]}}
  DT_SEMANTIC[hint]=${DT_SEMANTIC[hint]:-${DT_SEMANTIC[cyan]}}
  for ((n=0;n<16;n++)); do DT_SEMANTIC[color$n]=${DT_SEMANTIC[${names[n]}]}; done
  dt_rgb "${DT_SEMANTIC[background]}"
  (( DT_R*299+DT_G*587+DT_B*114 < 128000 )) || DT_MODE=light
  DT_MODE=${DT_SEMANTIC[mode]:-$DT_MODE}
  DT_SEMANTIC[mode]=$DT_MODE
}
dt_load() {
  local name=$1 flavor=${2:-} key family
  DT_ID='' DT_THEME_DIR='' DT_SEMANTIC=() DT_ADAPTER=native
  if [[ -d $DT_ROOT/$name/flavors ]]; then
    dt_native_load "$name" "$flavor" || return
    DT_ID=$DT_THEME-$DT_FLAVOR
    if [[ -d $DT_ROOT/$DT_ID || -d $DT_USER_THEMES/$DT_ID ]]; then
      dt_find_theme "$DT_ID" && dt_colors "$DT_THEME_DIR/colors.toml" || return
    fi
  elif dt_find_theme "$name"; then
    DT_ID=$name
    family=$name flavor=default
    if [[ -f $DT_THEME_DIR/theme.toml ]]; then
      dt_parse "$DT_THEME_DIR/theme.toml" metadata || return
      family=${DT_DATA[family]:-$name} flavor=${DT_DATA[flavor]:-default}
    fi
    if [[ -d $DT_ROOT/$family/flavors ]]; then
      dt_native_load "$family" "$flavor" || return
      dt_find_theme "$name" || return
      dt_colors "$DT_THEME_DIR/colors.toml" || return
    else
      DT_THEME=$name DT_FLAVOR=default DT_ADAPTER=generic
      dt_colors "$DT_THEME_DIR/colors.toml" || return
      DT_COLORS=() DT_NAMES=() DT_META=() DT_VALUES=()
      for key in "${!DT_SEMANTIC[@]}"; do
        [[ $key != mode ]] || continue
        DT_COLORS[$key]=${DT_SEMANTIC[$key]}; DT_NAMES+=("$key")
      done
      for key in background foreground muted accent selection error warning info hint; do DT_META["roles.$key"]=$key; done
    fi
  else dt_error "unknown theme: $name"; return 1; fi
}
dt_render() {
  local dir=$1 template filename line rest key value prefix output
  local pattern='\{\{[[:space:]]*([a-zA-Z_][a-zA-Z0-9_]*)[[:space:]]*\}\}'
  local -A rendered=()
  # Only bundled app overrides are trusted. Installed repositories supply colors/images only.
  if [[ $DT_THEME_DIR == "$DT_ROOT/"* ]]; then
    for filename in kitty.conf tmux.conf btop.theme termux.properties bat.tmTheme yazi.toml; do
      if [[ -f $DT_THEME_DIR/$filename && ! -L $DT_THEME_DIR/$filename ]]; then
        cp -- "$DT_THEME_DIR/$filename" "$dir/$filename" || return
        rendered[$filename]=1
      fi
    done
  fi
  for template in "$DT_USER_TEMPLATES/"*.tpl "$DT_TEMPLATES/"*.tpl; do
    [[ -f $template && ! -L $template ]] || continue
    filename=${template##*/}; filename=${filename%.tpl}
    [[ $filename =~ ^[a-zA-Z0-9][a-zA-Z0-9._-]*$ ]] || { dt_error 'invalid template output name'; return 1; }
    case $filename in selection|fingerprint|palette.json|init.*|previous|status|active.new|connectors|bat-cache) dt_error "reserved template output: $filename"; return 1 ;; esac
    [[ ! ${rendered[$filename]:-} ]] || continue
    output=''
    while IFS= read -r line || [[ $line ]]; do
      rest=$line; line=''
      while [[ $rest =~ $pattern ]]; do
        key=${BASH_REMATCH[1]}; prefix=${rest%%"${BASH_REMATCH[0]}"*}
        rest=${rest#*"${BASH_REMATCH[0]}"}
        case $key in
          *_strip) key=${key%_strip}; value=${DT_SEMANTIC[$key]:-}; value=${value#\#} ;;
          *_rgb) key=${key%_rgb}; [[ ${DT_SEMANTIC[$key]:-} ]] || return 1; dt_rgb "${DT_SEMANTIC[$key]}"; value="$DT_R,$DT_G,$DT_B" ;;
          *) value=${DT_SEMANTIC[$key]:-} ;;
        esac
        [[ $value ]] || { dt_error "unknown template color: $key"; return 1; }
        line+=$prefix$value
      done
      line+=$rest
      [[ $line != *'{{'* && $line != *'}}'* ]] || { dt_error "unresolved template expression: $template"; return 1; }
      output+=$line$'\n'
    done < "$template"
    printf '%s' "$output" > "$dir/$filename" || return
    rendered[$filename]=1
  done
  mkdir -p "$dir/yazi" || return
  cp -- "$dir/yazi.toml" "$dir/yazi/flavor.toml" && cp -- "$dir/bat.tmTheme" "$dir/yazi/tmtheme.xml" || return
}
