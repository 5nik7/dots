# Completion returns data, never shell code or extension output.
# shellcheck source-path=SCRIPTDIR
source "$DOTS_LIB_DIR/catalog.bash"

dots_candidate() {
  local value=$1 description=${2:-}
  [[ $value == "$DOTS_CURRENT"* ]] || return 0
  DOTS_SUGGESTIONS+=("candidate"$'\t'"$value"$'\t'"$description")
}
dots_value_candidates() {
  local type=$1 lead=${2:-} value
  local -a values=()
  case $type in
    theme-id)
      local path name root=${DOTHEMES:-${THEMES:-$DOTS/themes}} user=${XDG_CONFIG_HOME:-$HOME/.config}/dots/themes
      for path in "$root/"*/colors.toml "$user/"*/colors.toml; do
        [[ -f $path && ! -L $path ]] || continue
        name=${path%/colors.toml}; dots_candidate "$lead${name##*/}"
      done
      [[ ! -d $root/pywal16-current ]] || dots_candidate "${lead}pywal16-current"
      ;;
    file-resource|file-repository)
      local action=list
      [[ $type != file-repository ]] || action=sources
      local output
      output=$(python3 -B "$DOTS_LIB_DIR/files/catalog.py" "$action" --all-platforms 2>/dev/null) || return 0
      while IFS=$'\t' read -r value _; do dots_candidate "$lead$value"; done <<< "$output"
      ;;
    theme|flavor|palette-color|color-format)
      local DT_LIB=$DOTS_LIB_DIR/themes name file theme_name='' flavor_name=''
      source "$DT_LIB/core.bash"
      # Positional data is collected by the completion parser, never evaluated.
      theme_name=${DOTS_POSITIONALS[0]:-} flavor_name=${DOTS_POSITIONALS[1]:-}
      case $type in
        theme)
          for file in "$DT_ROOT/"*/theme.toml; do
            [[ -f $file && -d ${file%/theme.toml}/flavors ]] || continue
            name=${file%/theme.toml}; dots_candidate "$lead${name##*/}"
          done ;;
        flavor)
          dt_theme_id "$theme_name" || return 0
          for file in "$DT_ROOT/$theme_name/flavors/"*.toml; do
            [[ -f $file ]] || continue
            name=${file##*/}; dots_candidate "$lead${name%.toml}"
          done ;;
        palette-color)
          dt_load "$theme_name" "$flavor_name" 2>/dev/null || return 0
          for name in "${DT_NAMES[@]}"; do dots_candidate "$lead$name"; done ;;
        color-format) for name in "${DT_FORMATS[@]}"; do dots_candidate "$lead$name"; done ;;
      esac ;;
    choice:*)
      IFS=, read -r -a values <<< "${type#choice:}"
      for value in "${values[@]}"; do dots_candidate "$lead$value"; done ;;
    file|directory) DOTS_SUGGESTIONS+=("$type"$'\t'"$lead"$'\t') ;;
  esac
}
dots_find_option() {
  local wanted=$1 row long short description
  DOTS_OPTION_TYPE=''
  for row in "${DOTS_META_OPTIONS[@]}"; do
    IFS='|' read -r long short DOTS_OPTION_TYPE description <<< "$row"
    [[ $wanted == "$long" || ( -n $short && $wanted == "$short" ) ]] && return 0
  done
  DOTS_OPTION_TYPE=''
  return 1
}
dots_completion_children() {
  local prefix=$1 stem suffix next description
  local -A seen=()
  # Complete only route-like current words, and inspect only matching filenames.
  # A flag or path prefix should not cause an unrelated full catalog scan.
  [[ $DOTS_CURRENT =~ ^[a-z0-9]*$ ]] || return 0
  dots_catalog_load "${prefix:+$prefix-}$DOTS_CURRENT" || return
  for stem in "${DOTS_CATALOG[@]}"; do
    [[ ${DOTS_CATALOG_HIDDEN[$stem]} == true ]] && continue
    suffix=${stem#"${prefix:+$prefix-}"}; next=${suffix%%-*}
    [[ ${seen[$next]:-} ]] && continue
    seen[$next]=1
    description=${DOTS_CATALOG_SUMMARY[$stem]}
    [[ $suffix == "$next" ]] || description="Browse $next commands"
    dots_candidate "$next" "$description"
  done
}

dots_complete() {
  local shell=${1:-} cursor=${2:-}
  [[ $shell == bash || $shell == zsh || $shell == fish ]] || return 2
  [[ $cursor =~ ^[0-9]+$ && ${3:-} == -- ]] || return 2
  shift 3
  # shellcheck disable=SC2034
  local -a DOTS_POSITIONALS=() words=("$@") DOTS_SUGGESTIONS=() DOTS_EXTRA_ROOTS=() DOTS_ROOTS=()
  (( cursor >= 1 && cursor < ${#words[@]} )) || return 2
  local DOTS_CURRENT=${words[cursor]} index=1 token prefix='' help=0 resolved start
  local expected='' positional=1 options=1 long short type description row position lead=''
  # Only words before the cursor affect context; words after it are ignored.
  while (( index < cursor )); do
    token=${words[index]}
    case $token in
      --command-dir)
        (( ++index ))
        if (( index == cursor )); then
          dots_value_candidates directory; printf '%s\n' "${DOTS_SUGGESTIONS[@]}"; return
        fi
        [[ ${words[index]} == /* && -d ${words[index]} ]] || return 1
        DOTS_EXTRA_ROOTS+=("${words[index]}") ;;
      --color=*|--icons=*|-r|--raw) ;;
      *) break ;;
    esac
    (( ++index ))
  done
  dots_roots
  if (( index == cursor )); then
    if [[ $DOTS_CURRENT == --color=* || $DOTS_CURRENT == --icons=* ]]; then
      dots_value_candidates choice:auto,always,never "${DOTS_CURRENT%%=*}="
    else
      for row in "${DOTS_GLOBAL_OPTIONS[@]}"; do
        IFS='|' read -r long short type description <<< "$row"
        [[ $type != choice:* ]] || long+='='
        dots_candidate "$long" "$description"
        [[ -z $short ]] || dots_candidate "$short" "$description"
      done
      for token in "${DOTS_BUILTIN_NAMES[@]}"; do dots_candidate "$token" "${DOTS_BUILTIN_SUMMARY[$token]}"; done
      dots_completion_children '' || return
    fi
  else
    if [[ ${words[index]} == help ]]; then help=1; (( ++index )); fi
    if (( index == cursor )); then
      for token in "${DOTS_BUILTIN_NAMES[@]}"; do dots_candidate "$token" "${DOTS_BUILTIN_SUMMARY[$token]}"; done
      dots_completion_children '' || return
    elif [[ ${words[index]} == completion ]]; then
      if (( cursor == index+1 )); then for token in bash zsh fish; do dots_candidate "$token"; done; fi
    elif [[ ${words[index]} == commands ]]; then
      if (( ! help )); then
        dots_builtin_metadata commands
        for row in "${DOTS_META_OPTIONS[@]}"; do
          IFS='|' read -r long short type description <<< "$row"
          dots_candidate "$long" "$description"
        done
      fi
    else
      start=$index
      local -a args=("${words[@]:start:cursor-start}")
      dots_resolve "${args[@]}"; resolved=$?
      (( resolved != 1 )) || return 1
      if (( resolved == 3 )); then
        for token in "${args[@]}"; do [[ $token =~ ^[a-z][a-z0-9]*$ ]] || return 0; prefix+=${prefix:+-}$token; done
        dots_completion_children "$prefix" || return
      else
        # DOTS_ROUTE is assigned by dots_resolve in dispatch.bash.
        # shellcheck disable=SC2153
        local executable=$DOTS_EXECUTABLE consumed=$DOTS_CONSUMED route=$DOTS_ROUTE
        if (( cursor == start+consumed )); then
          dots_completion_children "${route// /-}" || return
        fi
        if (( ! help )); then
          dots_metadata "$executable" || return
          for ((index=start+consumed; index<cursor; index++)); do
            token=${words[index]}
            if [[ $expected ]]; then expected=; continue; fi
            if (( options )) && [[ $token == -- ]]; then options=0; continue; fi
            if (( options )) && [[ $token == -* ]]; then
              if dots_find_option "${token%%=*}"; then
                [[ $DOTS_OPTION_TYPE == flag || $token == *=* ]] || expected=$DOTS_OPTION_TYPE
              else
                # Unknown option grammar cannot safely predict the next argument.
                return 0
              fi
            else DOTS_POSITIONALS+=("$token"); (( ++positional )); fi
          done
          if [[ $expected ]]; then dots_value_candidates "$expected"
          elif (( options )) && [[ $DOTS_CURRENT == --*=* ]]; then
            if dots_find_option "${DOTS_CURRENT%%=*}"; then dots_value_candidates "$DOTS_OPTION_TYPE" "${DOTS_CURRENT%%=*}="; fi
          elif (( options )) && [[ $DOTS_CURRENT == -* ]]; then
            dots_candidate --help 'Show command help'
            for row in "${DOTS_META_OPTIONS[@]}"; do
              IFS='|' read -r long short type description <<< "$row"
              dots_candidate "$long" "$description"
              [[ -z $short ]] || dots_candidate "$short" "$description"
            done
          else
            for row in "${DOTS_META_ARGUMENTS[@]}"; do
              IFS='|' read -r position type description <<< "$row"
              if [[ $position == "$positional" || $position == '*' ]]; then dots_value_candidates "$type"; break; fi
            done
          fi
        fi
      fi
    fi
  fi
  ((${#DOTS_SUGGESTIONS[@]})) && printf '%s\n' "${DOTS_SUGGESTIONS[@]}"
  return 0
}
