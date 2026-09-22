# shellcheck source-path=SCRIPTDIR
# Literal tilde is the documented --dir abbreviation.
# shellcheck disable=SC2088

dots_error() {
  # shellcheck source=ui.bash
  source "$DOTS_LIB_DIR/ui.bash"
  dots::error "$*"
}

dots_reserved() {
  case $1 in
    help|doctor|commands|completion|version|status|spec|plan|apply|undo|history|backup|config|bootstrap|self|__complete) return 0 ;;
    *) return 1 ;;
  esac
}

dots_roots() {
  DOTS_ROOTS=()
  local directory previous duplicate
  for directory in "$DOTS/bin" "$DOTS/local/bin" "${DOTS_EXTRA_ROOTS[@]}"; do
    [[ -d $directory ]] || continue
    duplicate=0
    for previous in "${DOTS_ROOTS[@]}"; do
      [[ $directory -ef $previous ]] && duplicate=1 && break
    done
    (( duplicate )) || DOTS_ROOTS+=("$directory")
  done
}

# Return 0 for a resolved executable, 3 for no match, 1 for a blocking error.
# Never enumerate directories or read metadata on the execution path.
dots_resolve() {
  local word candidate='' depth directory found matches
  local -a candidates=()
  DOTS_EXECUTABLE='' DOTS_CONSUMED=0 DOTS_ROUTE=''
  for word; do
    [[ $word =~ ^[a-z][a-z0-9]*$ ]] || break
    candidate+=${candidate:+-}$word
    candidates+=("$candidate")
  done
  for ((depth=${#candidates[@]}; depth>0; depth--)); do
    candidate=${candidates[depth-1]} found='' matches=0
    for directory in "${DOTS_ROOTS[@]}"; do
      if [[ -e $directory/dots-$candidate || -L $directory/dots-$candidate ]]; then
        (( ++matches ))
        found=$directory/dots-$candidate
        if [[ ! -f $found || ! -x $found ]]; then
          dots_error "Command is not an executable regular file: $found"
          return 1
        fi
      fi
    done
    if (( matches > 1 )); then dots_error "Duplicate command route: ${candidate//-/ }"; return 1; fi
    if (( matches == 1 )); then
      DOTS_EXECUTABLE=$found DOTS_CONSUMED=$depth DOTS_ROUTE=${candidate//-/ }
      return 0
    fi
  done
  return 3
}

dots_main() {
  local raw=0 mode option word want_help=0 resolved
  local -a DOTS_EXTRA_ROOTS=() DOTS_ROOTS=()
  while (($#)); do
    case $1 in
      -r|--raw) raw=1; shift ;;
      -d|--dir)
        if (( ! raw )) && [[ -n ${HOME:-} && $DOTS == "$HOME" ]]; then printf '~\n'
        elif (( ! raw )) && [[ -n ${HOME:-} && $DOTS == "$HOME/"* ]]; then printf '%s%s\n' '~/' "${DOTS#"$HOME/"}"
        else printf '%s\n' "$DOTS"; fi
        return 0 ;;
      --color=*|--icons=*)
        option=${1%%=*} mode=${1#*=}
        case $mode in auto|always|never) ;; *) dots_error "Expected $option=auto|always|never"; return 2 ;; esac
        if [[ $option == --color ]]; then export DOTS_COLOR=$mode; else export DOTS_ICONS=$mode; fi
        shift ;;
      --command-dir)
        if (($# < 2)) || [[ $2 != /* || ! -d $2 ]]; then dots_error '--command-dir requires an existing absolute directory'; return 2; fi
        DOTS_EXTRA_ROOTS+=("$2"); shift 2 ;;
      *) break ;;
    esac
  done
  for mode in "${DOTS_COLOR:-auto}" "${DOTS_ICONS:-auto}"; do
    case $mode in auto|always|never) ;; *) dots_error 'Invalid DOTS_COLOR or DOTS_ICONS setting'; return 2 ;; esac
  done
  case ${1:-help} in
    __complete)
      shift
      # Completion errors never enter a shell's candidate stream.
      # shellcheck source=complete.bash
      source "$DOTS_LIB_DIR/complete.bash"
      dots_complete "$@" 2>/dev/null
      return ;;
    completion)
      if (($# == 2)) && [[ $2 == -h || $2 == --help ]]; then
        source "$DOTS_LIB_DIR/catalog.bash"
        dots_help completion
        return
      fi
      if (($# != 2)); then dots_error 'Usage: dots completion bash|zsh|fish'; return 2; fi
      case $2 in bash|zsh|fish) ;; *) dots_error 'Unknown completion shell'; return 2 ;; esac
      local line
      while IFS='' read -r line || [[ -n $line ]]; do printf '%s\n' "$line"; done < "$DOTS_LIB_DIR/completion/$2"
      return ;;
  esac
  dots_roots
  case ${1:-help} in
    help|-h|--help)
      (($#)) && shift
      # shellcheck source=catalog.bash
      source "$DOTS_LIB_DIR/catalog.bash"
      dots_help "$@"; return ;;
    commands)
      shift
      source "$DOTS_LIB_DIR/catalog.bash"
      if (($# == 0)); then dots_catalog_load && dots_catalog_print
      elif (($# == 1)) && [[ $1 == --check ]]; then
        dots_catalog_load || return
        source "$DOTS_LIB_DIR/ui.bash"
        dots::success "Validated ${#DOTS_CATALOG[@]} external commands"
      elif (($# == 1)) && [[ $1 == -h || $1 == --help ]]; then dots_help commands
      else dots_error 'Usage: dots commands [--check]'; return 2; fi
      return ;;
  esac
  if dots_reserved "$1"; then dots_error 'This core command is not implemented'; return 1; fi
  for word; do
    [[ $word == -- ]] && break
    [[ $word == -h || $word == --help ]] && want_help=1
  done
  dots_resolve "$@"; resolved=$?
  if (( resolved == 1 )); then return 1; fi
  if (( resolved == 0 )); then
    if (( want_help )); then
      source "$DOTS_LIB_DIR/catalog.bash"
      dots_metadata "$DOTS_EXECUTABLE" || return
      dots_command_help "$DOTS_ROUTE"
    else
      shift "$DOTS_CONSUMED"
      exec "$DOTS_EXECUTABLE" "$@"
    fi
    return
  fi
  # Group discovery is a slow path, reached only when no executable matches.
  source "$DOTS_LIB_DIR/catalog.bash"
  dots_help "$@"
}
