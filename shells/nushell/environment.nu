# Resolve at parse time so linked configs and explicit generated hooks agree.
const dots_root = (path self | path expand --strict | path dirname | path dirname | path dirname)
if not ($dots_root | path join 'bin' 'dots' | path exists) {
    error make {msg: 'dots: Nushell startup requires the Dots checkout layout'}
}
$env.DOTS = $dots_root
const dots_integration = ($dots_root | path join 'lib/dots/shell/init.nu')
source $dots_integration
