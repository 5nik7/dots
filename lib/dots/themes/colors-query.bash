#!/usr/bin/env bash
DT_LIB=${BASH_SOURCE[0]%/*}
source "$DT_LIB/core.bash"
if [[ ${1:-} == current ]]; then dt_current_id && printf '%s\n' "$REPLY"; exit; fi
if [[ ${1:-} == dir ]]; then dt_find_theme "$2" && printf '%s\n' "$DT_THEME_DIR"; exit; fi
dt_load "$1" && dt_json
