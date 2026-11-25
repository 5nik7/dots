# Nu's shipped prompt is a closure too. Recognize its native source so a
# profile-defined left or right prompt always keeps ownership.
def _dots-default-prompts [] {
    let defaults = (config env --default)
    [$env.PROMPT_COMMAND? $env.PROMPT_COMMAND_RIGHT?] | all {|prompt|
        if $prompt == null { true } else if ($prompt | describe) == closure {
            try { $defaults | str contains (view source $prompt) } catch { false }
        } else { false }
    }
}

# Keep existing FZF and user bindings when another native tool supplies the same chord.
def --env _dots-keep-keybindings [prior: list] {
    let added = ($env.config.keybindings | where {|binding|
        $prior | all {|old|
            let different_modifier = (($old.modifier | str lowercase) != ($binding.modifier | str lowercase))
            let different_key = (($old.keycode | str lowercase) != ($binding.keycode | str lowercase))
            $different_modifier or $different_key or ([$old.mode] | flatten | all {|mode| $mode not-in ([$binding.mode] | flatten)})
        }
    })
    $env.config.keybindings = ($prior ++ $added)
}

# direnv's Nu interface is its JSON export on PWD changes.
def --env _dots-direnv-update [] {
    let update = (^direnv export json | complete)
    if $update.stderr != '' { print --stderr --no-newline $update.stderr }
    if $update.exit_code != 0 or ($update.stdout | str trim | is-empty) { return }
    let changes = ($update.stdout | from json)
    for pair in ($changes | transpose name value) {
        if $pair.value == null {
            hide-env --ignore-errors $pair.name
        } else if ($pair.name | str lowercase) == 'path' {
            $env.PATH = ($pair.value | split row (char esep))
        } else {
            load-env {($pair.name): $pair.value}
        }
    }
}

def --env _dots-direnv-init [] {
    $env.config.hooks.env_change.PWD = (($env.config.hooks.env_change.PWD? | default []) | append {|before, after| _dots-direnv-update })
    _dots-direnv-update
}

# The early profile may select native tools. Generate only installed selections,
# after local configuration has established PATH, and keep session code in memory.
def --env _dots-prepare-tools [] {
    let request = ($env.dots_shell_tools? | default [])
    if ($request | is-empty) { return }
    let selected = if ($request | describe) == string { $request | split words } else { $request }
    let done = if $env._DOTS_NU_TOOLS?.pid? == $nu.pid { $env._DOTS_NU_TOOLS.loaded } else { [] }
    let names = [zoxide mise atuin tv starship direnv] | where {|tool|
        let wanted = ($tool not-in $done and ($tool in $selected or 'all' in $selected))
        $wanted and ($tool != 'starship' or (_dots-default-prompts)) and (which --all $tool | where type == external | is-not-empty)
    }
    if ($names | is-empty) { return }
    let result = (_dots-python -B ($env.DOTS | path join lib/dots/shell/nu_tools.py) ...$names)
    if $result.exit_code != 0 { return }
    let data = ($result.stdout | from json)
    $env.config.hooks.pre_prompt = ($data.hooks ++ $env.config.hooks.pre_prompt)
    $env._DOTS_NU_TOOLS = {pid: $nu.pid, loaded: ($done ++ $data.loaded)}
}
