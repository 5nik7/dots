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
  function rosewater() {
    catppuccin $FLAVOR "$0"
  }
  function flamingo() {
    catppuccin $FLAVOR "$0"
  }
  function pink() {
    catppuccin $FLAVOR "$0"
  }
  function mauve() {
    catppuccin $FLAVOR "$0"
  }
  function red() {
    catppuccin $FLAVOR "$0"
  }
  function maroon() {
    catppuccin $FLAVOR "$0"
  }
  function peach() {
    catppuccin $FLAVOR "$0"
  }
  function yellow() {
    catppuccin $FLAVOR "$0"
  }
  function green() {
    catppuccin $FLAVOR "$0"
  }
  function teal() {
    catppuccin $FLAVOR "$0"
  }
  function sky() {
    catppuccin $FLAVOR "$0"
  }
  function sapphire() {
    catppuccin $FLAVOR "$0"
  }
  function blue() {
    catppuccin $FLAVOR "$0"
  }
  function lavender() {
    catppuccin $FLAVOR "$0"
  }
  function text() {
    catppuccin $FLAVOR "$0"
  }
  function subtext1() {
    catppuccin $FLAVOR "$0"
  }
  function subtext0() {
    catppuccin $FLAVOR "$0"
  }
  function overlay2() {
    catppuccin $FLAVOR "$0"
  }
  function overlay1() {
    catppuccin $FLAVOR "$0"
  }
  function overlay0() {
    catppuccin $FLAVOR "$0"
  }
  function surface2() {
    catppuccin $FLAVOR "$0"
  }
  function surface1() {
    catppuccin $FLAVOR "$0"
  }
  function surface0() {
    catppuccin $FLAVOR "$0"
  }
  function base() {
    catppuccin $FLAVOR "$0"
  }
  function mantle() {
    catppuccin $FLAVOR "$0"
  }
  function crust() {
    catppuccin $FLAVOR "$0"
  }
if cmd_exists pastel; then
  function escol {
    pastel format ansi-24bit-escapecode "$@"
  }
  function creset {
    esc=$'\033'
    c_reset="${esc}[0m"
    printf "$c_reset"
  }
fi
else
  echo "catppuccin command not found. Please install it to use the colors."
fi
