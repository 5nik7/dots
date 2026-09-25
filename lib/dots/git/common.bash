# Adapted from git-it 0.1.0; see LICENSE in this directory.
canonical_dir() { (cd -- "$1" && pwd -P); }

# Preserve embedded AND trailing newlines, removing only the command's terminator.
text_cmd() {
    local rc
    REPLY=$("$@"; rc=$?; printf '.'; exit "$rc"); rc=$?
    REPLY=${REPLY%.}
    REPLY=${REPLY%$'\n'}
    return "$rc"
}

# Commands passed here must output NUL-terminated records. Preserve exit status.
records_cmd() {
    local last rc
    mapfile -d '' -t RECORDS < <("$@"; printf '\0%d\0' "$?")
    last=$((${#RECORDS[@]} - 1)); rc=${RECORDS[last]}
    unset 'RECORDS[last]'; unset 'RECORDS[last-1]'
    return "$rc"
}

json_string() {
    local s=$1 ch i n LC_ALL=C
    REPLY='"'
    for ((i=0; i<${#s}; i++)); do
        ch=${s:i:1}
        case $ch in
            '"') REPLY+='\"' ;; \\) REPLY+=$'\\\\' ;;
            *) printf -v n '%d' "'$ch"
               if ((n < 32)); then printf -v ch '\\u%04x' "$n"; fi
               REPLY+=$ch ;;
        esac
    done
    REPLY+='"'
}

display() {
    local s=$1 ch i n LC_ALL=C
    REPLY=''
    for ((i=0; i<${#s}; i++)); do
        ch=${s:i:1}; printf -v n '%d' "'$ch"
        if ((n < 32 || n == 127)); then printf -v ch '\\x%02x' "$n"; fi
        REPLY+=$ch
    done
}

