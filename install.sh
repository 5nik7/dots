#!/bin/sh
# Sets up Dots, Blastoff and pkgs together from an existing checkout. No downloads or machine changes before planning.
set -eu
setup_root=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd -P)
. "$setup_root/lib/dots/bootstrap-ui.sh"
if [ "${1:-}" = --bootstrap ]; then
  shift
  exec sh "$setup_root/bootstrap.sh" --destination "$setup_root" "$@"
fi
if ! command -v python3 >/dev/null 2>&1 || ! python3 -B -c 'import sys;sys.exit(sys.version_info < (3,11))' >/dev/null 2>&1; then
  [ "${DOTS_BOOTSTRAP_READY:-}" != 1 ] || { dots_bootstrap_error 'Python is still unavailable after prerequisite preparation' "$@"; exit 1; }
  exec sh "$setup_root/bootstrap.sh" --destination "$setup_root" "$@"
fi
export DOTS="$setup_root"
exec python3 -B "$setup_root/lib/dots/files/install.py" install "$@"
