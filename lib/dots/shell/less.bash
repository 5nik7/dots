# Builtin-only Bash/Zsh less style adapter. Shared contract: less_style.py.
# shellcheck disable=SC2034
_dots_less_style() {
  local fg=${1:-} bg=${2:-} mode=${3:-auto} enabled=${4:-1} owned=0 start
  [[ -z ${_DOTS_LESS_STYLE:-} || ${LESS_TERMCAP_so-} != "$_DOTS_LESS_STYLE" ||
     ${LESS_TERMCAP_se-} != $'\e[0m' ]] || owned=1
  if [[ ( ${LESS_TERMCAP_so+x} || ${LESS_TERMCAP_se+x} ) && $owned == 0 ]]; then
    unset _DOTS_LESS_STYLE; return 0
  fi
  if [[ ${LESS_TERMINFO_smso+x} || ${LESS_TERMINFO_rmso+x} ]]; then
    (( ! owned )) || unset LESS_TERMCAP_so LESS_TERMCAP_se
    unset _DOTS_LESS_STYLE; return 0
  fi
  if [[ $enabled != 1 || ( $mode != always &&
        ( $mode != auto || ${TERM:-dumb} == dumb || -n ${NO_COLOR:-} ) ) ]]; then
    (( ! owned )) || unset LESS_TERMCAP_so LESS_TERMCAP_se
    unset _DOTS_LESS_STYLE; return 0
  fi
  [[ $fg =~ ^#[a-fA-F0-9]{6}$ && $bg =~ ^#[a-fA-F0-9]{6}$ ]] || return 0
  printf -v start '\e[0;38;2;%d;%d;%d;48;2;%d;%d;%dm' \
    "0x${fg:1:2}" "0x${fg:3:2}" "0x${fg:5:2}" \
    "0x${bg:1:2}" "0x${bg:3:2}" "0x${bg:5:2}"
  export LESS_TERMCAP_so=$start LESS_TERMCAP_se=$'\e[0m' _DOTS_LESS_STYLE=$start
}
