#!/usr/bin/zsh

function walbg() {
    wal -n -i "$@"
    swaybg -i "$(< "${HOME}/.cache/wal/wal")"
}