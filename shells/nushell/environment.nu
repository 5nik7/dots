# Resolve at parse time so linked configs and explicit generated hooks agree.
const dots_root = (path self | path expand --strict | path dirname | path dirname | path dirname)
if not ($dots_root | path join 'bin' 'dots' | path exists) {
    error make {msg: 'dots: Nushell startup requires the Dots checkout layout'}
}
$env.DOTS = $dots_root
const dots_integration = ($dots_root | path join 'lib/dots/shell/init.nu')
source $dots_integration

# Only paths formerly exported by Dots are retired.
for root in [($env.DOTFILES? | default '') ($env.DOTCONFIG? | default '')
    ($env.DOTS | path join 'config') ($env.DOTS | path join 'configs')
    ($nu.home-dir | path join 'dots' 'config') ($nu.home-dir | path join 'dots' 'configs')
    ($nu.home-dir | path join '.dots' 'config') ($nu.home-dir | path join '.dots' 'configs')] {
    if ($root != '') and (($env.STARSHIP_CONFIG? | default '') == ($root | path join 'starship' 'starship.toml')) {
        hide-env STARSHIP_CONFIG
        break
    }
}
