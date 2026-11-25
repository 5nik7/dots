use less.nu _dots-less-style
def --wrapped .ln [...args] {
    if ($env.dots_options.DOTS_INIT_COMMANDS? | default '1') != '1' { error make {msg: 'Dots command integration is disabled'} }
    if $nu.os-info.name == 'windows' {
        let engines = (which pwsh powershell | where type == 'external')
        if ($engines | is-empty) { error make {msg: 'Native PowerShell is required for dots link on Windows'} }
        ^($engines.0.path) -NoLogo -NoProfile -File ($env.DOTS | path join 'scripts/dots-link.ps1') ...$args
    } else {
        ^($env.DOTS | path join 'bin/dots') link ...$args
    }
}
hide-env --ignore-errors DOTRUBY RUBYCOMP
let dots_retired_roots = ([$env.DOTS ($env.DOTS_PROFILE_CHECKOUT? | default '') (($env.HOME? | default $env.USERPROFILE?) | path join 'dots')] | where {|root| $root != ''})
let dots_normalize_path = {|entry|
    let path = if $nu.os-info.name == 'windows' { $entry | str replace --all '\' '/' | str lowercase } else { $entry }
    $path | str replace --regex '/+$' ''
}
let dots_retired_paths = ($dots_retired_roots | each {|root| do $dots_normalize_path ($root | path join 'ruby' 'completion')})
$env.PATH = ($env.PATH | where {|entry| (do $dots_normalize_path $entry) not-in $dots_retired_paths})
for name in ['DOTS_ENV_HOOKS' 'DOTS_ENV_ORIGINS'] {
    let value = ($env | get -o $name)
    if $value != null {
        load-env {($name): ($value | split row ';' | where {|record| $record != '' and $record !~ '^(DOTRUBY|RUBYCOMP)[:|]'} | str join ';')}
    }
}
# Shared profile and application environment, transferred as inert JSON.
let dots_python = (which --all python3 python | where type == 'external' | where {|candidate|
    if $nu.os-info.name == 'windows' {
        let path = ($candidate.path | str replace --all '\' '/' | str lowercase)
        ($path !~ '/windowsapps/') and ($path | str ends-with '.exe')
    } else { true }
})
if ($dots_python | is-empty) { error make {msg: 'dots: Python is required for native initialization'} }
$env._DOTS_PYTHON = $dots_python.0.path
# A discovered manager executable must never acquire Python during startup or
# completion. These overrides apply only to the selected child invocation.
def --wrapped _dots-python [...args: string] {
    with-env {PYTHON_MANAGER_AUTOMATIC_INSTALL: 'false'} {
        # Legacy launchers enable acquisition when these names are present,
        # even when their value is "0". Hide them only in this child scope.
        hide-env --ignore-errors PYLAUNCHER_ALLOW_INSTALL PYLAUNCHER_ALWAYS_INSTALL
        ^($env._DOTS_PYTHON) ...$args | complete
    }
}
do --env {
    let prepared = ($env._DOTS_PREPARED_NU? | default {})
    hide-env --ignore-errors _DOTS_PREPARED_NU
    let document = if ($prepared | describe | str starts-with 'record') and ($prepared.exports?.DOTS_PROFILE_CHECKOUT? | default '') == $env.DOTS {
        $prepared
    } else {
        let resolved = (_dots-python -B ($env.DOTS | path join 'lib/dots/native_completion.py') --environment)
        if $resolved.exit_code != 0 { error make {msg: 'dots: native environment preparation failed'} }
        $resolved.stdout | from json
    }
    $env.dots_options = $document.settings.values
    $env.dots_option_sources = $document.settings.origins
    $env._DOTS_NATIVE_PATHS = ($document.shell_paths | upsert config $document.settings.path)
    $env._DOTS_COMPLETION_NAMES = $document.completion_commands
    let data = $document.exports
    for name in $document.unset { hide-env --ignore-errors $name }
    for name in ($env._dots_profile_map_names? | default []) { hide-env --ignore-errors $name }
    mut names = []
    for row in ($document.maps | transpose name paths) {
        let name = $'($row.name)_map'
        load-env {($name): $row.paths}
        $names = ($names | append $name)
    }
    $env._dots_profile_map_names = $names
    load-env ($data | reject PATH)
    $env.PATH = ($data.PATH | split row (char esep))
}

# Build native Nu maps from the same resolved settings as the other adapters.
def --env _dots-load [] {
    mut paths = {}
    mut exports = {}
    for line in (open --raw ($env.DOTS | path join 'lib/dots/shell/paths.tsv') | lines) {
        let fields = ($line | split row "\t")
        let value = if $fields.2 == '.' { $env.DOTS } else { $env.DOTS | path join $fields.2 }
        if $fields.0 != '-' { $exports = ($exports | upsert $fields.0 $value) }
        if $fields.1 != '-' { $paths = ($paths | upsert $fields.1 $value) }
    }
    $env.dot = ($paths | upsert config $env._DOTS_NATIVE_PATHS.config | upsert state $env._DOTS_NATIVE_PATHS.state)
    load-env $exports
    $env.THEME = ($env.dot.state | path join 'current/theme')
    $env.THEMESCMD = $env._DOTS_NATIVE_PATHS.theme_command
    $env.THEMESBIN = ($env.dot.state | path join 'themes/commands/current/bin')

}
def --env _dots-refresh-theme [] {
    if $env.dots_options.DOTS_INIT_THEME != '1' {
        _dots-less-style '' '' auto '0'
        return
    }
    let marker = ($env.dot.state | path join 'themes/current')
    if not ($marker | path exists) { return }
    let generation = (open --raw $marker | str trim)
    if $generation == ($env._DOTS_THEME_GENERATION? | default '') { return }
    if $generation !~ '^g\.[a-zA-Z0-9]+$' { error make {msg: 'dots: invalid theme generation'} }
    mut data = {}
    for line in (open --raw ($env.dot.state | path join themes generations $generation shell.tsv) | lines) {
        let fields = ($line | split row "\t")
        if ($fields | length) != 3 or $fields.0 !~ '^(@theme|@palette|@role|[a-z_][a-zA-Z0-9_]*)$' or $fields.1 !~ '^[a-zA-Z0-9_-]+$' {
            error make {msg: 'dots: invalid palette data'}
        }
        let entry = ($data | get -o $fields.0 | default {} | upsert $fields.1 $fields.2)
        $data = ($data | upsert $fields.0 $entry)
    }
    let identity = ($data | get '@theme')
    if ($identity.id | is-empty) { error make {msg: 'dots: missing theme identity'} }
    $env.dots_palette = ($data | get '@palette')
    $env.dots_roles = ($data | get '@role')
    $env.dots_colors = if $env.dots_options.DOTS_INIT_COLORS == '1' { $data | reject '@theme' '@palette' '@role' } else { {} }
    $env.DOTS_THEME_FAMILY = $identity.family
    $env.FLAVOR = $identity.flavor
    $env.DOTS_THEME_ID = $identity.id
    $env.dot = ($env.dot | upsert theme $identity.id)
    let ls_file = ($env.dot.state | path join themes generations $generation ls_colors)
    if ($ls_file | path exists) { $env.LS_COLORS = (open --raw $ls_file | str trim --right) }
    _dots-less-style ($data | get -o foreground.hex | default '') ($data | get -o lighter_background.hex | default ($data | get -o background.hex | default '')) $env.dots_options.DOTS_COLOR '1'
    let visual_file = ($env.dot.state | path join themes generations $generation visual.tsv)
    if ($visual_file | path exists) {
        mut visual_env = {}
        for line in (open --raw $visual_file | lines) {
            let fields = ($line | split row "\t")
            if ($fields | length) != 3 { error make {msg: 'dots: invalid visual data'} }
            if $fields.0 == 'env' {
                if $fields.1 !~ '^[A-Z][A-Z0-9_]*$' { error make {msg: 'dots: invalid visual variable'} }
                $visual_env = ($visual_env | upsert $fields.1 $fields.2)
            }
        }
        load-env $visual_env
        if 'DOTS_THEME_FZF_COLORS' in $visual_env and $env._DOTS_VISUAL_FZF_BASE?.pid? == $nu.pid and 'FZF_DEFAULT_OPTS_FILE' not-in $env {
            let base = ($visual_env.DOTS_THEME_FZF_OPTS? | default $env._DOTS_VISUAL_FZF_BASE.options)
            let preview = if ($visual_env.DOTS_THEME_FZF_PREVIEW? == '0') { " --preview='_dots-fzf-preview --selection {f}'" } else { '' }
            $env.FZF_DEFAULT_OPTS = ($base + $preview + ' --color=' + $env.DOTS_THEME_FZF_COLORS)
        }
    }
    $env._DOTS_THEME_GENERATION = $generation
}
_dots-load
if $nu.is-interactive {
    if 'FZF_DEFAULT_OPTS' not-in $env and 'FZF_DEFAULT_OPTS_FILE' not-in $env {
        $env.FZF_DEFAULT_OPTS = "--bind=ctrl-x:toggle-preview --preview-window=right:hidden:50% --preview='_dots-fzf-preview --selection {f}'"
        $env._DOTS_VISUAL_FZF_BASE = {pid: $nu.pid, options: $env.FZF_DEFAULT_OPTS}
    }
    if $env.dots_options.DOTS_INIT_COLORS == '0' { $env.dots_colors = {} }
    $env.esc = "\u{1b}"
    $env.ESC = $env.esc
    $env.rst = (ansi reset)
    $env.RST = $env.rst
    $env._DOTS_THEME_GENERATION = ''
    try { _dots-refresh-theme } catch { print -e 'dots: theme artifact unavailable; run theme refresh' }
    if not ($env._DOTS_PROMPT_READY? | default false) {
        $env.config.hooks.pre_prompt = ($env.config.hooks.pre_prompt | append {||
            if $env.dots_options.DOTS_THEME_AUTO_UPDATE == '1' { try { _dots-refresh-theme } }
        })
        $env._DOTS_PROMPT_READY = true
    }
    if not ($env._DOTS_COMPLETION_READY? | default false) {
        $env._DOTS_PREVIOUS_COMPLETER = $env.config.completions.external.completer
        $env.config.completions.external.completer = {|spans|
            let names_file = ($env.dot.state | path join 'themes/commands/current/names')
            let families = if ($names_file | path exists) { open --raw $names_file | lines } else { [] }
            let basename = ($spans.0 | path basename)
            let identity = if $nu.os-info.name == 'windows' { $basename | str lowercase } else { $basename }
            let command = ($identity | str replace --regex '\.ps1$' '')
            if $env.dots_options.DOTS_INIT_COMPLETION == '1' and $command in ($env._DOTS_COMPLETION_NAMES | append $families) {
                let result = (_dots-python -B ($env.DOTS | path join 'lib/dots/native_completion.py') --complete nu ...$spans)
                if $result.exit_code != 0 { return [] }
                $result.stdout | from json | default []
            } else if ($env._DOTS_PREVIOUS_COMPLETER | describe) == closure {
                do $env._DOTS_PREVIOUS_COMPLETER $spans
            } else { null }
        }
        $env._DOTS_COMPLETION_READY = true
    }
}


let profile_paths = ($env.DOTS_PROFILE_PATHS? | default "" | split row (char esep) | where {|entry| $entry != ""})
let owned_paths = ([$env.DOTBIN $env.DOTSCRIPTS] | where {|entry| $entry | path exists })
let theme_paths = if $env.dots_options.DOTS_INIT_COMMANDS == '1' { [$env.THEMESBIN] } else { [] }
let old_paths = ($env.PATH | where {|entry| $entry != $env.THEMESBIN and $entry != ($env.DOTS | path join 'themes/bin') })
$env.PATH = ($owned_paths | append $theme_paths | append $profile_paths | append $old_paths | uniq)
