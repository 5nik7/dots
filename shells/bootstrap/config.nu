# Nushell resolves source paths before evaluating its configuration.
const dots_bootstrap = ($nu.home-dir | path join '.local/share/dots/bootstrap/entry.nu')
source $dots_bootstrap
