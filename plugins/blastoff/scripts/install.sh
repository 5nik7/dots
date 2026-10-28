#!/usr/bin/env bash
set -u
script_dir=${BASH_SOURCE[0]%/*}
[[ $script_dir == "${BASH_SOURCE[0]}" ]] && script_dir=.
root=$(CDPATH='' cd -- "$script_dir/.." && pwd -P) || exit 1
. "$root/scripts/lifecycle.sh" || exit 3
blastoff_lifecycle "$root" "$@"
