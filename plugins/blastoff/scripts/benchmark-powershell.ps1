#requires -Version 7.0
<# Measure import, process startup, first command and completion separately.
Run in a fresh pwsh -NoProfile process. Only a new temporary fixture is written.
#>
param([ValidateRange(5,10000)][int]$Samples=60)
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
$manifest=Join-Path $root 'powershell/blastoff.psd1'
$pwsh=Join-Path $PSHOME $(if ($IsWindows) {'pwsh.exe'} else {'pwsh'})
$temporary=Join-Path ([IO.Path]::GetTempPath()) ('blastoff ps benchmark '+[guid]::NewGuid().ToString('N'))
$names=@('BLASTOFF_HOME','STARSHIP_CONFIG','NO_COLOR','STARSHIP_CACHE')
$previous=@{};foreach ($key in $names) {$previous[$key]=[Environment]::GetEnvironmentVariable($key,'Process')}
$results=[ordered]@{}
function Measure-BlastoffCase($name,[scriptblock]$body,[scriptblock]$setup={}) {
    $values=[Collections.Generic.List[double]]::new()
    for ($i=0;$i -lt ($Samples+5);$i++) {
        & $setup
        $watch=[Diagnostics.Stopwatch]::StartNew(); & $body | Out-Null; $watch.Stop()
        if ($i -ge 5) {$values.Add($watch.Elapsed.TotalMilliseconds)}
    }
    $sorted=@($values | Sort-Object)
    $results[$name]=@{p50_ms=$sorted[[int][Math]::Floor($sorted.Count/2)];p95_ms=$sorted[[int][Math]::Ceiling($sorted.Count*0.95)-1]}
}
try {
    New-Item -ItemType Directory -Path $temporary | Out-Null
    $env:BLASTOFF_HOME=Join-Path $temporary 'store';$env:STARSHIP_CONFIG=Join-Path $temporary 'active.toml'
    $env:STARSHIP_CACHE=Join-Path $temporary 'starship-cache';$env:NO_COLOR='1'
    Measure-BlastoffCase 'module-import' { Import-Module $manifest -Force } { Remove-Module blastoff -ErrorAction SilentlyContinue }
    Measure-BlastoffCase 'fresh-process-no-profile' { & $pwsh -NoLogo -NoProfile -Command 'exit 0' }
    $profile=Join-Path $temporary 'minimal-profile.ps1'
    [IO.File]::WriteAllText($profile,('Import-Module '+"'"+$manifest.Replace("'","''")+"'"),[Text.UTF8Encoding]::new($false))
    Measure-BlastoffCase 'fresh-process-minimal-profile-import' { & $pwsh -NoLogo -NoProfile -File $profile }
    Measure-BlastoffCase 'first-command-after-import' { blastoff --version; if ($LASTEXITCODE -ne 0) {throw 'Command failed'} } { Remove-Module blastoff -ErrorAction SilentlyContinue;Import-Module $manifest }
    Measure-BlastoffCase 'static-completion' { $line='blastoff pick --'; TabExpansion2 $line $line.Length }
    $themes=Join-Path $env:BLASTOFF_HOME 'themes';New-Item -ItemType Directory -Path $themes -Force | Out-Null
    foreach ($size in @(0,1000,10000)) {
        if ($size) {for ($i=$(if ($size -eq 1000){0}else{1000});$i -lt $size;$i++) {[IO.File]::WriteAllText((Join-Path $themes "theme$i.toml"),'x=1')}}
        Measure-BlastoffCase "dynamic-cold-$size" { $line='blastoff theme apply th'; TabExpansion2 $line $line.Length } {Remove-Module blastoff;Import-Module $manifest}
        Measure-BlastoffCase "dynamic-warm-$size" { $line='blastoff theme apply th'; TabExpansion2 $line $line.Length }
    }
    [ordered]@{host=$PSVersionTable.OS;platform=$PSVersionTable.Platform;powershell=[string]$PSVersionTable.PSVersion;samples=$Samples;warmups=5;results=$results} | ConvertTo-Json -Depth 6
} finally {
    foreach ($key in $names) {[Environment]::SetEnvironmentVariable($key,$previous[$key],'Process')}
    Remove-Module blastoff -ErrorAction SilentlyContinue
    if (Test-Path -LiteralPath $temporary) {Remove-Item -LiteralPath $temporary -Recurse -Force}
}
