use less.nu _dots-less-style
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
if (which python3 | is-not-empty) {
    let resolved = (^python3 -B ($env.DOTS | path join 'lib/dots/native_environment.py') --document | complete)
    if $resolved.exit_code == 0 {
        let document = ($resolved.stdout | from json)
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
}

# Native Nu environment records are retained by Nu, not exported as shell code.
def _dots-valid [kind: string, value: string] {
    match $kind {
        bool => ($value in ['0' '1'])
        style => ($value in ['auto' 'always' 'never'])
        suggestions => ($value in ['deja' 'autosuggestions' 'none'])
        id => ($value =~ '^[a-z][a-z0-9_]*(-[a-z0-9_]+)*$')
        _ => false
    }
}
def --env _dots-load [] {
    mut config = ($env.DOTS_CONFIG_FILE? | default (($env.XDG_CONFIG_HOME? | default (($env.HOME? | default $env.USERPROFILE?) | path join '.config')) | path join 'dots/config.env'))
    mut values = {}
    mut origins = {}
    mut kinds = {}
    for line in (open --raw ($env.DOTS | path join 'lib/dots/shell/settings.tsv') | lines) {
        let fields = ($line | split row "\t")
        $values = ($values | upsert $fields.0 $fields.2)
        $kinds = ($kinds | upsert $fields.0 $fields.1)
        $origins = ($origins | upsert $fields.0 default)
    }
    mut seen = []
    if ($config | path exists) {
        for raw in (open --raw $config | lines) {
            let line = ($raw | str trim)
            if ($line | is-empty) or ($line | str starts-with '#') { continue }
            let parts = ($line | split row -n 2 '=')
            if ($parts | length) != 2 { error make {msg: 'dots: invalid setting'} }
            let key = ($parts.0 | str trim)
            if $key not-in ($kinds | columns) or $key in $seen { error make {msg: 'dots: unknown or duplicate setting'} }
            let value = ($parts.1 | str trim | str replace -r '^"(.*)"$' '$1' | str replace -r "^'(.*)'$" '$1')
            if not (_dots-valid ($kinds | get $key) $value) { error make {msg: $'dots: invalid ($key)'} }
            $values = ($values | upsert $key $value)
            $origins = ($origins | upsert $key config)
            $seen = ($seen | append $key)
        }
    }
    if ($env.DOTS_CONFIG_FILE? | default '' | is-empty) {
        let profile_config = (^python3 -B ($env.DOTS | path join 'lib/dots/profile_config.py') __settings-json | from json)
        let profile_settings = $profile_config.settings
        $config = $profile_config.path
        for key in ($profile_settings | columns) {
            if $key in ($kinds | columns) {
                $values = ($values | upsert $key ($profile_settings | get $key | get value))
                $origins = ($origins | upsert $key ($profile_settings | get $key | get source))
            }
        }
    }
    for key in ($kinds | columns) {
        let override = ($env | get -o $key | default '')
        if $override != '' {
            if not (_dots-valid ($kinds | get $key) $override) { error make {msg: $'dots: invalid override ($key)'} }
            $values = ($values | upsert $key $override)
            $origins = ($origins | upsert $key environment)
        }
    }
    $env.dots_options = $values
    $env.dots_option_sources = $origins
    mut paths = {}
    mut exports = {}
    for line in (open --raw ($env.DOTS | path join 'lib/dots/shell/paths.tsv') | lines) {
        let fields = ($line | split row "\t")
        let value = if $fields.2 == '.' { $env.DOTS } else { $env.DOTS | path join $fields.2 }
        if $fields.0 != '-' { $exports = ($exports | upsert $fields.0 $value) }
        if $fields.1 != '-' { $paths = ($paths | upsert $fields.1 $value) }
    }
    $env.dot = ($paths | upsert config $config | upsert state (($env.XDG_STATE_HOME? | default (($env.HOME? | default $env.USERPROFILE?) | path join '.local/state')) | path join dots))
    load-env $exports
    $env.THEMESCMD = ($env.dot.bin | path join theme)
    $env.THEMESBIN = ($env.dot.state | path join 'themes/commands/current/bin')
    $env.PATH = ($env.PATH | where {|entry| $entry != $env.THEMESBIN and $entry != ($env.DOTS | path join 'themes/bin') })
    for directory in [$env.DOTBIN $env.DOTSCRIPTS] {
        if ($directory | path exists) and $directory not-in $env.PATH { $env.PATH = ($env.PATH | prepend $directory) }
    }
    if $env.dots_options.DOTS_INIT_COMMANDS == '1' { $env.PATH = ($env.PATH | append $env.THEMESBIN) }
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
    $env.THEME = $identity.family
    $env.FLAVOR = $identity.flavor
    $env.DOTS_THEME_ID = $identity.id
    $env.dot = ($env.dot | upsert theme $identity.id)
    let ls_file = ($env.dot.state | path join themes generations $generation ls_colors)
    if ($ls_file | path exists) { $env.LS_COLORS = (open --raw $ls_file | str trim --right) }
    _dots-less-style ($data | get -o foreground.hex | default '') ($data | get -o lighter_background.hex | default ($data | get -o background.hex | default '')) $env.dots_options.DOTS_COLOR '1'
    $env._DOTS_THEME_GENERATION = $generation
}
_dots-load
if $nu.is-interactive {
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
            if $env.dots_options.DOTS_INIT_COMPLETION == '1' and $spans.0 in ([dots theme] | append $families) {
                let result = (^($env.DOTS | path join bin dots) __complete bash (($spans | length) - 1) -- ...$spans | complete)
                if $result.exit_code != 0 { return [] }
                $result.stdout | lines | each {|line|
                    let fields = ($line | split row "\t")
                    if $fields.0 == candidate { {value: $fields.1, description: ($fields | get -o 2 | default '')} }
                } | compact
            } else if ($env._DOTS_PREVIOUS_COMPLETER | describe) == closure {
                do $env._DOTS_PREVIOUS_COMPLETER $spans
            } else { null }
        }
        $env._DOTS_COMPLETION_READY = true
    }
}


let profile_paths = ($env.DOTS_PROFILE_PATHS? | default "" | split row (char esep) | where {|entry| $entry != ""})
$env.PATH = ($profile_paths | append $env.PATH | uniq)
