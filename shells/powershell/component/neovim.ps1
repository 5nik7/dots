function neovim-fix {
    param (
        [string] $args
    )
    nvim.exe @args
    Write-Host -NoNewLine "`e[5 q"
}

$env:NEOVIMCONFIG = $env:LOCALAPPDATA + "\nvim"
$env:NEOVIMDATA = $env:LOCALAPPDATA + "\nvim-data"
$env:MASONBIN = $env:NEOVIMDATA + "\mason\bin"

Add-Path -Path $env:MASONBIN