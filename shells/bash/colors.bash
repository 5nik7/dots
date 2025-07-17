#!/usr/bin/env bash

THEME=$(echo "$DOT_THEME" | cut -d '-' -f 1)
if [ $THEME = 'catppuccin' ]; then
  FLAVOR=$(echo "$DOT_THEME" | cut -d '-' -f 2)
  export "$FLAVOR"
fi

if cmd_exists catppuccin; then
  function flavor() {
    command catppuccin "$FLAVOR" "$@"
  }
  function mocha() {
    commandcatppuccin mocha "$@"
  }
  function macchiato() {
    command catppuccin macchiato "$@"
  }
  function frappe() {
    command catppuccin frappe "$@"
  }
  function latte() {
    command catppuccin latte "$@"
  }
  function rosewater() {
    command catppuccin "$FLAVOR" rosewater
  }
  function flamingo() {
    command catppuccin "$FLAVOR" flamingo
  }
  function pink() {
    command catppuccin "$FLAVOR" pink
  }
  function mauve() {
    command catppuccin "$FLAVOR" mauve
  }
  function red() {
    command catppuccin "$FLAVOR" red
  }
  function maroon() {
    command catppuccin "$FLAVOR" maroon
  }
  function peach() {
    command catppuccin "$FLAVOR" peach
  }
  function yellow() {
    command catppuccin "$FLAVOR" yellow
  }
  function green() {
    command catppuccin "$FLAVOR" green
  }
  function teal() {
    command catppuccin "$FLAVOR" teal
  }
  function sky() {
    command catppuccin "$FLAVOR" sky
  }
  function sapphire() {
    command catppuccin "$FLAVOR" sapphire
  }
  function blue() {
    command catppuccin "$FLAVOR" blue
  }
  function lavender() {
    command catppuccin "$FLAVOR" lavender
  }
  function text() {
    command catppuccin "$FLAVOR" text
  }
  function subtext1() {
    command catppuccin "$FLAVOR" subtext1
  }
  function subtext0() {
    command catppuccin "$FLAVOR" subtext0
  }
  function overlay2() {
    command catppuccin "$FLAVOR" overlay2
  }
  function overlay1() {
    command catppuccin "$FLAVOR" overlay1
  }
  function overlay0() {
    command catppuccin "$FLAVOR" overlay0
  }
  function surface2() {
    command catppuccin "$FLAVOR" surface2
  }
  function surface1() {
    command catppuccin "$FLAVOR" surface1
  }
  function surface0() {
    command catppuccin "$FLAVOR" surface0
  }
  function base() {
    command catppuccin "$FLAVOR" base
  }
  function mantle() {
    command catppuccin "$FLAVOR" mantle
  }
  function crust() {
    command catppuccin "$FLAVOR" crust
  }
else
  echo "catppuccin command not found. Please install it to use the colors."
fi
