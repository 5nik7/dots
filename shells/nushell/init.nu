const dots_nu_directory = (path self | path expand --strict | path dirname)
const dots_environment = ($dots_nu_directory | path join 'environment.nu')
source $dots_environment
# Nushell resolves source paths at parse time. Parsing the ordered files in
# the first env_change keeps native declarations visible at the first input.
if $nu.is-interactive {
    $env.config.show_banner = false
    let dirs = $env._DOTS_NATIVE_PATHS.profile_shells
    let profile_sources = {|name|
        $dirs | each {|dir| $dir | path join $name } | where {|file| ($file | path type) == file }
    }
    let files = (do $profile_sources 'init.nu' | append ($dots_nu_directory | path join 'interactive.nu') | append (do $profile_sources 'local.nu'))
    let sources = ($files | each {|file| 'source ' + ($file | to json --raw) } | str join '; ')
    # env_change runs before pre_prompt so selected tools can define commands for the first input.
    $env._DOTS_NU_STARTUP = (date now | into int)
    let finish = '; _dots-prepare-tools'
    let hook = ('$env.config.hooks.env_change = ($env.config.hooks.env_change | reject -o _DOTS_NU_STARTUP); hide-env _DOTS_NU_STARTUP; ' + $sources + $finish)
    $env.config.hooks.env_change._DOTS_NU_STARTUP = [$hook]
}
