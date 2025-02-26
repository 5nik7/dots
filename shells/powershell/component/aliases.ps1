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

    # eza -a -l --group-directories-first --git-repos --git --icons --time-style relative --no-permissions --no-filesize --no-time --no-user --hyperlink --follow-symlinks --no-quotes $Path
    # eza -a -l --group-directories-first --git-repos --git --icons --time-style relative --no-permissions --no-filesize --no-time --no-user --hyperlink --follow-symlinks --no-quotes $Path

    Function Get-ChildItemPretty {
        [CmdletBinding()]
        param (
            [Parameter(Mandatory = $false, Position = 0)]
            [string]$Path = $PWD,
            [switch]$minimal = $false,
            [switch]$more = $false,
            [switch]$tree = $false,
            [switch]$1 = $false,
            [int]$level = 1

        )
        if (-not $Path) {
            $Path = $PWD
        }
        if ($more) {
            Write-Host ' '
            eza -a -l --group-directories-first --git-repos --git --icons --hyperlink --follow-symlinks --no-quotes --modified --flags -h --time-style '+  󰨲%m.%d.%y 󰅐 %H:%M ' $Path
            Write-Host ' '
        }
        elseif ($tree) {
            Write-Host ' '
            eza --icons --git-repos --git -n -L $level --time-style=relative --hyperlink --follow-symlinks --no-quotes --tree $Path
            Write-Host ' '

        }
        elseif ($minimal) {
            Write-Host ' '
            eza -a -l --group-directories-first --git-repos --git --icons --time-style relative --no-permissions --no-filesize --no-time --no-user --hyperlink --follow-symlinks --no-quotes $Path
            Write-Host ' '
        }
        else {
            Write-Host ' '
            eza $Path
            Write-Host ' '
        }
    }
    function Get-ChildItemPrettyTree {
        <#
    .SYNOPSIS
        Runs eza with a specific set of arguments. Plus some line breaks before and after the output.
        Alias: ls, ll, la, l
    #>
        [CmdletBinding()]
        param (
            [Parameter(Mandatory = $false, Position = 0)]
            [string]$Path,
            [int]$level = 1
        )
        if (-not $Path) {
            $Path = $PWD
        }
        eza --icons --git-repos --git -n -L $level --time-style=relative --hyperlink --follow-symlinks --no-quotes --tree $Path
        linebreak
    }
    function ll {
        Get-ChildItemPretty -more
    }

    function lt {
        Get-ChildItemPretty -tree
    }

    function l {
        Get-ChildItemPretty -minimal
    }

    Set-Alias -Name ls -Value Get-ChildItem -Option AllScope
    Set-Alias -Name lspr -Value Get-ChildItemPretty -Option AllScope


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
