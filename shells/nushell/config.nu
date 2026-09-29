# A linked config always loads its own checkout, regardless of old generated hooks.
const dots_loader = (path self | path expand --strict | path dirname | path join 'init.nu')
source $dots_loader
