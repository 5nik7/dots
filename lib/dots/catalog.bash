# Static metadata only. Nothing read here is shell code.
# shellcheck source-path=SCRIPTDIR
source "$DOTS_LIB_DIR/ui.bash"

# Built-in presentation and completion share the same static metadata.
DOTS_BUILTIN_NAMES=(help commands completion)
declare -A DOTS_BUILTIN_SUMMARY=(
  [help]='Show global or command help'
  [commands]='List or validate registered commands'
  [completion]='Print Bash, Zsh, or Fish integration'
)
DOTS_GLOBAL_OPTIONS=(
  '--help|-h|flag|Show help'
  '--dir|-d|flag|Print the repository directory'
  '--raw|-r|flag|Do not abbreviate home paths with --dir'
  '--command-dir||directory|Add an absolute extension directory'
  '--color||choice:auto,always,never|Color mode (DOTS_COLOR)'
  '--icons||choice:auto,always,never|Icon mode (DOTS_ICONS)'
)
dots_builtin_metadata() {
  DOTS_META_SUMMARY=${DOTS_BUILTIN_SUMMARY[$1]}
  DOTS_META_USAGE='' DOTS_META_HIDDEN=false
  DOTS_META_OPTIONS=() DOTS_META_ARGUMENTS=() DOTS_META_EXAMPLES=()
  case $1 in
    help) DOTS_META_USAGE='[ROUTE...]' ;;
    commands)
      DOTS_META_USAGE='[--check]'
      DOTS_META_OPTIONS=('--check||flag|Validate command definitions without executing them') ;;
    completion)
      DOTS_META_USAGE='bash|zsh|fish'
      DOTS_META_ARGUMENTS=('1|choice:bash,zsh,fish|Shell adapter to print') ;;
  esac
}

