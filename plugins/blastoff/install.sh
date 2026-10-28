#!/bin/sh
# Bundled application lifecycle belongs to the complete Dots installation.
set -eu
bundle_root=$(CDPATH='' cd -- "$(dirname -- "$0")/../.." && pwd -P)
exec sh "$bundle_root/install.sh" "$@"
