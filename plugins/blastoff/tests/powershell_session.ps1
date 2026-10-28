#requires -Version 7.0
# Run in a fresh pwsh -NoProfile process. No live config or profile writes.
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
$manifest=Join-Path $root 'powershell/blastoff.psd1'
$oldPython=$env:BLASTOFF_PYTHON
try {
    # Selection-only mocks exercise rejection without launching any interpreter.
    & {
        . (Join-Path $root 'powershell/runtime.ps1')
        $env:BLASTOFF_PYTHON=''
        function Get-Command {
            param($Name,$CommandType,$ErrorAction)
            if ($Name -eq 'py') { return [pscustomobject]@{Source='fake.cmd'} }
            if ($Name -eq 'python3') { return [pscustomobject]@{Source='fake.bat'} }
            if ($Name -eq 'python') { return [pscustomobject]@{Source='native-python.exe'} }
            if ($Name -eq 'explicit-batch') { return [pscustomobject]@{Source='fake.cmd'} }
        }
        $selection=Get-BlastoffRuntime
        if ($selection.Executable -cne 'native-python.exe') { throw 'Automatic batch candidate was accepted' }
        $env:BLASTOFF_PYTHON='explicit-batch'
        $rejected=$false
        try { $null=Get-BlastoffRuntime } catch { $rejected=$true }
        if (-not $rejected) { throw 'Explicit batch runtime was accepted' }
    }
    $env:BLASTOFF_PYTHON='blastoff-must-not-run-during-import'
    $global:LASTEXITCODE=73
    Import-Module $manifest -Force
    foreach ($line in @('blastoff --','blastoff pick ','blastoff pick --fancy ','blastoff module show --','blastoff backup delete --pick --')) {
        $matches=@((TabExpansion2 $line $line.Length).CompletionMatches)
        if (-not $matches.Count) { throw "No fresh-session completion: $line" }
    }
    if ($LASTEXITCODE -ne 73) { throw 'Import or static completion launched a process' }
    Remove-Module blastoff
    Import-Module $manifest -Force
    $line='blastoff pick f'
    if ('fzf' -notin @((TabExpansion2 $line $line.Length).CompletionMatches.CompletionText)) { throw 'Reimport failed' }
    Register-ArgumentCompleter -Native -CommandName blastoff -ScriptBlock { 'other-tool-marker' }
    Remove-Module blastoff
    $line='blastoff oth'
    if ('other-tool-marker' -notin @((TabExpansion2 $line $line.Length).CompletionMatches.CompletionText)) { throw 'Removal overwrote another completer' }
    'Fresh-session import/completion passed on '+$PSVersionTable.OS+' / '+$PSVersionTable.PSVersion
} finally { $env:BLASTOFF_PYTHON=$oldPython }
