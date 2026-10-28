#!/usr/bin/env bash
set -u
script_dir=${BASH_SOURCE[0]%/*}
[[ $script_dir == "${BASH_SOURCE[0]}" ]] && script_dir=.
root=$(CDPATH='' cd -- "$script_dir/.." && pwd -P) || exit 1
runtime=${BLASTOFF_PYTHON:-python3}
if ! command -v -- "$runtime" >/dev/null 2>&1; then
    printf 'blastoff: Python runtime not found: %s; install Python 3.11+ or set BLASTOFF_PYTHON.\n' "$runtime" >&2
    exit 3
fi
exec "$runtime" -I "$root/scripts/package.py" "$@"
