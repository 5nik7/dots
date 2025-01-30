function Invoke-Nvim {
    param (
        [Parameter(Mandatory=$false, ValueFromRemainingArguments=$true)]
        [string[]]$args
    )
    nvim  $args
    Write-Host -NoNewLine "`e[5 q"
}

$env:NEOVIMCONFIG = $env:LOCALAPPDATA + "\nvim"
$env:NEOVIMDATA = $env:LOCALAPPDATA + "\nvim-data"
$env:MASONBIN = $env:NEOVIMDATA + "\mason\bin"

Add-Path -Path $env:MASONBIN