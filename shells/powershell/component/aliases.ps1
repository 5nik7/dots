function q {
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
            [switch]$a,
            [switch]$l,
            [switch]$time,
            [Parameter(ValueFromRemainingArguments = $true)]
            [string[]]$Arguments
        )
        $timestyle = '+󰨲 %m/%d/%y 󰅐 %H:%M'
        if ($a) { $Arguments += '-a' }
        if ($l) { $Arguments += '-l' }
        if ($time) { $Arguments += '--time-style', $timestyle }

        $Arguments += ( '--group-directories-first', '--git-repos', '--git', '--hyperlink', '--follow-symlinks', '--no-quotes', '--icons' )
        Write-Host ' '
        eza @Arguments
        Write-Host ' '
    }

    function l {
        [CmdletBinding()]
        param (
            [Parameter(ValueFromRemainingArguments = $true)]
            [string[]]$Arguments
        )
        $Arguments += ( '-a', '-l', '--no-permissions', '--no-filesize', '--no-time', '--no-user' )
        Get-ChildItemPretty @Arguments
    }

    function lt {
        [CmdletBinding()]
        param (
            [Parameter(Position = 0)]
            [int]$L = 1,
            [Parameter(ValueFromRemainingArguments = $true)]
            [string[]]$Arguments
        )
        $Arguments += ( '-n', '--tree', '-L', $L )
        Get-ChildItemPretty @Arguments
    }

    function ll {
        [CmdletBinding()]
        param (
            [Parameter(ValueFromRemainingArguments = $true)]
            [string[]]$Arguments
        )
        $Arguments += ( '-a', '-l', '--flags', '-h' )
        Get-ChildItemPretty -time @Arguments
    }

    Set-Alias -Name ls -Value Get-ChildItemPretty
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
