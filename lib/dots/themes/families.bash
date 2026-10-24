# shellcheck disable=SC2034
# Data-only family index. Built on demand, never during shell startup.
dt_family_reserved() {
  case $1 in themes|env|theme|dots|anodize|current_theme|help|list|current|dir|show|color|colors|init|set|refresh|switcher|install|update|remove|bg|plugin|plugins|files|summary) return 0 ;; *) return 1 ;; esac
}
dt_family_index() {
  local id dir family flavor file key DT_THEME_DIR
  local -A DT_DATA=() DT_LINES=()
  local -a DT_KEYS=()
  declare -gA DT_FAMILY_VARIANTS=() DT_FAMILY_DEFAULTS=() DT_FAMILY_DIRS=() DT_ID_FAMILIES=() DT_ID_FLAVORS=()
  declare -ga DT_FAMILIES=()
  local -A seen=()
  dt_discover_ids theme-id || return
  local -a ids=("${DT_DISCOVERY_IDS[@]}")
  if [[ ${DT_INDEX_REPLACE_ID:-} ]]; then
    local present=0
    for id in "${ids[@]}"; do [[ $id != "$DT_INDEX_REPLACE_ID" ]] || present=1; done
    ((present)) || ids+=("$DT_INDEX_REPLACE_ID")
  fi
  for id in "${ids[@]}"; do
    [[ $id != "${DT_INDEX_REMOVE_ID:-}" ]] || continue
    if [[ $id == "${DT_INDEX_REPLACE_ID:-}" ]]; then dir=$DT_INDEX_REPLACE_DIR
    else dt_find_theme "$id" || return; dir=$DT_THEME_DIR; fi
    family=$id flavor=default
    if [[ -f $dir/theme.toml ]]; then
      [[ ! -L $dir/theme.toml ]] || { dt_error 'theme metadata must be a regular file'; return 1; }
      dt_parse "$dir/theme.toml" metadata || return
      family=${DT_DATA[family]:-$id} flavor=${DT_DATA[flavor]:-default}
    fi
    dt_theme_id "$family" && dt_id "$flavor" || { dt_error "invalid family metadata: $id"; return 1; }
    key=$family:$flavor
    [[ ! ${DT_FAMILY_VARIANTS[$key]+yes} ]] || { dt_error "duplicate family/flavor: $key"; return 1; }
    DT_FAMILY_VARIANTS[$key]=$id DT_ID_FAMILIES[$id]=$family DT_ID_FLAVORS[$id]=$flavor
    if [[ ! ${seen[$family]:-} ]]; then
      DT_FAMILIES+=("$family"); seen[$family]=1
      DT_FAMILY_DIRS[$family]=$dir
    fi
  done
  for family in "${DT_FAMILIES[@]}"; do
    for file in "$DT_ROOT/$family/theme.toml" "$DT_USER_THEMES/$family/theme.toml"; do
      [[ -f $file && ! -L $file ]] || continue
      dt_parse "$file" metadata || return
      DT_FAMILY_DIRS[$family]=${file%/*}
      [[ ! ${DT_DATA[default_flavor]:-} ]] || DT_FAMILY_DEFAULTS[$family]=${DT_DATA[default_flavor]}
    done
    dt_family_flavors "$family"
    if [[ ! ${DT_FAMILY_DEFAULTS[$family]:-} && ${#DT_FAMILY_FLAVORS[@]} == 1 ]]; then
      DT_FAMILY_DEFAULTS[$family]=${DT_FAMILY_FLAVORS[0]}
    fi
  done
  dt_family_sort DT_FAMILIES
}
dt_family_flavors() {
  local key
  declare -ga DT_FAMILY_FLAVORS=()
  for key in "${!DT_FAMILY_VARIANTS[@]}"; do
    [[ $key != "$1:"* ]] || DT_FAMILY_FLAVORS+=("${key#*:}")
  done
  dt_family_sort DT_FAMILY_FLAVORS
}
dt_family_sort() {
  local -n items=$1
  local i j value LC_ALL=C
  for ((i=1;i<${#items[@]};i++)); do
    value=${items[i]}; j=$i
    while ((j>0)) && [[ ${items[j-1]} > $value ]]; do items[j]=${items[j-1]}; ((j-=1)) || :; done
    items[j]=$value
  done
}
dt_family_pick() {
  local family=$1 flavor=${2:-${DT_FAMILY_DEFAULTS[$1]:-}}
  [[ $flavor ]] || { dt_error "choose a flavor for $family"; return 1; }
  REPLY=${DT_FAMILY_VARIANTS[$family:$flavor]:-}
  [[ $REPLY ]] || { dt_error "unknown flavor: $family $flavor"; return 1; }
}
