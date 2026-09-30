#!/usr/bin/env bash
# Plain preview fallback when the optional Zsh preview interpreter is absent.
if [[ -d $1 ]]; then
  if command -v eza >/dev/null 2>&1; then eza -a -1 --icons=auto --color=always -- "$1"
  else command ls -A -- "$1"; fi
elif command -v bat >/dev/null 2>&1; then
  command bat --color=always --style=numbers --line-range=:500 -- "$1"
else
  command head -n 500 -- "$1"
fi
