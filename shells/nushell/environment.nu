# Resolve at parse time so linked configs and explicit generated hooks agree.
const dots_root = (path self | path expand --strict | path dirname | path dirname | path dirname)
if not ($dots_root | path join 'bin' 'dots' | path exists) {
    error make {msg: 'dots: Nushell startup requires the Dots checkout layout'}
}
$env.DOTS = $dots_root
$env.DOTBIN = ($env.DOTS | path join "bin")
$env.DOTSCRIPTS = ($env.DOTS | path join "scripts")
$env.DOTFILES = ($env.DOTS | path join "config")
$env.DOTCONFIG = $env.DOTFILES
$env.DOTSHHHH = ($env.DOTS | path join "secrets")
$env.SHELLS = ($env.DOTS | path join "shells")
$env.ZSH = ($env.DOTS | path join "shells/zsh")
$env.PWSH = ($env.DOTS | path join "shells/powershell")
for directory in [$env.DOTBIN $env.DOTSCRIPTS] {
    if ($directory | path type) == dir and $directory not-in $env.PATH {
        $env.PATH = ($env.PATH | prepend $directory)
    }
}
