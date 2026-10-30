# Shared Bash/Zsh data reader. Never evaluate config values as shell code.
# shellcheck disable=SC2296,SC2299,SC2034
_dots_config_valid() {
  case $1 in
    bool) [[ $2 == 0 || $2 == 1 ]] ;;
    style) [[ $2 == auto || $2 == always || $2 == never ]] ;;
    suggestions) [[ $2 == deja || $2 == autosuggestions || $2 == none ]] ;;
    id) [[ $2 =~ ^[a-z][a-z0-9_]*(-[a-z0-9_]+)*$ ]] ;;
    *) return 1 ;;
  esac
}
_dots_config_load() {
  local key kind value description line number=0 source_value
  local root=${DOTS:-${DT_LIB%/lib/dots/themes}}
  local config=${DOTS_CONFIG_FILE:-${XDG_CONFIG_HOME:-$HOME/.config}/dots/config.env}
  local -A values=() origins=() kinds=() seen=()
  while IFS=$'\t' read -r key kind value description; do
    values[$key]=$value kinds[$key]=$kind origins[$key]=default
  done < "$root/lib/dots/shell/settings.tsv"
  if [[ -e $config ]]; then
    [[ -f $config && -r $config ]] || { printf 'dots: unreadable settings file\n' >&2; return 1; }
    while IFS= read -r line || [[ -n $line ]]; do
      ((number+=1)); line=${line%$'\r'}
      line=${line#"${line%%[![:space:]]*}"}; line=${line%"${line##*[![:space:]]}"}
      [[ -n $line && $line != \#* ]] || continue
      [[ $line == *=* ]] || { printf 'dots: invalid setting on line %s\n' "$number" >&2; return 1; }
      key=${line%%=*}; key=${key%"${key##*[![:space:]]}"}
      value=${line#*=}; value=${value#"${value%%[![:space:]]*}"}
      [[ $key =~ ^DOTS_[A-Z_]+$ && -n ${kinds[$key]:-} && -z ${seen[$key]:-} ]] || {
        printf 'dots: unknown or duplicate setting on line %s\n' "$number" >&2; return 1;
      }
      if [[ $value == \"*\" || $value == \'*\' ]]; then value=${value:1:${#value}-2}; fi
      _dots_config_valid "${kinds[$key]}" "$value" || { printf 'dots: invalid %s on line %s\n' "$key" "$number" >&2; return 1; }
      values[$key]=$value origins[$key]=config seen[$key]=1
    done < "$config"
  fi
  # Compiled startup provides these literals without Python on the warm path.
  if [[ ${_DOTS_PROFILE_SETTINGS_CHECKOUT:-} != "$root" ]]; then
    typeset -ga _DOTS_PROFILE_SETTING_ROWS=()
    local rows=''
    if command -v python3 >/dev/null 2>&1; then
      rows=$(DOTS="$root" command python3 -B "$root/lib/dots/profile_config.py" __settings) || return
    fi
    while IFS= read -r line; do [[ -z $line ]] || _DOTS_PROFILE_SETTING_ROWS+=("$line"); done <<< "$rows"
    typeset -g _DOTS_PROFILE_SETTINGS_CHECKOUT=$root
  fi
  typeset -gA _DOTS_STYLE_ICONS _DOTS_STYLE_COLORS
  _DOTS_STYLE_ICONS=() _DOTS_STYLE_COLORS=()
  for line in "${_DOTS_PROFILE_SETTING_ROWS[@]}"; do
    key=${line%%$'\t'*}
    value=${line#*$'\t'}; value=${value%%$'\t'*}
    case $key in
      __icon.*) _DOTS_STYLE_ICONS[${key#__icon.}]=$value; continue ;;
      __color.*) _DOTS_STYLE_COLORS[${key#__color.}]=$value; continue ;;
    esac
    IFS=$'\t' read -r key value source_value <<< "$line"
    if [[ $key == __path ]]; then typeset -g _DOTS_PROFILE_CONFIG=$value; continue; fi
    [[ -z ${DOTS_CONFIG_FILE:-} ]] || continue
    [[ -n ${kinds[$key]:-} ]] && _dots_config_valid "${kinds[$key]}" "$value" || return 1
    values[$key]=$value origins[$key]=$source_value
  done
  while IFS=$'\t' read -r key kind value description; do
    if [[ -n ${ZSH_VERSION:-} ]]; then source_value=${(P)key}
    else source_value=${!key-}; fi
    if [[ -n $source_value ]]; then
      _dots_config_valid "$kind" "$source_value" || { printf 'dots: invalid override %s\n' "$key" >&2; return 1; }
      values[$key]=$source_value origins[$key]=environment
    fi
  done < "$root/lib/dots/shell/settings.tsv"
  # Commit only after the complete input has passed validation.
  typeset -gA dots_options dots_option_sources
  dots_options=() dots_option_sources=()
  while IFS=$'\t' read -r key kind value description; do
    dots_options[$key]=${values[$key]} dots_option_sources[$key]=${origins[$key]}
  done < "$root/lib/dots/shell/settings.tsv"
  typeset -g _DOTS_CONFIG_PATH=$config
  if [[ -z ${DOTS_CONFIG_FILE:-} && -f ${_DOTS_PROFILE_CONFIG:-}/profile.json ]]; then _DOTS_CONFIG_PATH=$_DOTS_PROFILE_CONFIG/profile.json; fi
}
