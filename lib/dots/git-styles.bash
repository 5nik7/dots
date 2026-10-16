# Lazy Git presentation roles. Published data is never executed or resolved here.
# shellcheck shell=bash disable=SC2034
dots::_git_styles_load() {
  [[ ${_DOTS_GIT_STYLES_READY:-} ]] && return 0
  _DOTS_GIT_STYLES_READY=1
  declare -gA _DOTS_GIT_STYLES=()
  local file=${XDG_STATE_HOME:-$HOME/.local/state}/dots/current/theme/git-styles.tsv
  local data='' header line key code valid=1
  [[ -f $file && ! -L $file ]] || return 0
  IFS= read -r -N 2097153 data < "$file" || :
  (( ${#data} <= 2097152 )) || return 0
  {
    IFS= read -r header
    [[ $header == $'dots-git-styles\t1' ]] || valid=0
    while IFS= read -r line || [[ $line ]]; do
      key=${line%%$'\t'*}; code=${line#*$'\t'}
      if [[ $line != *$'\t'* || ! $key =~ ^[a-z][a-z0-9_]*$ ||
            ! $code =~ ^[0-9\;]{1,128}$ || ${_DOTS_GIT_STYLES[$key]+yes} ]]; then
        valid=0; break
      fi
      _DOTS_GIT_STYLES[$key]=$code
    done
  } <<< "${data%$'\n'}"
  (( valid )) || _DOTS_GIT_STYLES=()
  return 0
}

# Returns a style in REPLY. Caller supplies the actual destination descriptor.
dots::git_style() {
  local role=$1 code
  dots::style "${2:-1}"
  REPLY=''
  [[ $DOTS_UI_RESET ]] || return 0
  dots::_git_styles_load
  case $role in
    repo) code='1;94' ;;
    branch|untracked) code=95 ;;
    modified|behind|detached|missing) code=93 ;;
    staged|added|clean|ahead) code=92 ;;
    deleted|blocked) code=91 ;;
    conflict) code='1;91' ;;
    renamed|copied) code=96 ;;
    ignored) code='2;90' ;;
    *) code=94 ;;
  esac
  printf -v REPLY '\e[%sm' "${_DOTS_GIT_STYLES[$role]:-$code}"
}
