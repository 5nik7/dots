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
    wiki-page|wiki-section)
      local output
      output=$(python3 -B "$DOTS_LIB_DIR/wiki.py" __names "$type" 2>/dev/null) || return 0
      while IFS= read -r value; do [[ ! $value ]] || dots_candidate "$lead$value"; done <<< "$output"
      ;;
    profile-id)
      local output
      output=$(python3 -B "$DOTS_LIB_DIR/profiles.py" __names 2>/dev/null) || return 0
      while IFS= read -r value; do [[ ! $value ]] || dots_candidate "$lead$value"; done <<< "$output"
      ;;
    dots-setting)
      local output
      output=$(python3 -B "$DOTS_LIB_DIR/environment.py" __names 2>/dev/null) || return 0
      while IFS= read -r value; do [[ ! $value ]] || dots_candidate "$value"; done <<< "$output"
      ;;
    theme-file|theme-app)
      local output operation=__files
      [[ $type != theme-app ]] || operation=__apps
      output=$(python3 -B "$DOTS_LIB_DIR/themes/inspection.py" "$operation" 2>/dev/null) || return 0
      while IFS= read -r value; do [[ ! $value ]] || dots_candidate "$lead$value"; done <<< "$output"
      ;;
    theme-plugin)
      local output
      output=$(python3 -B "$DOTS_LIB_DIR/themes/plugins.py" __names 2>/dev/null) || return 0
      while IFS= read -r value; do [[ ! $value ]] || dots_candidate "$lead$value"; done <<< "$output"
      ;;
    anodize-theme|anodize-user-theme)
      local path name root=${DOTHEMES:-${THEMES:-$DOTS/themes}}
      local -a authored_roots=("${XDG_CONFIG_HOME:-$HOME/.config}/dots/themes")
      [[ $type != anodize-theme || $root == "${authored_roots[0]}" ]] || authored_roots+=("$root")
      for root in "${authored_roots[@]}"; do
        for path in "$root/"*/anodize.json; do
          [[ -f $path && ! -L $path ]] || continue
          name=${path%/anodize.json}; dots_candidate "$lead${name##*/}"
        done
      done
      ;;
    theme-id)
      local DT_ROOT=${DOTHEMES:-${THEMES:-$DOTS/themes}} DT_USER_THEMES=${XDG_CONFIG_HOME:-$HOME/.config}/dots/themes name
      # Literal hints need only discovery, not palette loading or validation.
      # shellcheck source=themes/discovery.bash
      source "$DOTS_LIB_DIR/themes/discovery.bash"
      dt_discover_ids theme-id completion || return
      for name in "${DT_DISCOVERY_IDS[@]}"; do dots_candidate "$lead$name"; done
      ;;
    git-submodule)
      local output base=${DOTS_OPTION_VALUES[--directory]:-${DOTS_OPTION_VALUES[-C]:-$DOTS}}
      output=$(python3 -B "$DOTS_LIB_DIR/git/inspection.py" _complete -C "$base" 2>/dev/null) || return 0
      while IFS= read -r value; do [[ ! $value ]] || dots_candidate "$lead$value"; done <<< "$output"
      ;;
    file-resource|file-repository)
      local action=list
      [[ $type != file-repository ]] || action=sources
      local output
      output=$(DOTS_COLOR=never DOTS_ICONS=never python3 -B "$DOTS_LIB_DIR/files/catalog.py" "$action" --all-platforms 2>/dev/null) || return 0
      while IFS=$'\t' read -r value _; do dots_candidate "$lead$value"; done <<< "$output"
      ;;
    file-color-key)
      local output
      output=$(python3 -B "$DOTS_LIB_DIR/themes/file-colors.py" _complete "${DOTS_POSITIONALS[@]}" 2>/dev/null) || return 0
      while IFS= read -r value; do [[ ! $value ]] || dots_candidate "$lead$value"; done <<< "$output"
      ;;
    theme-color)
      local DT_LIB=$DOTS_LIB_DIR/themes name id=${DOTS_OPTION_VALUES[--theme]:-}
      source "$DT_LIB/core.bash"
      if [[ ! $id ]]; then
        dt_current_id 2>/dev/null || return 0
        id=$REPLY
      fi
      dt_find_theme "$id" 2>/dev/null && dt_load "$id" 2>/dev/null || return 0
      local -A names=()
      for name in "${DT_NAMES[@]}"; do names[$name]=1; done
      if [[ ! ${DOTS_OPTION_VALUES[--native]:-} ]]; then
        for name in "${!DT_SEMANTIC[@]}"; do names[$name]=1; done
      fi
      while IFS= read -r name; do [[ ! $name ]] || dots_candidate "$lead$name"; done < <(printf '%s\n' "${!names[@]}" | LC_ALL=C sort)
      ;;
    theme|flavor|palette-color|color-format)
      local DT_LIB=$DOTS_LIB_DIR/themes name theme_name='' flavor_name=''
      # shellcheck source=themes/core.bash
      source "$DT_LIB/core.bash"
      # Positional data is collected by the completion parser, never evaluated.
      theme_name=${DOTS_POSITIONALS[0]:-} flavor_name=${DOTS_POSITIONALS[1]:-}
      case $type in
        theme)
          dt_discover_ids families || return
          for name in "${DT_DISCOVERY_IDS[@]}"; do dots_candidate "$lead$name"; done ;;
        flavor)
          dt_discover_ids flavors "$theme_name" || return
          for name in "${DT_DISCOVERY_IDS[@]}"; do dots_candidate "$lead$name"; done ;;
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
  local -A DOTS_OPTION_VALUES=()
  (( cursor >= 1 && cursor < ${#words[@]} )) || return 2
  # Standalone wrappers share this same completion protocol.
  local command_name=${words[0]##*/}
  if [[ $command_name == theme ]]; then
    words=(dots theme "${words[@]:1}"); ((cursor+=1))
  elif [[ $command_name != dots ]]; then
    local family_target=$command_name
    words=(dots theme "$family_target" "${words[@]:1}"); ((cursor+=2))
  fi
  local DOTS_CURRENT=${words[cursor]} index=1 token prefix='' help=0 resolved start
  local expected='' expected_option='' positional=1 options=1 long short type description row position lead=''
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
      if [[ $DOTS_CURRENT == --color=* ]]; then dots_value_candidates choice:auto,always,never,none "${DOTS_CURRENT%%=*}="
      else dots_value_candidates choice:auto,always,never "${DOTS_CURRENT%%=*}="; fi
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
    # Anodize accepts its presentation options before the action as well as
    # on leaves. Remove only complete, valid prefix options for route lookup;
    # an option being completed still uses static metadata below.
    if [[ ${words[index]} == anodize ]]; then
      local prefix_end=$((index+1)) prefix_count=0 prefix_value prefix_flag
      while (( prefix_end < cursor )); do
        token=${words[prefix_end]}
        prefix_flag=${token%%=*}
        if [[ $prefix_flag == --interactive ]]; then
          words=("${words[@]:0:prefix_end}" "${words[@]:prefix_end+1}")
          (( --cursor ))
          continue
        fi
        case $prefix_flag in --logo|--logo-layout) ;; *) break ;; esac
        if [[ $token == *=* ]]; then prefix_value=${token#*=}; prefix_count=1
        else
          (( prefix_end+1 < cursor )) || break
          prefix_value=${words[prefix_end+1]}; prefix_count=2
        fi
        case $prefix_flag:$prefix_value in
          --logo:text|--logo:auto|--logo:kitty|--logo:chafa|--logo-layout:auto|--logo-layout:horizontal|--logo-layout:stacked|--logo-layout:icon) ;;
          *) return 0 ;;
        esac
        words=("${words[@]:0:prefix_end}" "${words[@]:prefix_end+prefix_count}")
        (( cursor-=prefix_count ))
      done
    fi
    if [[ ${words[index]} == help ]]; then help=1; (( ++index )); fi
    if [[ ${words[index]} == git && ${words[index+1]:-} == submodule ]] && (( cursor >= index+2 )); then
      dots_resolve "${words[@]:index:cursor-index}"; resolved=$?
      (( resolved != 1 )) || return 1
      if [[ $DOTS_ROUTE == "git submodule" && $DOTS_EXECUTABLE == "$DOTS/bin/dots-git-submodule" ]]; then
        python3 -B "$DOTS_LIB_DIR/git/submodule.py" --complete "${words[@]:index+2:cursor-index-1}"
        return
      fi
    fi
    if (( index == cursor )); then
      for token in "${DOTS_BUILTIN_NAMES[@]}"; do dots_candidate "$token" "${DOTS_BUILTIN_SUMMARY[$token]}"; done
      dots_completion_children '' || return
    elif [[ ${words[index]} == init ]]; then
      if (( cursor == index+1 )); then
        dots_builtin_metadata init
        dots_value_candidates choice:bash,zsh,fish,powershell,nu,xonsh
        (( help )) || dots_candidate --bootstrap 'Print missing-checkout bootstrap'
        (( help )) || dots_candidate --setup 'Install platform configurations'
        (( help )) || dots_candidate --help 'Show command help'
      elif [[ ${words[index+1]} == --bootstrap ]]; then
        dots_value_candidates choice:bash,zsh,powershell
      elif [[ ${words[index+1]} == --setup ]]; then
        if [[ ${words[cursor-1]} == --with-source ]]; then
          dots_value_candidates choice:termux,windows,nvim
        else
          dots_builtin_metadata init
          for row in "${DOTS_META_OPTIONS[@]}"; do
            IFS='|' read -r long short type description <<< "$row"
            [[ $long == --setup ]] || dots_candidate "$long" "$description"
            [[ ! $short ]] || dots_candidate "$short" "$description"
          done
        fi
      fi
    elif [[ ${words[index]} == completion ]]; then
      if (( cursor == index+1 )); then for token in bash zsh fish powershell; do dots_candidate "$token"; done; fi
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
      if [[ ${args[0]:-} == theme ]]; then
        local DT_LIB=$DOTS_LIB_DIR/themes
        source "$DT_LIB/core.bash"
        source "$DT_LIB/families.bash"
        if ((${#args[@]} == 1)); then
          dt_family_index || return
          for token in "${DT_FAMILIES[@]}"; do dt_family_reserved "$token" || dots_candidate "$token" 'Theme palette'; done
        elif ! dt_family_reserved "${args[1]}"; then
          source "$DT_LIB/complete.bash"
          dt_palette_candidates "${args[@]:1}" || return
          ((${#DOTS_SUGGESTIONS[@]} == 0)) || printf '%s\n' "${DOTS_SUGGESTIONS[@]}"
          return 0
        fi
      fi
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
            if [[ $expected ]]; then DOTS_OPTION_VALUES[$expected_option]=$token; expected=; continue; fi
            if (( options )) && [[ $token == -- ]]; then options=0; continue; fi
            if (( options )) && [[ $token == -* ]]; then
              if dots_find_option "${token%%=*}"; then
                if [[ $DOTS_OPTION_TYPE == flag ]]; then DOTS_OPTION_VALUES[${token%%=*}]=1
                elif [[ $token == *=* ]]; then DOTS_OPTION_VALUES[${token%%=*}]=${token#*=}
                else expected=$DOTS_OPTION_TYPE; expected_option=$token; fi
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
