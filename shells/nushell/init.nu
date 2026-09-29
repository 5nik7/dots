const dots_nu_directory = (path self | path expand --strict | path dirname)
const dots_environment = ($dots_nu_directory | path join 'environment.nu')
source $dots_environment
const dots_body = ($dots_nu_directory | path join (if $nu.is-interactive { 'interactive.nu' } else { 'noninteractive.nu' }))
source $dots_body
