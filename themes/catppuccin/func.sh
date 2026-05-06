if has catppuccin; then

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
    local format=${1:-esc}
    catppuccin $FLAVOR -r ${format} "$0"
  }
  function flamingo() {
    local format=${1:-esc}
    catppuccin $FLAVOR -r ${format} "$0"
  }
  function pink() {
    local format=${1:-esc}
    catppuccin $flavor -r ${format} "$0"
  }
  function mauve() {
    local format=${1:-esc}
    catppuccin $flavor -r ${format} "$0"
  }
  function red() {
    local format=${1:-esc}
    catppuccin $flavor -r ${format} "$0"
  }
  function maroon() {
    local format=${1:-esc}
    catppuccin $flavor -r ${format} "$0"
  }
  function peach() {
    local format=${1:-esc}
    catppuccin $flavor -r ${format} "$0"
  }
  function yellow() {
    local format=${1:-esc}
    catppuccin $flavor -r ${format} "$0"
  }
  function green() {
    local format=${1:-esc}
    catppuccin $flavor -r ${format} "$0"
  }
  function teal() {
    local format=${1:-esc}
    catppuccin $flavor -r ${format} "$0"
  }
  function sky() {
    local format=${1:-esc}
    catppuccin $flavor -r ${format} "$0"
  }
  function sapphire() {
    local format=${1:-esc}
    catppuccin $flavor -r ${format} "$0"
  }
  function blue() {
    local format=${1:-esc}
    catppuccin $flavor -r ${format} "$0"
  }
  function lavender() {
    local format=${1:-esc}
    catppuccin $flavor -r ${format} "$0"
  }
  function text() {
    local format=${1:-esc}
    catppuccin $flavor -r ${format} "$0"
  }
  function subtext1() {
    local format=${1:-esc}
    catppuccin $flavor -r ${format} "$0"
  }
  function subtext0() {
    local format=${1:-esc}
    catppuccin $flavor -r ${format} "$0"
  }
  function overlay2() {
    local format=${1:-esc}
    catppuccin $flavor -r ${format} "$0"
  }
  function overlay1() {
    local format=${1:-esc}
    catppuccin $flavor -r ${format} "$0"
  }
  function overlay0() {
    local format=${1:-esc}
    catppuccin $flavor -r ${format} "$0"
  }
  function surface2() {
    local format=${1:-esc}
    catppuccin $flavor -r ${format} "$0"
  }
  function surface1() {
    local format=${1:-esc}
    catppuccin $flavor -r ${format} "$0"
  }
  function surface0() {
    local format=${1:-esc}
    catppuccin $flavor -r ${format} "$0"
  }
  function base() {
    local format=${1:-esc}
    catppuccin $flavor -r ${format} "$0"
  }
  function mantle() {
    local format=${1:-esc}
    catppuccin $flavor -r ${format} "$0"
  }
  function crust() {
    local format=${1:-esc}
    catppuccin $flavor -r ${format} "$0"
  }
else
  echo "catppuccin command not found. Please install it to use the colors."
fi
