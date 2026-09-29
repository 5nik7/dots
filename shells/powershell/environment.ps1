# DOTS is established by the resolved native entry point.
$env:DOTBIN = (Join-Path $env:DOTS 'bin')
$env:DOTSCRIPTS = (Join-Path $env:DOTS 'scripts')
$env:DOTFILES = (Join-Path $env:DOTS 'config')
$env:DOTCONFIG = $env:DOTFILES
$env:DOTSHHHH = (Join-Path $env:DOTS 'secrets')
$env:SHELLS = (Join-Path $env:DOTS 'shells')
$env:ZSH = (Join-Path $env:DOTS 'shells/zsh')
$env:PWSH = (Join-Path $env:DOTS 'shells/powershell')
foreach ($directory in @($env:DOTBIN, $env:DOTSCRIPTS)) {
    $entries = $env:PATH -split [regex]::Escape([string][IO.Path]::PathSeparator)
    if ((Test-Path -LiteralPath $directory -PathType Container) -and $entries -cnotcontains $directory) {
        $env:PATH = $directory + [IO.Path]::PathSeparator + $env:PATH
    }
}
