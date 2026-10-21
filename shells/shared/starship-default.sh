# shellcheck shell=bash
# Retire only values previously exported by Dots; explicit overrides stay valid.
if [[ -n ${STARSHIP_CONFIG:-} ]]; then
  for _dots_starship_root in "${_dots_app_config:-}" "${DOTFILES:-}" "${DOTCONFIG:-}" \
      "$DOTS/config" "$DOTS/configs" "$HOME/dots/config" "$HOME/dots/configs" \
      "$HOME/.dots/config" "$HOME/.dots/configs"; do
    if [[ -n $_dots_starship_root && $STARSHIP_CONFIG == "${_dots_starship_root%/}/starship/starship.toml" ]]; then
      unset STARSHIP_CONFIG
      break
    fi
  done
  unset _dots_starship_root
fi
