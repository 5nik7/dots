# Initialization is a code stream. Never source user configuration here.
# shellcheck source-path=SCRIPTDIR
# Generated code is deliberately expanded by the receiving shell.
# shellcheck disable=SC2016
dots_init() {
  if [[ ${1:-} == --bootstrap ]]; then
    [[ $# == 2 && ( $2 == bash || $2 == zsh || $2 == powershell ) ]] || { dots_error 'Usage: dots init --bootstrap bash|zsh|powershell'; return 2; }
    python3 -B "$DOTS_LIB_DIR/bootstrap_snippet.py" "$2"
    return
  fi
  if [[ ${1:-} == --setup ]]; then
    shift
    python3 -B "$DOTS_LIB_DIR/files/install.py" install "$@"
    return
  fi
  local shell=${1-auto} root=$DOTS loader quoted
  if (($# > 1)) || { (($# == 1)) && [[ $1 == auto ]]; }; then dots_error 'Usage: dots init [bash|zsh|fish|powershell|nu|xonsh]'; return 2; fi
  case $shell in
    auto) loader='init.bash init.zsh' ;;
    bash) loader=init.bash ;;
    zsh) loader=init.zsh ;;
    fish) loader=init.fish ;;
    powershell) loader=init.ps1 ;;
    nu) loader=init.nu ;;
    xonsh) loader=init.xsh ;;
    *) dots_error 'Unknown initialization shell; use bash, zsh, fish, powershell, nu, or xonsh'; return 2 ;;
  esac
  [[ $root == /* ]] || root=$PWD/$root
  root=$(cd -- "$root" && pwd -P) || return 1
  local file
  for file in $loader; do
    if [[ ! -f $root/lib/dots/shell/$file || ! -r $root/lib/dots/shell/$file ]]; then
      dots_error "Cannot read shell loader: $root/lib/dots/shell/$file"
      return 1
    fi
  done
  # Shell-specific literal quoting; never interpolate environment file contents.
  case $shell in
    auto|bash|zsh)
      quoted=${root//\'/\'\\\'\'}
      printf "export DOTS='%s'\n" "$quoted"
      if [[ $shell == auto ]]; then
        printf '%s\n' 'if [ -n "${ZSH_VERSION:-}" ]; then' \
          '  . "$DOTS/lib/dots/shell/init.zsh"' 'elif [ -n "${BASH_VERSION:-}" ]; then' \
          '  . "$DOTS/lib/dots/shell/init.bash"' 'else' \
          '  printf "%s\n" "dots init: specify a supported shell" >&2' '  false' 'fi'
      else printf '. "$DOTS/lib/dots/shell/%s"\n' "$loader"; fi ;;
    fish)
      quoted=${root//\\/\\\\}; quoted=${quoted//\'/\\\'}
      printf "set -gx DOTS '%s'\nsource \"\$DOTS/lib/dots/shell/init.fish\"\n" "$quoted" ;;
    powershell)
      quoted=${root//\'/\'\'}
      printf "\$env:DOTS = '%s'\n. (Join-Path \$env:DOTS 'lib/dots/shell/init.ps1')\n" "$quoted" ;;
    nu)
      # Nu double-quoted strings have escapes but no interpolation without $.
      quoted=${root//\\/\\\\}; quoted=${quoted//\"/\\\"}
      quoted=${quoted//$'\n'/\\n}; quoted=${quoted//$'\r'/\\r}; quoted=${quoted//$'\t'/\\t}
      printf '$env.DOTS = "%s"\n' "$quoted"
      printf 'source "%s/lib/dots/shell/init.nu"\n' "$quoted" ;;
    xonsh)
      quoted=${root//\\/\\\\}; quoted=${quoted//\'/\\\'}
      quoted=${quoted//$'\n'/\\n}; quoted=${quoted//$'\r'/\\r}; quoted=${quoted//$'\t'/\\t}
      printf "\$DOTS = '%s'\nsource @(\$DOTS + '/lib/dots/shell/init.xsh')\n" "$quoted" ;;
  esac
}
