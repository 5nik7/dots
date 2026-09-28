#!/usr/bin/env pwsh

function cwd {
    (Get-Location).Path
}

function lwd {
    (Resolve-Path -LiteralPath (Get-Location).Path).Path
}

function spath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    $Path.Replace($HOME, "~")
}

function main {
    $wd1 = cwd
    $wd2 = lwd

    if ($wd1 -eq $wd2) {
        exit 1
    }

    $swd = spath -Path $wd1
    $swd
}

main
