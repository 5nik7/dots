# shellcheck disable=SC1090,SC1091,SC2153
_dots_bash_generated() {
  local output
  has "$1" || return 1
  output=$("$@") && [[ -n $output ]] &&
    command bash --noprofile --norc -n <<< "$output" || return 1
  REPLY=$output
}
declare -gA _DOTS_BASH_TOOL_READY
[[ ! -r $HOME/.cargo/env ]] || source "$HOME/.cargo/env"
[[ ! -r $HOME/.atuin/bin/env ]] || source "$HOME/.atuin/bin/env"
[[ ! -r $HOME/.pythonrc ]] || export PYTHONSTARTUP="$HOME/.pythonrc"
export NVM_DIR="${NVM_DIR:-$HOME/.nvm}"
if [[ -d $HOME/.bun ]]; then export BUN_INSTALL="$HOME/.bun"; prepath "$BUN_INSTALL/bin"; fi
if [[ -r $NVM_DIR/nvm.sh && -z ${_DOTS_BASH_TOOL_READY[nvm]:-} ]]; then
  if source "$NVM_DIR/nvm.sh"; then
    [[ ! -r $NVM_DIR/bash_completion ]] || source "$NVM_DIR/bash_completion"
    _DOTS_BASH_TOOL_READY[nvm]=1
  fi
fi
# Evaluate at source scope: some native integrations declare global shell state.
for _dots_bash_tool in zoxide direnv batpipe usage batman atuin tv mise rbenv starship; do
  [[ -z ${_DOTS_BASH_TOOL_READY[$_dots_bash_tool]:-} ]] || continue
  if case $_dots_bash_tool in
    zoxide) _dots_bash_generated zoxide init bash ;;
    direnv) _dots_bash_generated direnv hook bash ;;
    batpipe)
      # Its native shell export contract is fixed; avoid process-tree detection
      # (restricted on Termux) and quote executable paths for less's child shell.
      if has batpipe; then
        printf -v _dots_bash_batpipe_path '%q' "$(command -v batpipe)"
        printf -v REPLY 'export LESSOPEN=%q LESS=%q BATPIPE=color; unset LESSCLOSE' \
          "|$_dots_bash_batpipe_path %s" "${LESS:-} -R"
      else false; fi ;;
    usage) _dots_bash_generated usage g completion-init bash ;;
    batman) _dots_bash_generated batman --export-env ;;
    atuin) _dots_bash_generated atuin init bash ;;
    tv) _dots_bash_generated tv init bash ;;
    mise) _dots_bash_generated mise activate bash ;;
    rbenv) _dots_bash_generated "$HOME/.rbenv/bin/rbenv" init - --no-rehash bash ;;
    starship) _dots_bash_generated starship init bash ;;
  esac
  then
    if eval "$REPLY"; then
      _DOTS_BASH_TOOL_READY[$_dots_bash_tool]=1
      # A newly available history/search tool may replace Readline bindings.
      case $_dots_bash_tool in atuin|tv) unset _DOTS_BASH_FZF_READY ;; esac
    fi
  fi
 done
unset _dots_bash_tool _dots_bash_batpipe_path
export DIRENV_LOG_FORMAT=$'\033[0;90mdirenv: %s\033[0m'
