# The normal checkout can be parsed directly. First acquisition completes
# before the REPL parses a one-shot source hook for the newly available file.
const dots_default = ($nu.home-dir | path join 'dots/shells/nushell/init.nu')
const dots_pin = ($nu.home-dir | path join '.local/share/dots/bootstrap/init.nu')
const dots_static = if ($dots_pin | path exists) { $dots_pin } else if ($dots_default | path exists) { $dots_default } else { null }
let exe = if $nu.os-info.name == 'windows' { 'dots.ps1' } else { 'dots' }
let usable = {|entry|
    if $entry == null or not ($entry | path exists) { return false }
    if $nu.os-info.name == 'windows' {
        if $entry !~ '^(?:[a-zA-Z]:[\\/]|\\\\[^?.])' { return false }
    } else if not ($entry | str starts-with '/') { return false }
    let root = ($entry | path expand | path dirname | path dirname | path dirname)
    let cli = ($root | path join bin $exe)
    ($root | path join 'lib/dots/shell/startup.bash' | path exists) and (if $nu.os-info.name == 'windows' {
        ($cli | path type) == 'file'
    } else { not (which --all $cli | is-empty) })
}
let explicit = ($env.DOTS_BOOTSTRAP_DIR? | default '')
let from_env = if $explicit != '' { $explicit | path join 'shells/nushell/init.nu' }
let cli = (which --all $exe | where type == 'external' | get -o 0.path)
let from_cli = if $cli != null { $cli | path expand | path dirname | path dirname | path join 'shells/nushell/init.nu' }
let pin_record = ($nu.home-dir | path join '.local/share/dots/bootstrap/checkout')
let pinned = if ($pin_record | path type) == 'file' {
    try { open --raw $pin_record | str trim --right --char (char nl) | str trim --right --char (char cr) | path join 'shells/nushell/init.nu' }
}
let preferred = if $explicit != '' {
    if (do $usable $from_env) { $from_env }
} else if (do $usable $from_cli) {
    $from_cli
} else if (do $usable $pinned) {
    $pinned
} else if (do $usable $dots_static) {
    $dots_static
} else if (do $usable $dots_default) {
    $dots_default
}
if not $nu.is-interactive {
    # Nu can only parse literal source paths offline. Only source a static
    # alternative if it is the selected checkout.
    if $preferred != null and $dots_static != null and (
        ($preferred | path expand) == ($dots_static | default '' | path expand)
    ) {
        source $dots_static
    }
} else {
    let entry = if $preferred != null {
        $preferred
    } else {
        let result = if $nu.os-info.name == 'windows' {
            ^powershell.exe -NoProfile -NonInteractive -File ($nu.home-dir | path join '.local/share/dots/bootstrap/locate.ps1') interactive -Utf8 -Shell nu | complete
        } else {
            ^sh ($nu.home-dir | path join '.local/share/dots/bootstrap/locate.sh') interactive nu | complete
        }
        if $result.stderr != '' { print --stderr --no-newline $result.stderr }
        if $result.exit_code == 0 and ($result.stdout | str trim) != '' {
            $result.stdout | str trim --right | path join 'shells/nushell/init.nu'
        }
    }
    if $entry != null {
        $env.config.show_banner = false
        let root = ($entry | path expand | path dirname | path dirname | path dirname)
        let bridge = ($root | path join 'lib/dots/native_completion.py')
        mut files = [$entry]
        mut finish = ''
        if ($bridge | path exists) and ($root | path join 'shells/nushell/environment.nu' | path exists) {
            let python = (which --all python3 python | where type == 'external' | where {|candidate|
                if $nu.os-info.name == 'windows' {
                    let path = ($candidate.path | str replace --all '\' '/' | str lowercase)
                    ($path !~ '/windowsapps/') and ($path | str ends-with '.exe')
                } else { true }
            } | get -o 0.path)
            if $python != null {
                let resolved = (with-env {DOTS: $root, PYTHON_MANAGER_AUTOMATIC_INSTALL: 'false'} {
                    hide-env --ignore-errors PYLAUNCHER_ALLOW_INSTALL PYLAUNCHER_ALWAYS_INSTALL
                    ^$python -B $bridge --nu-startup | complete
                })
                if $resolved.exit_code == 0 {
                    let data = ($resolved.stdout | from json)
                    $files = $data.startup_sources
                    $finish = '; _dots-prepare-tools'
                    $env._DOTS_PREPARED_NU = ($data | reject startup_sources)
                }
            }
        }
        let sources = ($files | each {|file| 'source ' + ($file | to json --raw) } | str join '; ')
        # env_change runs before pre_prompt so selected tools can define commands for the first input.
        $env._DOTS_NU_STARTUP = (date now | into int)
        let hook = ('$env.config.hooks.env_change = ($env.config.hooks.env_change | reject -o _DOTS_NU_STARTUP); hide-env _DOTS_NU_STARTUP; ' + $sources + $finish)
        $env.config.hooks.env_change._DOTS_NU_STARTUP = [$hook]
    }
}
