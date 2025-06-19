THEME=$(echo "$DOT_THEME" | cut -d '-' -f 1)
if [ $THEME = 'catppuccin' ]; then
  FLAVOR=$(echo "$DOT_THEME" | cut -d '-' -f 2)
  export "$FLAVOR"
fi

if cmd_exists catppuccin; then
  function flavor() {
    catppuccin "$FLAVOR" "$@"
  }
  function mocha() {
    catppuccin mocha "$@"
  }
  function macchiato() {
    catppuccin macchiato "$@"
  }
  function frappe() {
    catppuccin frappe "$@"
  }
  function latte() {
    catppuccin latte "$@"
  }
  rosewater() {
    catppuccin $FLAVOR "$0"
  }
  flamingo() {
    catppuccin $FLAVOR "$0"
  }
  pink() {
    catppuccin $FLAVOR "$0"
  }
  mauve() {
    catppuccin $FLAVOR "$0"
  }
  red() {
    catppuccin $FLAVOR "$0"
  }
  maroon() {
    catppuccin $FLAVOR "$0"
  }
  peach() {
    catppuccin $FLAVOR "$0"
  }
  yellow() {
    catppuccin $FLAVOR "$0"
  }
  green() {
    catppuccin $FLAVOR "$0"
  }
  teal() {
    catppuccin $FLAVOR "$0"
  }
  sky() {
    catppuccin $FLAVOR "$0"
  }
  sapphire() {
    catppuccin $FLAVOR "$0"
  }
  blue() {
    catppuccin $FLAVOR "$0"
  }
  lavender() {
    catppuccin $FLAVOR "$0"
  }
  text() {
    catppuccin $FLAVOR "$0"
  }
  subtext1() {
    catppuccin $FLAVOR "$0"
  }
  subtext0() {
    catppuccin $FLAVOR "$0"
  }
  overlay2() {
    catppuccin $FLAVOR "$0"
  }
  overlay1() {
    catppuccin $FLAVOR "$0"
  }
  overlay0() {
    catppuccin $FLAVOR "$0"
  }
  surface2() {
    catppuccin $FLAVOR "$0"
  }
  surface1() {
    catppuccin $FLAVOR "$0"
  }
  surface0() {
    catppuccin $FLAVOR "$0"
  }
  base() {
    catppuccin $FLAVOR "$0"
  }
  mantle() {
    catppuccin $FLAVOR "$0"
  }
  crust() {
    catppuccin $FLAVOR "$0"
  }
fi
