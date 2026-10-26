# Native adapter; shared contract: less_style.py. Native Windows less has no
# termcap RGB override, so leave its stock colors intact.
function global:Update-DotsLessStyle {
    param([string] $Foreground, [string] $Background, [string] $Mode = 'auto', [string] $Enabled = '1')
    $reset = [string][char]27 + '[0m'
    $owned = $env:_DOTS_LESS_STYLE -and $env:LESS_TERMCAP_so -ceq $env:_DOTS_LESS_STYLE -and $env:LESS_TERMCAP_se -ceq $reset
    if (((Test-Path Env:LESS_TERMCAP_so) -or (Test-Path Env:LESS_TERMCAP_se)) -and -not $owned) {
        Remove-Item Env:_DOTS_LESS_STYLE -ErrorAction SilentlyContinue
        return
    }
    if ((Test-Path Env:LESS_TERMINFO_smso) -or (Test-Path Env:LESS_TERMINFO_rmso)) {
        if ($owned) { Remove-Item Env:LESS_TERMCAP_so, Env:LESS_TERMCAP_se -ErrorAction SilentlyContinue }
        Remove-Item Env:_DOTS_LESS_STYLE -ErrorAction SilentlyContinue
        return
    }
    $color = $Mode -eq 'always' -or ($Mode -eq 'auto' -and $env:TERM -and $env:TERM -ne 'dumb' -and -not $env:NO_COLOR)
    if ($IsWindows -or $env:OS -eq 'Windows_NT' -or $Enabled -ne '1' -or -not $color) {
        if ($owned) { Remove-Item Env:LESS_TERMCAP_so, Env:LESS_TERMCAP_se -ErrorAction SilentlyContinue }
        Remove-Item Env:_DOTS_LESS_STYLE -ErrorAction SilentlyContinue
        return
    }
    if ($Foreground -cnotmatch '^#[a-fA-F0-9]{6}$' -or $Background -cnotmatch '^#[a-fA-F0-9]{6}$') { return }
    $fg = (1,3,5 | ForEach-Object { [Convert]::ToInt32($Foreground.Substring($_,2),16) }) -join ';'
    $bg = (1,3,5 | ForEach-Object { [Convert]::ToInt32($Background.Substring($_,2),16) }) -join ';'
    $env:LESS_TERMCAP_so = [string][char]27 + '[0;38;2;' + $fg + ';48;2;' + $bg + 'm'
    $env:LESS_TERMCAP_se = $reset
    $env:_DOTS_LESS_STYLE = $env:LESS_TERMCAP_so
}
