# Shared Bash lifecycle boundary. Source only from shipped entry points.
blastoff_lifecycle() {
    local root=$1 runtime=${BLASTOFF_PYTHON:-python3} label
    shift
    case $OSTYPE in
        msys*|mingw*) label='MSYS2 / Git Bash' ;;
        cygwin*) label='Cygwin' ;;
        *) label='' ;;
    esac
    if [[ -n $label ]]; then
        printf 'blastoff: %s Bash lifecycle is unsupported; open native PowerShell 7+ in the source directory and run .\\install.ps1 -WhatIf (or .\\uninstall.ps1 -WhatIf). No files changed.\n' "$label" >&2
        return 3
    fi
    if ! command -v -- "$runtime" >/dev/null 2>&1; then
        printf 'blastoff: Python runtime not found: %s; install Python 3.11+ or set BLASTOFF_PYTHON.\n' "$runtime" >&2
        return 3
    fi
    exec "$runtime" -I -B "$root/scripts/install.py" --_bash-host-v1 "$OSTYPE" "$@"
}
