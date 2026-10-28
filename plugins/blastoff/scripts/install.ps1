#requires -Version 7.0
# Compatibility prefix bridge. For CurrentUser module/profile integration use
# the root install.ps1 / uninstall.ps1 with -WhatIf; see docs/POWERSHELL.md.
# Invoke with: ./scripts/install.ps1 install --prefix "$HOME/.local" --yes
. (Join-Path (Split-Path $PSScriptRoot -Parent) 'powershell/runtime.ps1')
try {
    $selection = Get-BlastoffRuntime
    $runtime = $selection.Executable; $prefix = @($selection.Prefix)
    $envelope = ConvertTo-BlastoffEnvelope -Arguments $args
    $PSNativeCommandUseErrorActionPreference = $false
    $ErrorActionPreference = 'Continue'
    & $runtime @prefix -I -B (Join-Path $PSScriptRoot 'install.py') --_powershell-argv-v1 $envelope
    exit $LASTEXITCODE
} catch [System.Management.Automation.PipelineStoppedException] {
    exit 130
} catch {
    [Console]::Error.WriteLine('blastoff lifecycle: runtime launch failed: '+$_.Exception.Message)
    exit 3
}
