function _fzf_preview_file --description "Preview a hovered file or directory."
    set -l file_path "$argv"
    if test -d "$file_path"; and set -q fzf_preview_dir_cmd
        eval "$fzf_preview_dir_cmd "(string escape -- "$file_path")
    else if test -f "$file_path"; and set -q fzf_preview_file_cmd
        eval "$fzf_preview_file_cmd "(string escape -- "$file_path")
    else if test -x "$DOTS/scripts/_dots-fzf-preview"
        command "$DOTS/scripts/_dots-fzf-preview" "$file_path"
    else if test -d "$file_path"
        command ls -A -F -- "$file_path"
    else if test -f "$file_path"
        command bat --style=numbers --color=always -- "$file_path"
    else
        _fzf_report_file_type "$file_path" "unavailable"
    end
end
