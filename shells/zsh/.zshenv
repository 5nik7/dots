#  ╔═╗╔═╗╦ ╦╔═╗╔╗╔╦  ╦
#  ╔═╝╚═╗╠═╣║╣ ║║║╚╗╔╝
# o╚═╝╚═╝╩ ╩╚═╝╝╚╝ ╚╝

prefix="${TERMUX__PREFIX:-$PREFIX}"

if [[ -r /etc/os-release ]]; then
  distro=$(awk -F'=' '"NAME" == $1 { gsub("\"", "", $2); print tolower($2); }' /etc/os-release)
  distro="${distro%% *}"
elif [[ -r "$prefix/etc/os-release" ]]; then
  distro=$(awk -F'=' '"NAME" == $1 { gsub("\"", "", $2); print tolower($2); }' "$prefix/etc/os-release")
  distro="${distro%% *}"
elif [[ -n "${TERMUX_VERSION:-}" ]]; then
  distro='termux'
else
  distro='unknown'
fi

export distro

dotstro() {
  local distro="${distro:-unknown}"
  echo "$distro"
}

if [[ "$distro" == "termux" ]]; then
  declare -x is_termux=true
fi

if [[ -r /etc/wsl-distribution.conf ]]; then
  declare -x is_wsl=true
fi

is_termux() {
  local verbose=0
  if [[ $1 == '-v' ]]; then
    verbose=1
    shift
  fi
  if [[ "$is_termux" == true ]] &>/dev/null; then
    ((verbose)) && echo "true"
    return 0
  else
    ((verbose)) && echo "false"
    return 1
  fi
}

is_wsl() {
  local verbose=0
  if [[ $1 == '-v' ]]; then
    verbose=1
    shift
  fi
  if [[ "$is_wsl" == true ]] &>/dev/null; then
    ((verbose)) && echo "true"
    return 0
  else
    ((verbose)) && echo "false"
    return 1
  fi
}

has_pip_pkg() {
  local pkg="$1"
  command -v pip &>/dev/null || return 1
  pip show $pkg -q 2>/dev/null || return 1
  return 0
}
