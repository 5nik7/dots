﻿function q {
    Exit
}

Set-Alias -Name c -Value Clear-Host
Set-Alias -Name path -Value Get-Path
Set-Alias -Name env -Value Get-Env
Set-Alias -Name which -Value Show-Command
Set-Alias -Name touch -Value New-File
Set-Alias -Name rlp -Value rl
Set-Alias -Name ln -Value Set-Link
Set-Alias -Name clr -Value Write-Color
Set-Alias -Name err -Value Write-Err
Set-Alias -Name wrn -Value Write-Warn
Set-Alias -Name scs -Value Write-Success
Set-Alias -Name nfo -Value Write-Info
Set-Alias -Name edit -Value Edit-Item
Set-Alias -Name e -Value Edit-Item
Set-Alias -Name ep -Value Edit-Profile
Set-Alias -Name dev -Value cdev
Set-Alias -Name concol -Value list-console-colors
Set-Alias -Name nf -Value powernerd -Option AllScope

if (Test-CommandExists bat) {
    Set-Alias -Name cat -Value Get-ContentPretty -Option AllScope
}
if (Test-CommandExists eza) {

    Function Get-ChildItemPretty {
        <#
    .SYNOPSIS
        Runs eza with a specific set of arguments. Plus some line breaks before and after the output.
        Alias: ls, ll, la, l
    #>


        [CmdletBinding()]
        param (
            [Parameter(ValueFromRemainingArguments = $true)]
            [string[]]$Arguments
        )
        if ($a -or $all) { $Arguments += '--all' }
        if ($l -or $long) { $Arguments += '--long' }

        $Arguments += ( '--group-directories-first', '--git-repos', '--git', '--hyperlink', '--follow-symlinks', '--no-quotes', '--icons' )
        Write-Host ' '
        eza @Arguments
        Write-Host ' '
        return
    }

    function l {
        [CmdletBinding()]
        $Arguments += ( '-a', '-l', '--no-permissions', '--no-filesize', '--no-time', '--no-user' )
        Get-ChildItemPretty @Arguments
        return
    }

    function lt {
        [CmdletBinding()]
        param (
            [int]$L = 1
        )
        $Arguments += ( '-n', '--tree', '-L', $L )
        Get-ChildItemPretty @Arguments
        return
    }

    function ll {
        $timestyle = '+󰨲 %m/%d/%y 󰅐 %H:%M'
        [CmdletBinding()]
        $Arguments += ( '-a', '-l', '--flags', '-h', '--time-style', $timestyle )
        Get-ChildItemPretty @Arguments

    }

    Set-Alias -Name ls -Value Get-ChildItemPretty -Option AllScope
}




if (Test-CommandExists yazi) {
    Set-Alias -Name d -Value yy
}
if (Test-CommandExists git) {
    Set-Alias -Name g -Value git
}
if (Test-CommandExists nvim) {
    Set-Alias -Name v -Value nvim
    Set-Alias -Name vi -Value nvim
}
if (Test-CommandExists fastfetch) {
    Set-Alias -Name fetch -Value Get-Fetch
}
if (Test-CommandExists lazygit) {
    Set-Alias -Name lg -Value lazygit.exe
}
