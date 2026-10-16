# Data-only palette completion. Never execute a theme or generated command.
dt_palette_candidates() {
  local target=$1 family flavor='' token name id='' previous='' color='' action=''
  shift
  dt_family_index || return
  if [[ ${DT_ID_FAMILIES[$target]:-} ]]; then
    family=${DT_ID_FAMILIES[$target]} flavor=${DT_ID_FLAVORS[$target]}
  elif [[ ${DT_FAMILY_DIRS[$target]:-} ]]; then family=$target
  else return 0; fi
  for token; do
    case $previous in
      -f|--flavor) flavor=$token; previous=''; continue ;;
      -c|--color) color=$token; previous=''; continue ;;
      -F|--format) previous=''; continue ;;
    esac
    case $token in
      -f|--flavor|-c|--color|-F|--format|--completion|completion) previous=$token ;;
      set|init|--init) action=$token ;;
      --color=*|show|--raw|-r|--array|-a|--all|color) ;;
      *) if [[ ${DT_FAMILY_VARIANTS[$family:$token]:-} ]]; then flavor=$token; else color=$token; fi ;;
    esac
  done
  case $previous in
    --completion|completion) for name in bash zsh fish; do dots_candidate "$name"; done; return ;;
    -F|--format) for name in "${DT_FORMATS[@]}"; do dots_candidate "$name"; done; return ;;
    -f|--flavor) dt_family_flavors "$family"; for name in "${DT_FAMILY_FLAVORS[@]}"; do dots_candidate "$name"; done; return ;;
  esac
  if [[ $action == set ]]; then
    for name in --dry-run --background --help; do dots_candidate "$name"; done; return
  elif [[ $action ]]; then return; fi
  if [[ $color && ! $previous ]]; then
    for name in "${DT_FORMATS[@]}"; do dots_candidate "$name"; done; return
  fi
  if [[ ! $previous ]]; then
    dt_family_flavors "$family"
    for name in "${DT_FAMILY_FLAVORS[@]}" show set color init --color=auto --color=always --color=never --color=none --help --raw --array --all --flavor --color --format --completion; do dots_candidate "$name"; done
  fi
  if dt_family_pick "$family" "$flavor" 2>/dev/null; then
    id=$REPLY
    if dt_load_native "$id" 2>/dev/null; then for name in "${DT_NAMES[@]}"; do dots_candidate "$name"; done; fi
  fi
}
