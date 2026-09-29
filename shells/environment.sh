# shellcheck shell=bash
# Shared Bash/Zsh defaults. Keep private and shell-specific modules in native loaders.
# DOTS is established by the native entry point, never inherited as a default.
export DOTBIN="$DOTS/bin"
export DOTSCRIPTS="$DOTS/scripts"
export DOTFILES="$DOTS/config"
export DOTCONFIG="$DOTFILES"
export DOTSHHHH="$DOTS/secrets"
export SHELLS="$DOTS/shells"
export ZSH="$SHELLS/zsh"
export PWSH="$SHELLS/powershell"

_dots_environment_paths() {
  local directory
  # Match the existing Zsh prepend sequence; preserve entries already present.
  for directory in "$DOTBIN" "$DOTSCRIPTS"; do
    [[ -d $directory ]] || continue
    case :${PATH:-}: in
      *:"$directory":*) ;;
      *) export PATH="$directory${PATH:+:$PATH}" ;;
    esac
  done
}
_dots_environment_paths
unset -f _dots_environment_paths
