# Shared Bash theme data engine. Palette input is never evaluated as shell code.
DT_ROOT=${DOTHEMES:-${THEMES:-${DT_LIB%/lib/dots/themes}/themes}}
DT_STATE=${XDG_STATE_HOME:-$HOME/.local/state}/dots/themes
# Shared with the completion provider.
# shellcheck disable=SC2034
DT_FORMATS=(name hex rgb r g b rgb-r rgb-g rgb-b luminance brightness cmyk ansi-8bit ansi-8bit-value ansi-8bit-escapecode ansi-24bit ansi-24bit-escapecode esc)
declare -A DT_DATA=() DT_COLORS=() DT_META=() DT_VALUES=() DT_LINES=() DT_META_LINES=()
declare -a DT_KEYS=() DT_NAMES=()
dt_error() { printf 'dots themes: %s\n' "$*" >&2; return 1; }
dt_id() { [[ $1 =~ ^[a-z][a-z0-9_]*$ ]]; }
dt_theme_id() { [[ $1 =~ ^[a-z][a-z0-9_]*(-[a-z0-9_]+)*$ ]]; }
dt_key() { [[ $1 =~ ^[a-zA-Z_][a-zA-Z0-9_]*$ ]]; }
# Flavors do not contain hyphens; split persisted IDs at the final delimiter.
dt_split() {
  local id=$1
  if [[ ${2:-} != persisted && -f $DT_ROOT/$id/theme.toml ]]; then DT_THEME=$id DT_FLAVOR=''
  else DT_THEME=${id%-*} DT_FLAVOR=${id##*-}; fi
  dt_theme_id "$DT_THEME" && { [[ -z $DT_FLAVOR ]] || dt_id "$DT_FLAVOR"; }
}
dt_supported() {
  [[ ${DT_ADAPTER:-native} != generic ]] || return 0
  [[ ${DT_META[integrations.nvim]:-} == "$DT_THEME" ]] || return 1
  case $DT_THEME:$DT_FLAVOR in
    catppuccin:mocha|catppuccin:macchiato|catppuccin:frappe|catppuccin:latte|tokyonight:night|tokyonight:storm|tokyonight:moon|tokyonight:day|rose-pine:main|rose-pine:moon|rose-pine:dawn|kanagawa:wave|kanagawa:dragon|kanagawa:lotus|gruvbox:dark|gruvbox:light|pywal16:current) return 0 ;;
    *) return 1 ;;
  esac
}
dt_parse() {
  local file=$1 mode=$2 line section='' key value full n=0
  local table='^[[:space:]]*\[([a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)?)\][[:space:]]*(#.*)?$'
  local pair='^[[:space:]]*([a-zA-Z_][a-zA-Z0-9_]*)[[:space:]]*=[[:space:]]*"([^"\\]*)"[[:space:]]*(#.*)?$'
  local literal="^[[:space:]]*([a-zA-Z_][a-zA-Z0-9_]*)[[:space:]]*=[[:space:]]*'([^']*)'[[:space:]]*(#.*)?$"
  local -A sections=()
  DT_DATA=() DT_KEYS=() DT_LINES=()
  [[ -f $file && -r $file ]] || { dt_error "cannot read $file"; return 1; }
  while IFS= read -r line || [[ -n $line ]]; do
    (( ++n )); line=${line%$'\r'}
    [[ $line =~ ^[[:space:]]*(#.*)?$ ]] && continue
    if [[ $line =~ $table ]]; then
      section=${BASH_REMATCH[1]}
      [[ $mode == metadata && ( $section == roles || $section == roles.* || $section == integrations ) && ! ${sections[$section]+yes} ]] || { dt_error "$file:$n: unsupported or duplicate table"; return 1; }
      sections[$section]=1; continue
    fi
    if [[ $line =~ $pair || $line =~ $literal ]]; then
      key=${BASH_REMATCH[1]} value=${BASH_REMATCH[2]} full=${section:+$section.}${BASH_REMATCH[1]}
      [[ ! ${DT_DATA[$full]+yes} && ! $value =~ [[:cntrl:]] ]] || { dt_error "$file:$n: duplicate key or control character"; return 1; }
      if [[ $mode == palette ]]; then
        [[ $value =~ ^#[a-fA-F0-9]{6}$ ]] || { dt_error "$file:$n: expected #RRGGBB"; return 1; }
      elif [[ $section == roles || $section == roles.* ]]; then
        dt_key "$value" || { dt_error "$file:$n: expected a color name"; return 1; }
      elif [[ $full != name && $full != source && $full != default_flavor && $full != integrations.nvim && $full != integrations.vivid && $full != family && $full != flavor ]]; then
        dt_error "$file:$n: unsupported metadata key $full"; return 1
      fi
      DT_DATA[$full]=$value; DT_LINES[$full]=$n; DT_KEYS+=("$full")
    else dt_error "$file:$n: unsupported TOML syntax"; return 1
    fi
  done < "$file"
  ((${#DT_KEYS[@]})) || { dt_error "$file: empty data"; return 1; }
}
dt_native_load() {
  local theme=$1 flavor=${2:-} key role
  dt_theme_id "$theme" || { dt_error 'invalid theme identifier'; return 1; }
  dt_parse "$DT_ROOT/$theme/theme.toml" metadata || return
  DT_META=() DT_META_LINES=(); for key in "${DT_KEYS[@]}"; do DT_META[$key]=${DT_DATA[$key]}; DT_META_LINES[$key]=${DT_LINES[$key]}; done
  flavor=${flavor:-${DT_META[default_flavor]:-}}
  dt_id "$flavor" || { dt_error 'invalid or missing flavor'; return 1; }
  if [[ ${DT_META[source]:-} ]]; then
    [[ $theme == pywal16 && $flavor == current && ${DT_META[source]} == pywal16 ]] || { dt_error 'unsupported palette source'; return 1; }
    source "$DT_LIB/pywal.bash"
    dt_pywal_load || return
  else dt_parse "$DT_ROOT/$theme/flavors/$flavor.toml" palette || return; fi
  # Resolve flavor-specific roles over the family defaults.
  for key in "${!DT_META[@]}"; do
    [[ $key == roles.$flavor.* ]] || continue
    role=roles.${key##*.}
    DT_META[$role]=${DT_META[$key]} DT_META_LINES[$role]=${DT_META_LINES[$key]}
  done
  DT_THEME=$theme DT_FLAVOR=$flavor DT_NAMES=("${DT_KEYS[@]}") DT_COLORS=() DT_VALUES=()
  for key in "${DT_NAMES[@]}"; do DT_COLORS[$key]=${DT_DATA[$key]}; done
  for key in "${!DT_META[@]}"; do
    [[ $key == roles.* && ${key#roles.} != *.* ]] || continue
    role=${DT_META[$key]}
    [[ ${DT_COLORS[$role]+yes} ]] || { dt_error "$DT_ROOT/$theme/theme.toml:${DT_META_LINES[$key]}: role $key references missing color $role"; return 1; }
  done
  if [[ $theme == catppuccin ]]; then
    for key in rosewater flamingo pink mauve red maroon peach yellow green teal sky sapphire blue lavender text subtext1 subtext0 overlay2 overlay1 overlay0 surface2 surface1 surface0 base mantle crust; do
      [[ ${DT_COLORS[$key]+yes} ]] || { dt_error "missing Catppuccin color $key"; return 1; }
    done
  fi
  for role in background foreground muted accent selection error warning info hint; do
    [[ ${DT_META[roles.$role]+yes} ]] || { dt_error "missing role $role"; return 1; }
  done
}
dt_generation() {
  DT_GENERATION=''
  local active=${XDG_STATE_HOME:-$HOME/.local/state}/dots/current/theme target
  if [[ -e $active || -L $active ]]; then
    [[ -L $active ]] || { dt_error 'invalid active theme'; return 1; }
    # Usually the compatibility token and stable link agree. Verify their inode
    # identity with Bash builtins; readlink is only needed during publication.
    if [[ -f $DT_STATE/current && ! -L $DT_STATE/current ]] && IFS= read -r DT_GENERATION < "$DT_STATE/current"; then
      target=$DT_STATE/generations/$DT_GENERATION
      if [[ $DT_GENERATION =~ ^g\.[a-zA-Z0-9]+$ && -d $target && ! -L $target && $active -ef $target ]]; then
        return 0
      fi
    fi
    target=$(readlink -- "$active") || return
    DT_GENERATION=${target##*/}
    [[ $target == "$DT_STATE/generations/$DT_GENERATION" && $DT_GENERATION =~ ^g\.[a-zA-Z0-9]+$ && -d $target && ! -L $target ]] || { dt_error 'invalid active theme'; return 1; }
    return 0
  fi
  [[ -e $DT_STATE/current || -L $DT_STATE/current ]] || return 0
  [[ -f $DT_STATE/current && ! -L $DT_STATE/current ]] || { dt_error 'invalid active selection'; return 1; }
  IFS= read -r DT_GENERATION < "$DT_STATE/current" || return 1
  [[ $DT_GENERATION =~ ^g\.[a-zA-Z0-9]+$ && -d $DT_STATE/generations/$DT_GENERATION && ! -L $DT_STATE/generations/$DT_GENERATION ]] || { dt_error 'invalid theme generation'; return 1; }
}
dt_selected() {
  local file id
  if [[ ${DOTS_THEME_SELECTION:-} ]]; then
    id=$DOTS_THEME_SELECTION
    dt_split "$id" || { dt_error 'invalid selected identifier'; return 1; }
    dt_load "$DT_THEME" "$DT_FLAVOR" || return
    DT_GENERATION=''
    return 0
  fi
  dt_generation || return
  if [[ $DT_GENERATION ]]; then
    file=$DT_STATE/generations/$DT_GENERATION/selection
  elif [[ -r $HOME/.theme ]]; then file=$HOME/.theme
  elif [[ -r $DT_ROOT/.theme ]]; then file=$DT_ROOT/.theme
  else file=$DT_ROOT/.default; fi
  IFS= read -r id < "$file" || [[ $id ]] || { dt_error 'no theme selection'; return 1; }
  dt_split "$id" "${DT_GENERATION:+persisted}" || { dt_error 'invalid selected identifier'; return 1; }
  if [[ ${1:-load} == selection && -n $DT_FLAVOR ]]; then
    dt_theme_id "$DT_THEME" && dt_id "$DT_FLAVOR" || { dt_error 'invalid selected identifier'; return 1; }
  else dt_load "$DT_THEME" "$DT_FLAVOR"; fi
}
dt_rgb() {
  local hex=${1#\#}
  DT_R=$((16#${hex:0:2})) DT_G=$((16#${hex:2:2})) DT_B=$((16#${hex:4:2}))
  if (( DT_R == DT_G && DT_G == DT_B )); then
    if (( DT_R < 8 )); then DT_A=16
    elif (( DT_R > 248 )); then DT_A=231
    else DT_A=$((232+(DT_R-8)*24/247)); fi
  else DT_A=$((16+36*((DT_R*5+127)/255)+6*((DT_G*5+127)/255)+(DT_B*5+127)/255)); fi
}
dt_metrics() {
  local name input='' lum brightness cmyk
  for name in "${DT_NAMES[@]}"; do
    dt_rgb "${DT_COLORS[$name]}"
    input+="$name $DT_R $DT_G $DT_B"$'\n'
  done
  local output
  output=$(LC_ALL=C awk '
    function lin(c) {c/=255; return c<=0.04045 ? c/12.92 : ((c+0.055)/1.055)^2.4}
    NF==4 {r=$2;g=$3;b=$4;
      c=1-r/255; m=1-g/255; y=1-b/255; k=c<m?(c<y?c:y):(m<y?m:y);
      if(k>=.999999) {c=0;m=0;y=0;k=1} else {c=(c-k)/(1-k);m=(m-k)/(1-k);y=(y-k)/(1-k)}
      printf "%s|%.6f|%d|%d %d %d %d\n",$1,.2126*lin(r)+.7152*lin(g)+.0722*lin(b),int(.299*r+.587*g+.114*b+.5),int(c*100+.5),int(m*100+.5),int(y*100+.5),int(k*100+.5)
    }' <<< "$input") || return
  DT_VALUES=()
  while IFS='|' read -r name lum brightness cmyk; do
    DT_VALUES[$name.luminance]=$lum DT_VALUES[$name.brightness]=$brightness DT_VALUES[$name.cmyk]=$cmyk
  done <<< "$output"
}
dt_value() {
  local name=$1 format=$2 hex=$3
  dt_rgb "$hex"
  case $format in
    name) REPLY=$name ;; hex) REPLY=$hex ;;
    rgb) REPLY="$DT_R $DT_G $DT_B" ;;
    r|rgb-r) REPLY=$DT_R ;; g|rgb-g) REPLY=$DT_G ;; b|rgb-b) REPLY=$DT_B ;;
    ansi-8bit|ansi-8bit-value) REPLY=$DT_A ;;
    ansi-8bit-escapecode) printf -v REPLY '\e[38;5;%sm' "$DT_A" ;;
    ansi-24bit) REPLY="38;2;$DT_R;$DT_G;$DT_B" ;;
    ansi-24bit-escapecode|esc) printf -v REPLY '\e[38;2;%s;%s;%sm' "$DT_R" "$DT_G" "$DT_B" ;;
    luminance|brightness|cmyk) [[ ${DT_VALUES[$name.$format]+yes} ]] || dt_metrics || return; REPLY=${DT_VALUES[$name.$format]} ;;
    *) dt_error "unsupported format: $format"; return 1 ;;
  esac
}
dt_fingerprint() {
  local sum input
  local -a inputs=("$DT_LIB/"*.bash)
  if [[ ${DT_ADAPTER:-native} != generic ]]; then
    inputs+=("$DT_ROOT/$DT_THEME/theme.toml" "$DT_ROOT/$DT_THEME/flavors/"*.toml)
  fi
  if [[ -n ${DT_THEME_DIR:-} ]]; then
    for input in "$DT_THEME_DIR/"*.toml "$DT_THEME_DIR/"*.conf "$DT_THEME_DIR/"*.theme "$DT_THEME_DIR/"*.properties "$DT_THEME_DIR/"*.tmTheme; do
      [[ ! -f $input ]] || inputs+=("$input")
    done
  fi
  for input in "$DT_TEMPLATES/"*.tpl "$DT_USER_TEMPLATES/"*.tpl; do [[ ! -f $input ]] || inputs+=("$input"); done
  if [[ $DT_THEME == pywal16 ]]; then
    [[ ${DT_META[source]:-} == pywal16 && -n ${DT_PYWAL_INPUT:-} ]] || dt_load "$DT_THEME" "$DT_FLAVOR" || return
    [[ -f $DT_PYWAL_FILE && $(<"$DT_PYWAL_FILE") == "$DT_PYWAL_INPUT" ]] || { dt_error 'pywal16 input changed; retry the command'; return 1; }
    inputs+=("$DT_PYWAL_FILE")
  fi
  # Batch hashing preserves filename/content identity without one process per file.
  sum=$(set -o pipefail; sha256sum -- "${inputs[@]}" | sha256sum) || return
  REPLY=${sum%% *}
}
dt_emit_array() {
  local array=$1 name=$2 format
  printf 'declare -gA %s=(\n' "$array"
  for format in name hex rgb r g b luminance brightness cmyk ansi-8bit ansi-8bit-value ansi-8bit-escapecode ansi-24bit ansi-24bit-escapecode esc; do
    dt_value "$name" "$format" "${DT_COLORS[$name]}" || return
    printf ' [%q]=%q\n' "$format" "$REPLY"
  done
  printf ')\n'
}
dt_emit_init() {
  local shell=$1 theme=$DT_THEME selected=$DT_FLAVOR name file flavor role
  case $shell in bash|zsh|fish) ;; *) dt_error 'expected bash, zsh, or fish'; return 1 ;; esac
  if [[ $shell == fish ]]; then
    printf 'set -gx THEME %s\nset -gx FLAVOR %s\n' "$theme" "$selected"
    for name in "${DT_NAMES[@]}"; do printf "set -g dots_color_%s '%s'\n" "$name" "${DT_COLORS[$name]}"; done
    for role in background foreground muted accent selection error warning info hint; do printf "set -g dots_role_%s '%s'\n" "$role" "${DT_SEMANTIC[$role]:-${DT_COLORS[${DT_META[roles.$role]}]}}"; done
    return
  fi
  printf 'export THEME=%q FLAVOR=%q\n' "$theme" "$selected"
  printf 'declare -gA dots_palette=(\n'
  for name in "${DT_NAMES[@]}"; do printf ' [%q]=%q\n' "$name" "${DT_COLORS[$name]}"; done
  printf ')\ndeclare -gA dots_roles=(\n'
  for role in background foreground muted accent selection error warning info hint; do printf ' [%q]=%q\n' "$role" "${DT_SEMANTIC[$role]:-${DT_COLORS[${DT_META[roles.$role]}]}}"; done
  printf ')\n'
  local ls='' code kind
  for kind in di ln ex or mi pi so bd cd su sg tw ow st '*.tar' '*.gz' '*.zip' '*.png' '*.jpg'; do
    case $kind in
      di) role=accent ;; ln|pi|so) role=info ;; or|mi|su|sg) role=error ;;
      ex|tw|ow|st) role=hint ;; *) role=warning ;;
    esac
    dt_rgb "${DT_SEMANTIC[$role]:-${DT_COLORS[${DT_META[roles.$role]}]}}"
    code="38;2;$DT_R;$DT_G;$DT_B"
    ls+="${ls:+:}$kind=$code"
  done
  printf 'export DOTS_THEME_LS_COLORS=%q\n' "$ls"
  if [[ $theme == catppuccin ]]; then
    printf 'declare -ga catppuccin_palette=('; printf ' %q' "${DT_NAMES[@]}"; printf ')\ndeclare -g catppuccin_flavor=%q\n' "$selected"
    for flavor in mocha macchiato frappe latte; do
      dt_load "$theme" "$flavor" && dt_metrics || return
      for name in "${DT_NAMES[@]}"; do
        if [[ $flavor == "$selected" ]]; then dt_emit_array "$name" "$name" || return; fi
        dt_emit_array "${flavor}_$name" "$name" || return
      done
    done
    dt_load "$theme" "$selected" || return
  fi
}
dt_cached_init() {
  local shell=$1 file cache=${XDG_CACHE_HOME:-$HOME/.cache}/dots/themes tmp
  dt_theme_id "$DT_THEME" && dt_id "$DT_FLAVOR" || { dt_error 'invalid theme or flavor'; return 1; }
  if [[ -z ${DT_THEME_DIR:-} && ( -d $DT_ROOT/$DT_THEME-$DT_FLAVOR || -d $DT_USER_THEMES/$DT_THEME-$DT_FLAVOR ) ]]; then
    dt_find_theme "$DT_THEME-$DT_FLAVOR" || return
  fi
  dt_fingerprint || return
  file=$cache/$DT_THEME-$DT_FLAVOR-$REPLY.$shell
  if [[ -f $file && ! -L $file ]]; then cat "$file"; return; fi
  # A matching content fingerprint already proves this data was validated.
  dt_load "$DT_THEME" "$DT_FLAVOR" || return
  mkdir -p -- "$cache" || return
  tmp=$(mktemp "$cache/.init.XXXXXXXX") || return
  if dt_emit_init "$shell" > "$tmp"; then
    chmod 600 "$tmp" && mv -f -- "$tmp" "$file" && cat "$file"
  else rm -f -- "$tmp"; return 1; fi
}
dt_json() {
  local name sep=''
  # All identifiers and colors are validated; no arbitrary strings enter JSON.
  printf '{"schema":1,"id":"%s","adapter":"%s","mode":"%s","theme":"%s","flavor":"%s","palette":{' "${DT_ID:-$DT_THEME-$DT_FLAVOR}" "${DT_ADAPTER:-native}" "${DT_MODE:-dark}" "$DT_THEME" "$DT_FLAVOR"
  for name in "${DT_NAMES[@]}"; do printf '%s"%s":"%s"' "$sep" "$name" "${DT_COLORS[$name]}"; sep=,; done
  printf '},"roles":{'
  sep=''
  for name in background foreground muted accent selection error warning info hint; do
    printf '%s"%s":"%s"' "$sep" "$name" "${DT_SEMANTIC[$name]:-${DT_COLORS[${DT_META[roles.$name]}]}}"; sep=,
  done
  printf '},"colors":{'
  sep=''
  # Additive normalized data for consumers that do not load native theme plugins.
  while IFS= read -r name; do
    [[ $name != mode ]] || continue
    printf '%s"%s":"%s"' "$sep" "$name" "${DT_SEMANTIC[$name]}"; sep=,
  done < <(printf '%s\n' "${!DT_SEMANTIC[@]}" | LC_ALL=C sort)
  printf '}}\n'
}

# shellcheck source=render.bash
source "$DT_LIB/render.bash"
