#requires -Version 7.0
# Native adapter acceptance. Source must have reviewed, current CHECKSUMS.json.
param([string]$PriorSource)
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
$temporary=Join-Path ([IO.Path]::GetTempPath()) ('blastoff lifecycle ü '+[guid]::NewGuid().ToString('N'))
$moduleRoot=Join-Path $temporary 'Modules'
$profile=Join-Path $temporary "profile ' ü.ps1"
$pwsh=Join-Path $PSHOME $(if ($IsWindows) {'pwsh.exe'} else {'pwsh'})
$version=(Get-Content -LiteralPath (Join-Path $root 'VERSION') -Raw).Trim()
$source=Join-Path $temporary 'source'
$names=@('BLASTOFF_HOME','STARSHIP_CONFIG','HOME','USERPROFILE','XDG_CONFIG_HOME','XDG_CACHE_HOME','STARSHIP_CACHE','BLASTOFF_PYTHON')
$previous=@{}; foreach ($key in $names) { $previous[$key]=[Environment]::GetEnvironmentVariable($key,'Process') }
function Snapshot {
    if (-not (Test-Path -LiteralPath $temporary)) { return '' }
    (@(Get-ChildItem -LiteralPath $temporary -Recurse -Force | ForEach-Object {
        $_.FullName+'|'+$_.LastWriteTimeUtc.Ticks+'|'+$(if (-not $_.PSIsContainer) {(Get-FileHash -LiteralPath $_.FullName).Hash})
    }) -join "`n")
}
try {
    . (Join-Path $root 'powershell/runtime.ps1')
    $selection=Get-BlastoffRuntime
    $runtime=$selection.Executable; $runtimeArgs=@($selection.Prefix)
    New-Item -ItemType Directory -Path $temporary | Out-Null
    $env:HOME=Join-Path $temporary 'home'; $env:USERPROFILE=$env:HOME
    $env:BLASTOFF_HOME=Join-Path $temporary 'user data'
    $env:STARSHIP_CONFIG=Join-Path $temporary 'starship.toml'
    $env:XDG_CONFIG_HOME=Join-Path $temporary 'config'; $env:XDG_CACHE_HOME=Join-Path $temporary 'cache'
    $env:STARSHIP_CACHE=Join-Path $temporary 'starship-cache'
    $clone=Join-Path $temporary 'copy_source.py'
    [IO.File]::WriteAllText($clone,@'
import pathlib,runpy,shutil,sys
root,destination=map(pathlib.Path,sys.argv[1:])
v=runpy.run_path(str(root/'scripts/verify.py'))
v['verify'](root)
for source in [*v['source_files'](root),root/'CHECKSUMS.json']:
    target=destination/source.relative_to(root)
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(source,target)
'@)
    & $runtime @runtimeArgs -I -B $clone $root $source
    if ($LASTEXITCODE -ne 0) { throw 'Disposable source copy failed' }
    [IO.File]::WriteAllText($env:STARSHIP_CONFIG,"[directory]`nstyle='purple'`n")
    New-Item -ItemType Directory -Path (Join-Path $env:BLASTOFF_HOME 'themes') -Force | Out-Null
    $theme=Join-Path $env:BLASTOFF_HOME 'themes/keep.toml'
    [IO.File]::WriteAllText($theme,"x=1`n")
    $configHash=(Get-FileHash -LiteralPath $env:STARSHIP_CONFIG).Hash
    $themeHash=(Get-FileHash -LiteralPath $theme).Hash
    if ($PriorSource) {
        $priorVersion=(Get-Content -LiteralPath (Join-Path $PriorSource 'VERSION') -Raw).Trim()
        if ($priorVersion -ne '0.1.11' -or $version -ne '0.1.12') { throw 'Expected genuine 0.1.11 to 0.1.12 sources' }
        & $pwsh -NoProfile -File (Join-Path $PriorSource 'install.ps1') -ModuleRoot $moduleRoot -ProfilePath $profile
        if ($LASTEXITCODE -ne 0) { throw 'Prior version install failed' }
        $oldCore=Join-Path $moduleRoot "blastoff/$priorVersion/lib/blastoff.py"
        $oldHash=(Get-FileHash -LiteralPath $oldCore).Hash
    }
    $before=Snapshot
    & $pwsh -NoProfile -File (Join-Path $source 'install.ps1') -ModuleRoot $moduleRoot -ProfilePath $profile -WhatIf
    if ($LASTEXITCODE -ne 0 -or (Snapshot) -cne $before) { throw 'WhatIf changed files or failed' }
    & $pwsh -NoProfile -File (Join-Path $source 'install.ps1') -ModuleRoot $moduleRoot -ProfilePath $profile
    if ($LASTEXITCODE -ne 0) { throw 'Install failed' }
    $installed=Snapshot
    & $pwsh -NoProfile -File (Join-Path $source 'install.ps1') -ModuleRoot $moduleRoot -ProfilePath $profile
    if ($LASTEXITCODE -ne 0 -or (Snapshot) -cne $installed) { throw 'Repeat install was not idempotent' }
    if ($PriorSource -and (Get-FileHash -LiteralPath $oldCore).Hash -cne $oldHash) { throw 'Upgrade changed old payload' }
    $versionRoot=Join-Path $moduleRoot "blastoff/$version"
    $missing=Join-Path $versionRoot 'lib/preview.py'
    $missingHash=(Get-FileHash -LiteralPath $missing).Hash
    Remove-Item -LiteralPath $missing
    & $pwsh -NoProfile -File (Join-Path $source 'install.ps1') -ModuleRoot $moduleRoot -ProfilePath $profile
    if ($LASTEXITCODE -ne 0 -or (Get-FileHash -LiteralPath $missing).Hash -cne $missingHash) { throw 'Missing support repair failed' }
    Move-Item -LiteralPath $source -Destination (Join-Path $temporary 'relocated source')
    $manifest=Join-Path $versionRoot 'blastoff.psd1'
    $command="Import-Module '"+$manifest.Replace("'","''")+"'; blastoff --version; exit `$LASTEXITCODE"
    $encoded=[Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($command))
    $reported=& $pwsh -NoProfile -EncodedCommand $encoded
    if ($LASTEXITCODE -ne 0 -or $reported -cne "blastoff $version") { throw 'Installed module depends on source' }
    $modified=Join-Path $versionRoot 'README.md'
    [IO.File]::AppendAllText($modified,"`n# user edit`n")
    $installed=Snapshot
    & $pwsh -NoProfile -File (Join-Path $versionRoot 'uninstall.ps1') -ModuleRoot $moduleRoot -WhatIf
    if ($LASTEXITCODE -ne 0 -or (Snapshot) -cne $installed) { throw 'Uninstall WhatIf changed files' }
    & $pwsh -NoProfile -File (Join-Path $versionRoot 'uninstall.ps1') -ModuleRoot $moduleRoot
    if ($LASTEXITCODE -ne 0) { throw 'Uninstall failed' }
    if (-not (Test-Path -LiteralPath $modified)) { throw 'Uninstall removed a modified owned file' }
    if ((Get-FileHash -LiteralPath $env:STARSHIP_CONFIG).Hash -cne $configHash -or
        (Get-FileHash -LiteralPath $theme).Hash -cne $themeHash) { throw 'Lifecycle changed application data' }
    'Native lifecycle adapter passed on '+$PSVersionTable.OS+' / '+$PSVersionTable.PSVersion
} finally {
    foreach ($key in $names) { [Environment]::SetEnvironmentVariable($key,$previous[$key],'Process') }
    # Only this freshly generated temporary fixture; never a discovered user root.
    if (Test-Path -LiteralPath $temporary) { Remove-Item -LiteralPath $temporary -Recurse -Force }
}
