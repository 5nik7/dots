#!/usr/bin/env bash
# Private preparation bridge. stdout is a NUL-delimited data stream.
# shellcheck source-path=SCRIPTDIR
set -o pipefail
DT_LIB=${BASH_SOURCE[0]%/*}
source "$DT_LIB/core.bash" || exit 1
source "$DT_LIB/views.bash" || exit 1
source "$DT_LIB/state.bash" || exit 1
dt_current_id || exit 1
id=$REPLY
dt_load "$id" && dt_supported && dt_fingerprint || exit 1
fingerprint=$REPLY
dt_generation || exit 1
dt_state_preflight || exit 1
if [[ -e $DT_COMMANDS/current || -L $DT_COMMANDS/current ]]; then
  [[ -L $DT_COMMANDS/current ]] || { dt_error 'generated command pointer is not managed'; exit 1; }
  commands=$(readlink -- "$DT_COMMANDS/current")
  if ! dt_commands_valid_target "$commands" || ! dt_commands_verify "$commands"; then
    dt_error 'generated commands changed'; exit 1
  fi
fi
for tool in flock sync sha256sum mktemp awk cat mkdir mv rm cp ln readlink cmp find sort tee chmod wc; do
  command -v "$tool" >/dev/null || { dt_error "theme setup requires $tool"; exit 1; }
done
case ${1:-} in
  inspect)
    printf '%s\0%s\0%s\0' "$id" "$fingerprint" "$DT_GENERATION" ;;
  prepare)
    # The Python coordinator holds themes/lock and commands/lock. No live
    # connectors, pointers, hooks, reloads or wallpaper actions run here.
    [[ $fingerprint == "${2:-}" ]] || { dt_error 'theme inputs changed after preview'; exit 1; }
    umask 077
    mkdir -p -- "$DT_STATE/generations" "$DT_COMMANDS/generations" || exit 1
    dt_prepare_generation "${DT_GENERATION:-none}" "$fingerprint" >&2 || exit 1
    printf '%s\0' "$DT_PREPARED"
    if [[ -f $DT_PREPARED/commands-new ]]; then cat "$DT_PREPARED/commands-new" | tr -d '\n'; fi
    printf '\0' ;;
  *) exit 2 ;;
esac
