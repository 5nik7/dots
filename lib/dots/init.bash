# Initialization is a code stream. Never source user configuration here.
# shellcheck source-path=SCRIPTDIR
# Generated code is deliberately expanded by the receiving shell.
# shellcheck disable=SC2016
dots_init() {
  local shell=${1-auto} root=$DOTS loader quoted
  if (($# > 1)) || { (($# == 1)) && [[ $1 == auto ]]; }; then dots_error 'Usage: dots init [bash|zsh|fish|powershell|nu|xonsh]'; return 2; fi
  case $shell in
    auto) loader='bash/init.bash zsh/init.zsh' ;;
    bash) loader=bash/init.bash ;;
    zsh) loader=zsh/init.zsh ;;
    fish) loader=fish/init.fish ;;
    powershell) loader=powershell/init.ps1 ;;
    nu) loader=nushell/init.nu ;;
    xonsh) loader=xonsh/init.xsh ;;
    *) dots_error 'Unknown initialization shell; use bash, zsh, fish, powershell, nu, or xonsh'; return 2 ;;
  esac
  [[ $root == /* ]] || root=$PWD/$root
  local file
  for file in $loader; do
    if [[ ! -f $root/shells/$file || ! -r $root/shells/$file ]]; then
      dots_error "Cannot read shell loader: $root/shells/$file"
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
          '  . "$DOTS/shells/zsh/init.zsh"' 'elif [ -n "${BASH_VERSION:-}" ]; then' \
          '  . "$DOTS/shells/bash/init.bash"' 'else' \
          '  printf "%s\n" "dots init: specify a supported shell" >&2' '  false' 'fi'
      else printf '. "$DOTS/shells/%s"\n' "$loader"; fi ;;
    fish)
      quoted=${root//\\/\\\\}; quoted=${quoted//\'/\\\'}
      printf "set -gx DOTS '%s'\nsource \"\$DOTS/shells/fish/init.fish\"\n" "$quoted" ;;
    powershell)
      quoted=${root//\'/\'\'}
      printf "\$env:DOTS = '%s'\n. (Join-Path \$env:DOTS 'shells/powershell/init.ps1')\n" "$quoted" ;;
    nu)
      # Nu double-quoted strings have escapes but no interpolation without $.
      quoted=${root//\\/\\\\}; quoted=${quoted//\"/\\\"}
      quoted=${quoted//$'\n'/\\n}; quoted=${quoted//$'\r'/\\r}; quoted=${quoted//$'\t'/\\t}
      printf '$env.DOTS = "%s"\n' "$quoted"
      printf 'source "%s/shells/nushell/init.nu"\n' "$quoted" ;;
    xonsh)
      quoted=${root//\\/\\\\}; quoted=${quoted//\'/\\\'}
      quoted=${quoted//$'\n'/\\n}; quoted=${quoted//$'\r'/\\r}; quoted=${quoted//$'\t'/\\t}
      printf "\$DOTS = '%s'\nsource @(\$DOTS + '/shells/xonsh/init.xsh')\n" "$quoted" ;;
  esac
}
