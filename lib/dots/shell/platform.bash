# Shared detection, also used by noninteractive shells. No external commands.
_dots_detect_platform() {
  local os=${1:-$OSTYPE} release=${2:-/etc/os-release}
  local kernel=${3:-/proc/sys/kernel/osrelease} wslconf=${4:-/etc/wsl-distribution.conf}
  local line name='' id='' key value kernel_name=''
  export is_termux=false is_wsl=false DOTS_PLATFORM=linux distro=unknown
  if [[ -n ${TERMUX_VERSION:-}${TERMUX__PREFIX:-} || ${PREFIX:-} == */com.termux/files/usr ]]; then
    DOTS_PLATFORM=termux
    is_termux=true
    release="${TERMUX__PREFIX:-$PREFIX}/etc/os-release"
  elif [[ $os == msys* || $os == cygwin* ]]; then
    DOTS_PLATFORM=msys
  else
    [[ -r $kernel ]] && IFS= read -r kernel_name < "$kernel"
    if [[ -n ${ZSH_VERSION:-} ]]; then kernel_name=${kernel_name:l}
    else kernel_name=${kernel_name,,}; fi
    if [[ -n ${WSL_DISTRO_NAME:-}${WSL_INTEROP:-} || ${kernel_name} == *microsoft* || -r $wslconf ]]; then
      DOTS_PLATFORM=wsl
      is_wsl=true
    fi
  fi
  if [[ -r $release ]]; then
    while IFS= read -r line; do
      key=${line%%=*}
      value=${line#*=}
      value=${value#\"}; value=${value%\"}
      value=${value#\'}; value=${value%\'}
      if [[ -n ${ZSH_VERSION:-} ]]; then value=${value:l}
      else value=${value,,}; fi
      case $key in
        NAME) name=$value ;;
        ID) id=$value ;;
      esac
    done < "$release"
    distro=${name%% *}
    [[ -n $distro ]] || distro=${id:-unknown}
  fi
  [[ $DOTS_PLATFORM == termux ]] && distro=termux
  [[ $DOTS_PLATFORM == msys && $distro == unknown ]] && distro=msys
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
