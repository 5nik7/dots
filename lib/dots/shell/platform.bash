# Native counterpart of platform_info.detect; no external commands.
_dots_detect_platform() {
  local os=${1:-$OSTYPE} release=${2:-/etc/os-release}
  local kernel=${3:-/proc/sys/kernel/osrelease}
  local line key value kernel_name='' prefix=${TERMUX__PREFIX:-${PREFIX:-}}
  export is_termux=false is_wsl=false DOTS_PLATFORM=linux distro=unknown
  export DOTS_RUNTIME=linux DOTS_DISTRO_FAMILY='' DOTS_DISTRO_VERSION=''
  if [[ $os == msys* || $os == cygwin* || $os == mingw* ]]; then
    DOTS_PLATFORM=windows DOTS_RUNTIME=${os%%-*}
  elif [[ $prefix == */com.termux/files/usr || ( -n ${TERMUX_VERSION:-} && $prefix == */usr ) ]]; then
    DOTS_PLATFORM=termux DOTS_RUNTIME=android is_termux=true
    release=$prefix/etc/os-release
  else
    [[ ! -r $kernel ]] || IFS= read -r kernel_name < "$kernel"
    if [[ -n ${ZSH_VERSION:-} ]]; then kernel_name=${kernel_name:l}; else kernel_name=${kernel_name,,}; fi
    if [[ $kernel_name == *microsoft* || -n ${WSL_INTEROP:-}${WSL_DISTRO_NAME:-} ]]; then
      DOTS_PLATFORM=wsl is_wsl=true
    fi
  fi
  if [[ $DOTS_PLATFORM != windows && -r $release ]]; then
    while IFS= read -r line; do
      key=${line%%=*}; value=${line#*=}
      value=${value#\"}; value=${value%\"}; value=${value#\'}; value=${value%\'}
      case $key in
        ID) if [[ -n ${ZSH_VERSION:-} ]]; then distro=${value:l}; else distro=${value,,}; fi ;;
        ID_LIKE) if [[ -n ${ZSH_VERSION:-} ]]; then DOTS_DISTRO_FAMILY=${value:l}; else DOTS_DISTRO_FAMILY=${value,,}; fi ;;
        VERSION_ID) DOTS_DISTRO_VERSION=$value ;;
      esac
    done < "$release"
  fi
  [[ $DOTS_PLATFORM != termux && $DOTS_PLATFORM != windows ]] || distro=$DOTS_PLATFORM
  [[ $distro =~ ^[a-z0-9][a-z0-9_.-]*$ ]] || distro=unknown
  export DOTS_DISTRO=$distro
  return 0
}
_dots_detect_platform
function dotstro { printf '%s\n' "${distro:-unknown}"; }
function is_termux {
  [[ ${1:-} != -v ]] || printf '%s\n' "${is_termux:-false}"
  [[ ${is_termux:-false} == true ]]
}
function is_wsl {
  [[ ${1:-} != -v ]] || printf '%s\n' "${is_wsl:-false}"
  [[ ${is_wsl:-false} == true ]]
}
