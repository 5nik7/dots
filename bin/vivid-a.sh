#!/usr/bin/env bash

declare -r esc=$'\033'
declare -r c_reset="${esc}[0m"
declare -r bold="${esc}[1m"
declare -r dim="${esc}[2m"
declare -r italic="${esc}[3m"
declare -r underline="${esc}[4m"
declare -r rev="${esc}[7m"
declare -r fg_red="${esc}[31m"
declare -r fg_green="${esc}[32m"
declare -r fg_yellow="${esc}[33m"

has() {
  command -v "$1" &> /dev/null
}

for theme in $(vivid themes); do
  printf "${underline}${bold}%s:${c_reset}\n" "$theme"
  LS_COLORS=$(vivid generate $theme)
  if has eza; then
    eza --icons $@
  else
    ls $@
  fi
  echo
done
