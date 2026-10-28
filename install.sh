#!/bin/sh
# Sets up Dots, Blastoff and pkgs together from an existing checkout. No downloads or machine changes before planning.
set -eu
setup_root=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd -P)
. "$setup_root/lib/dots/bootstrap-ui.sh"
command -v python3 >/dev/null 2>&1 || { dots_bootstrap_error 'dots setup requires Python 3.9 or newer' "$@"; exit 1; }
export DOTS="$setup_root"
exec python3 -B "$setup_root/lib/dots/files/install.py" install "$@"
