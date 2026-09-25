#!/usr/bin/env bash
# Private structured bridge; never parse the human theme CLI's output.
set -e
DT_LIB=$(cd -- "${BASH_SOURCE[0]%/*}/../themes" && pwd)
source "$DT_LIB/core.bash"
action=$1
shift
dt_load "$1"
case $action in
  resolve) dt_json ;;
  render)
    # The caller supplies a newly allocated temporary directory.
    dt_render "$2"
    ;;
  apply|plan)
    source "$DT_LIB/../ui.bash"
    source "$DT_LIB/state.bash"
    dt_state_preflight
    dt_supported || { dt_error 'theme has no supported adapter'; exit 1; }
    if [[ ${2:-} == background ]]; then
      source "$DT_LIB/backgrounds.bash"
      wallpaper=${3:-}
      if [[ ! $wallpaper ]]; then
        # Used by dt_bg_files in the sourced background adapter.
        # shellcheck disable=SC2034
        DT_BG_ID=$1
        mapfile -d '' -t backgrounds < <(dt_bg_files "$DT_THEME_DIR" | LC_ALL=C sort -zu)
        wallpaper=${backgrounds[0]:-}
      fi
      [[ $wallpaper ]] || { dt_error 'no theme backgrounds'; exit 1; }
      dt_bg_preflight "$wallpaper" || exit 1
    fi
    if [[ $action == apply ]]; then
      dt_set "$1" >&2
      if [[ ${2:-} == background ]]; then
        # commands.bash dispatches when sourced; invoke it in its own process.
        if ! bash -c 'DT_LIB=$1; shift; source "$DT_LIB/commands.bash" bg set "$@"' bash "$DT_LIB" "$wallpaper" >&2; then
          dt_error 'wallpaper action failed; app theme remains published'
          exit 1
        fi
      fi
      dt_generation
      printf '{"schema":1,"status":"complete","generation":"%s"}\n' "$DT_GENERATION"
    else
      preview=$(mktemp -d)
      trap 'rm -rf -- "$preview"' EXIT
      dt_render "$preview"
      # Paths travel as argv to a JSON encoder, never via string interpolation.
      python3 -c 'import json,sys; print(json.dumps({"schema":1,"status":"preview","theme":sys.argv[1],"publish":sys.argv[2],"connectors":sys.argv[3:]}))' "$1" "$DT_ACTIVE" "${DT_CONNECT_TARGETS[@]}"
    fi
    ;;
  *) exit 2 ;;
esac
