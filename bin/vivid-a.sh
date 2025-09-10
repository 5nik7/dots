#!/usr/bin/env bash

for theme in $(vivid themes); do
  echo "Theme: $theme"
  LS_COLORS=$(vivid generate $theme)
  ls $1
  echo
done
