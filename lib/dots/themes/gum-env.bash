# Sourceable Bash/Zsh startup adapter for the trusted published Gum environment.
# Missing artifacts are optional. Publication and CLI data paths never source it.
if [[ -f ${XDG_STATE_HOME:-$HOME/.local/state}/dots/current/theme/gum_env.sh &&
      -r ${XDG_STATE_HOME:-$HOME/.local/state}/dots/current/theme/gum_env.sh ]]; then
  # shellcheck disable=SC1091
  source "${XDG_STATE_HOME:-$HOME/.local/state}/dots/current/theme/gum_env.sh"
fi
