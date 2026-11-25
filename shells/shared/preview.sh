#!/usr/bin/env bash
# Compatibility entry point for personal preview commands.
exec "${DOTS:-$(dirname -- "${BASH_SOURCE[0]}")/../..}/scripts/_dots-fzf-preview" "$@"
