# Run native generators once in the interactive shell. A profile may already
# have installed a tool, a prompt, or its own key bindings.
set -l tool mode key
if contains -- all $argv
    set argv zoxide direnv mise atuin tv starship
end
for tool in $argv
    contains -- $tool $_dots_fish_tools; and continue
    command -sq -- $tool; or continue
    set -l arguments init fish
    set -l prior
    switch $tool
        case zoxide
            functions -q __zoxide_hook; and continue
            contains -- --no-cmd $argv; and set -a arguments --no-cmd
        case direnv
            functions -q __direnv_export_eval; and continue
            set arguments hook fish
        case mise
            functions -q __mise_env_eval; and continue
            set arguments activate fish
        case atuin
            functions -q _atuin_preexec; and continue
            set -a arguments --disable-up-arrow --disable-ctrl-r
        case tv
            functions -q tv_smart_autocomplete; and continue
            for mode in default insert
                for key in ctrl-r ctrl-t
                    set -a prior (bind --user --mode $mode $key 2>/dev/null)
                end
            end
        case starship
            functions -q __starship_set_job_count; and continue
            set -l prompt_file (functions --details fish_prompt)
            if not string match -q 'embedded:*' -- "$prompt_file"; and test "$prompt_file" != "$__fish_data_dir/functions/fish_prompt.fish"
                continue
            end
            # A profile can customize just the right prompt.
            if functions -q fish_right_prompt
                set -l right_file (functions --details fish_right_prompt)
                if not string match -q 'embedded:*' -- "$right_file"; and test "$right_file" != "$__fish_data_dir/functions/fish_right_prompt.fish"
                    continue
                end
            end
            set -a arguments --print-full-init
        case '*'
            continue
    end
    # Only evaluate complete output from a successful generator. Some failed
    # tools still emit partial, executable shell code.
    set -l generated (command $tool $arguments | string collect)
    test $pipestatus[1] -eq 0; and test -n "$generated"; or continue
    eval "$generated"
    set -l result $status
    for binding in $prior
        eval $binding
    end
    test $result -ne 0; or set -ga _dots_fish_tools $tool
end
