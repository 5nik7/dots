# Host paths and ShouldProcess adapter; all ownership/write logic is shared Python.
# Dot-sourcing defines functions only. Never source a user's profile.
. (Join-Path (Split-Path $PSScriptRoot -Parent) 'powershell/runtime.ps1')
function Resolve-BlastoffModuleRoot {
    param([string]$ExplicitRoot)
    if ($ExplicitRoot) { return $ExplicitRoot }
    if ($IsWindows) {
        $documents = [Environment]::GetFolderPath('MyDocuments')
        if (-not $documents) { throw 'Cannot resolve redirected Documents; provide -ModuleRoot.' }
        $defaultRoot = Join-Path $documents 'PowerShell/Modules'
        $configRoot = Join-Path $documents 'PowerShell'
    } else {
        $dataRoot = if ($env:XDG_DATA_HOME) { $env:XDG_DATA_HOME } else { Join-Path $HOME '.local/share' }
        $defaultRoot = Join-Path $dataRoot 'powershell/Modules'
        $configBase = if ($env:XDG_CONFIG_HOME) { $env:XDG_CONFIG_HOME } else { Join-Path $HOME '.config' }
        $configRoot = Join-Path $configBase 'powershell'
    }
    $configFile = Join-Path $configRoot 'powershell.config.json'
    if ([IO.File]::Exists($configFile)) {
        $configuration = [IO.File]::ReadAllText($configFile) | ConvertFrom-Json -ErrorAction Stop
        if ($configuration.PSObject.Properties['PSModulePath'] -and $configuration.PSModulePath) {
            $paths = @(([Environment]::ExpandEnvironmentVariables([string]$configuration.PSModulePath)).Split([IO.Path]::PathSeparator) | Where-Object { $_ })
            if ($paths.Count -ne 1) { throw 'Ambiguous CurrentUser PSModulePath configuration; provide -ModuleRoot.' }
            return $paths[0]
        }
    }
    return $defaultRoot
}
function Write-BlastoffLifecycleText {
    param([string]$Text,[switch]$Accent)
    # Preserve ordinary Unicode and line breaks, never replay terminal controls.
    $safe=[regex]::Replace($Text,'[\p{Cc}\p{Cf}-[\n\t]]','?')
    $color=$Accent -and $null -eq [Environment]::GetEnvironmentVariable('NO_COLOR') -and -not [Console]::IsOutputRedirected -and $Host.UI.SupportsVirtualTerminal
    if ($color) { Write-Output (([char]27)+'[35m'+$safe+([char]27)+'[0m') }
    else { Write-Output $safe }
}
function Invoke-BlastoffLifecycle {
    [CmdletBinding(SupportsShouldProcess=$true,ConfirmImpact='Medium')]
    param([ValidateSet('install','uninstall')][string]$Action,
          [string]$ModuleRoot,[string]$ProfilePath,[switch]$NoProfile,[switch]$DryRun)
    try {
        $moduleDestination = Resolve-BlastoffModuleRoot $ModuleRoot
        if (-not [IO.Path]::IsPathFullyQualified($moduleDestination)) { throw '-ModuleRoot must be absolute.' }
        $profileDestination = if ($Action -eq 'install' -and -not $NoProfile) {
            if ($ProfilePath) { $ProfilePath } else { $PROFILE.CurrentUserAllHosts }
        } else { $null }
        if ($profileDestination -and -not [IO.Path]::IsPathFullyQualified($profileDestination)) { throw '-ProfilePath must be absolute.' }
        $knownProfiles = if ($ProfilePath) { @($ProfilePath) } else { @($PROFILE.CurrentUserAllHosts,$PROFILE.CurrentUserCurrentHost,$PROFILE.AllUsersAllHosts,$PROFILE.AllUsersCurrentHost) | Where-Object { $_ } | Select-Object -Unique }
        # Parse imports as data. The backend also detects foreign managed blocks
        # and rechecks all observed profile bytes before applying any change.
        $observedImports = @()
        if ($profileDestination) {
            foreach ($path in @($knownProfiles)+@($profileDestination) | Select-Object -Unique) {
                if (-not [IO.File]::Exists($path)) { continue }
                $tokens=$null; $parseErrors=$null
                $ast=[Management.Automation.Language.Parser]::ParseFile($path,[ref]$tokens,[ref]$parseErrors)
                $imports=$ast.FindAll({param($node) $node -is [Management.Automation.Language.CommandAst] -and ($node.GetCommandName() -split '\\')[-1] -in @('Import-Module','ipmo')},$true)
                foreach ($import in $imports) {
                    if ($import.Extent.Text -match '(?i)blastoff') {
                        $observedImports += @{path=$path;text=$import.Extent.Text}
                        Write-Verbose ('Existing Blastoff import to inspect: '+$path)
                    }
                }
            }
        }
        $context=@{host=$(if ($IsWindows) {'nt'} else {'posix'});module_root=$moduleDestination;profile_path=$profileDestination;known_profiles=@($knownProfiles);imports=@($observedImports)}
        $encoded=[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes((ConvertTo-Json -InputObject $context -Compress -Depth 6)))
        $selection=Get-BlastoffRuntime
        $runtime=$selection.Executable; $prefix=@($selection.Prefix)
        $backend=Join-Path $PSScriptRoot 'powershell_install.py'
        $PSNativeCommandUseErrorActionPreference=$false
        # Scoped to this function: pre-7.2 redirected native stderr must not
        # become a terminating PowerShell error instead of the native status.
        $ErrorActionPreference='Continue'
        $result=& $runtime @prefix -I -B $backend $Action --context $encoded --plan-json
        if ($LASTEXITCODE -ne 0) { $global:LASTEXITCODE=$LASTEXITCODE; return }
        $plan=($result -join "`n") | ConvertFrom-Json -ErrorAction Stop
        Write-BlastoffLifecycleText -Accent ('Blastoff '+$Action+' '+$plan.version+'; current: '+$plan.current)
        Write-BlastoffLifecycleText ('SYSTEM: '+$plan.platform.label)
        Write-Verbose (Write-BlastoffLifecycleText ('Detection: '+($plan.platform.evidence -join '; ')+'; Python executable: '+$plan.platform.python))
        Write-BlastoffLifecycleText ('Module destination: '+$plan.destination)
        if ($WhatIfPreference -or $DryRun -or $VerbosePreference -ne 'SilentlyContinue') {
            foreach ($row in $plan.actions) { Write-BlastoffLifecycleText ('  '+$row[0]+': '+$row[1]) }
        } else { Write-BlastoffLifecycleText ((@($plan.actions).Count).ToString()+' owned file/profile actions; use -WhatIf for exact destinations.') }
        foreach ($profile in $plan.profiles) { Write-BlastoffLifecycleText $profile.diff }
        foreach ($note in $plan.notes) { Write-BlastoffLifecycleText $note }
        Write-Verbose ('Ownership and profile fingerprints inspected; plan '+$plan.token)
        if ($DryRun) { Write-BlastoffLifecycleText 'Dry run: no files changed.'; $global:LASTEXITCODE=0; return }
        if ($PSCmdlet.ShouldProcess($plan.destination,('Apply verified Blastoff '+$Action+' plan'))) {
            & $runtime @prefix -I -B $backend $Action --context $encoded --apply-token $plan.token
            $global:LASTEXITCODE=$LASTEXITCODE
        } else { $global:LASTEXITCODE=0 }
    } catch [System.Management.Automation.PipelineStoppedException] {
        $global:LASTEXITCODE=130
    } catch {
        $global:LASTEXITCODE=3
        [Console]::Error.WriteLine('blastoff lifecycle: '+$_.Exception.Message)
    }
}
