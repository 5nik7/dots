#!/usr/bin/env zsh
# Compatibility entry point for personal preview commands.
exec "${DOTS:-${0:A:h:h}}/scripts/_dots-fzf-preview" "$@"