dots_type_valid() {
  local value
  case $1 in
    flag|string|file|directory) return 0 ;;
    theme|flavor|palette-color|color-format) return 0 ;;
    choice:*)
      [[ ${1#choice:} && $1 != *, && $1 != *,,* ]] || return 1
      local -a values=()
      IFS=, read -r -a values <<< "${1#choice:}"
      for value in "${values[@]}"; do [[ -n $value && $value != *'|'* ]] || return 1; done
      return 0 ;;
    *) return 1 ;;
  esac
}

dots_metadata() {
  local file=$1 line key value separators n=0 bytes=0 long short type description extra position next=1 rest=0
  local LC_ALL=C
  local -A seen=() option_names=()
  DOTS_META_SUMMARY='' DOTS_META_USAGE='' DOTS_META_HIDDEN=false
  DOTS_META_EXAMPLES=() DOTS_META_OPTIONS=() DOTS_META_ARGUMENTS=()
  [[ -f $file && -r $file ]] || { dots_error "Cannot read command metadata: $file"; return 1; }
  while IFS='' read -r -n 16385 line || [[ -n $line ]]; do
    (( ++n, bytes+=${#line}+1 ))
    # An executable with no more header fits even when its first code line is long.
    [[ $line == '#'* || $line =~ ^[[:space:]]*$ ]] || break
    if (( n > 128 || bytes > 16384 )); then dots_error "Metadata header exceeds limit: $file"; return 1; fi
    [[ $line == '# dots:'* ]] || continue
    line=${line%$'\r'}
    if [[ $line == *[$'\001'-$'\037'$'\177']* || $line != *=* ]]; then
      dots_error "Invalid metadata header: $file"; return 1
    fi
    key=${line#'# dots:'}; key=${key%%=*}; value=${line#*=}
    case $key in
      summary|usage|hidden)
        if [[ ${seen[$key]:-} || -z $value ]]; then dots_error "Repeated or empty $key metadata: $file"; return 1; fi
        seen[$key]=1
        case $key in
          summary) DOTS_META_SUMMARY=$value ;;
          usage) DOTS_META_USAGE=$value ;;
          hidden)
            [[ $value == true || $value == false ]] || { dots_error "Invalid hidden metadata: $file"; return 1; }
            DOTS_META_HIDDEN=$value ;;
        esac ;;
      example)
        [[ $value ]] || { dots_error "Empty example: $file"; return 1; }
        DOTS_META_EXAMPLES+=("$value") ;;
      option)
        # long|short|flag/string/file/directory/choice:a,b|description
        separators=${value//[^|]/}
        [[ ${#separators} == 3 ]] || { dots_error "Invalid option field count: $file"; return 1; }
        IFS='|' read -r long short type description extra <<< "$value"
        if [[ ! $long =~ ^--[a-z][a-z0-9-]*$ || ( -n $short && ! $short =~ ^-[a-zA-Z0-9]$ ) || -z $description || -n $extra || $description == *'|'* ]] || ! dots_type_valid "$type"; then
          dots_error "Invalid option metadata: $file"; return 1
        fi
        if [[ ${option_names[$long]:-} || ( -n $short && ${option_names[$short]:-} ) ]]; then dots_error "Duplicate option metadata: $file"; return 1; fi
        option_names[$long]=1; [[ -z $short ]] || option_names[$short]=1
        DOTS_META_OPTIONS+=("$value") ;;
      argument)
        # sequential position (1-based), or final *|type|description
        separators=${value//[^|]/}
        [[ ${#separators} == 2 ]] || { dots_error "Invalid argument field count: $file"; return 1; }
        IFS='|' read -r position type description extra <<< "$value"
        if (( rest )) || [[ $position != "$next" && $position != '*' ]] || [[ $type == flag || -z $description || -n $extra ]] || ! dots_type_valid "$type"; then
          dots_error "Invalid positional metadata: $file"; return 1
        fi
        [[ $position != '*' ]] || rest=1
        (( ++next )); DOTS_META_ARGUMENTS+=("$value") ;;
      *) dots_error "Unknown metadata field '$key': $file"; return 1 ;;
    esac
  done < "$file"
}

dots_catalog_load() {
  local prefix=${1:-} directory file stem first
  DOTS_CATALOG=()
  declare -gA DOTS_CATALOG_FILE=() DOTS_CATALOG_SUMMARY=() DOTS_CATALOG_HIDDEN=()
  for directory in "${DOTS_ROOTS[@]}"; do
    for file in "$directory"/dots-"$prefix"*; do
      [[ -e $file || -L $file ]] || continue
      stem=${file##*/}; stem=${stem#dots-}; first=${stem%%-*}
      if [[ ! $stem =~ ^[a-z][a-z0-9]*(-[a-z][a-z0-9]*)*$ ]] || dots_reserved "$first"; then
        dots_error "Invalid or reserved command filename: $file"; return 1
      fi
      if [[ ! -f $file || ! -x $file ]]; then dots_error "Command is not executable: $file"; return 1; fi
      if [[ ${DOTS_CATALOG_FILE[$stem]:-} ]]; then dots_error "Duplicate command route: ${stem//-/ }"; return 1; fi
      dots_metadata "$file" || return
      DOTS_CATALOG+=("$stem")
      DOTS_CATALOG_FILE[$stem]=$file
      DOTS_CATALOG_SUMMARY[$stem]=${DOTS_META_SUMMARY:-Run ${stem//-/ }}
      DOTS_CATALOG_HIDDEN[$stem]=$DOTS_META_HIDDEN
    done
  done
}

dots_catalog_print() {
  local stem prefix=${1:-}
  dots::heading 'Commands'
  if [[ -z $prefix ]]; then
    for stem in "${DOTS_BUILTIN_NAMES[@]}"; do
      dots_builtin_metadata "$stem"
      dots::row "$stem${DOTS_META_USAGE:+ $DOTS_META_USAGE}" "$DOTS_META_SUMMARY"
    done
  fi
  for stem in "${DOTS_CATALOG[@]}"; do
    [[ ${DOTS_CATALOG_HIDDEN[$stem]} == true ]] && continue
    dots::row "${stem//-/ }" "${DOTS_CATALOG_SUMMARY[$stem]}"
  done
}

dots_command_help() {
  local route=$1 row long short type description position
  dots::heading "dots $route"
  printf '%s\n\n' "${DOTS_META_SUMMARY:-Run $route}"
  dots::heading 'Usage'
  printf '  dots %s%s\n' "$route" "${DOTS_META_USAGE:+ $DOTS_META_USAGE}"
  if ((${#DOTS_META_OPTIONS[@]})); then
    printf '\n'; dots::heading 'Options'
    for row in "${DOTS_META_OPTIONS[@]}"; do
      IFS='|' read -r long short type description <<< "$row"
      dots::row "${short:+$short, }$long$([[ $type == flag ]] || printf ' VALUE')" "$description"
    done
  fi
  if ((${#DOTS_META_ARGUMENTS[@]})); then
    printf '\n'; dots::heading 'Arguments'
    for row in "${DOTS_META_ARGUMENTS[@]}"; do
      IFS='|' read -r position type description <<< "$row"
      dots::row "$position ($type)" "$description"
    done
  fi
  if ((${#DOTS_META_EXAMPLES[@]})); then
    printf '\n'; dots::heading 'Examples'
    for row in "${DOTS_META_EXAMPLES[@]}"; do printf '  %s\n' "$row"; done
  fi
}

dots_help() {
  local route='' word resolved line long short type description
  for word; do
    [[ $word == -h || $word == --help ]] && continue
    [[ $word =~ ^[a-z][a-z0-9]*$ ]] || { dots_error 'Unknown command or invalid help route'; return 1; }
    route+=${route:+ }$word
  done
  if [[ -z $route ]]; then
    dots_catalog_load || return
    if [[ -f $DOTS/logo.txt && -r $DOTS/logo.txt ]]; then
      while IFS='' read -r line || [[ -n $line ]]; do printf '%s\n' "$line"; done < "$DOTS/logo.txt"
      printf '\n'
    fi
    dots::heading 'dots — your command center'
    printf '\n'; dots::heading 'Usage'
    printf '  dots [OPTIONS] COMMAND [ARGS...]\n\n'
    dots_catalog_print
    printf '\n'; dots::heading 'Global options (before the command)'
    for line in "${DOTS_GLOBAL_OPTIONS[@]}"; do
      IFS='|' read -r long short type description <<< "$line"
      case $type in directory) long+=' DIRECTORY' ;; choice:*) long+='=auto|always|never' ;; esac
      dots::row "${short:+$short, }$long" "$description"
    done
    return 0
  fi
  case $route in
    commands|completion|help) dots_builtin_metadata "$route"; dots_command_help "$route"; return ;;
  esac
  # Preserve argv boundaries; the normalized route is only used for display.
  local -a words=()
  read -r -a words <<< "$route"
  dots_resolve "${words[@]}"; resolved=$?
  if (( resolved == 1 )); then return 1; fi
  if (( resolved == 0 && DOTS_CONSUMED == ${#words[@]} )); then
    dots_metadata "$DOTS_EXECUTABLE" && dots_command_help "$route"
    return
  fi
  dots_catalog_load "${route// /-}-" || return
  if ((${#DOTS_CATALOG[@]})); then dots_catalog_print "$route"
  else dots_error "Unknown command: $route"; return 1; fi
}
