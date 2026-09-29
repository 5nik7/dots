# The native shell entry point selects the checkout. No home-directory guess.
if [ -n "${DOTS:-}" ]; then
  if [ -r "$DOTS/bin/lib/common.sh" ]; then
    . "$DOTS/bin/lib/common.sh"
    build_color_arrays
  fi
fi
