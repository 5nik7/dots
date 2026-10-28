#requires -Version 7.0
# Run in a disposable native Windows process: pwsh -NoProfile -File ./tests/parity.ps1
# Record the actual host/version. Linux/WSL runs never certify native Windows.
param([switch]$KeepSandbox,[switch]$AllowNonWindows)
$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $false # Expected nonzero statuses are assertions.
if (-not $IsWindows -and -not $AllowNonWindows) { throw 'Use -AllowNonWindows for a separately labelled Linux/WSL run; it is not Windows evidence.' }
$root = Split-Path $PSScriptRoot -Parent
$temporaryRoot = Join-Path ([IO.Path]::GetTempPath()) ('blastoff parity ü ' + [Guid]::NewGuid().ToString('N'))
$names = @('BLASTOFF_HOME','STARSHIP_CONFIG','BLASTOFF_PYTHON','NO_COLOR',
           'HOME','USERPROFILE','XDG_CONFIG_HOME','XDG_CACHE_HOME','STARSHIP_CACHE')
$previous = @{}
foreach ($key in $names) { $previous[$key] = [Environment]::GetEnvironmentVariable($key, 'Process') }
$success = $false
$utf8 = [Text.UTF8Encoding]::new($false)
$argumentMode = Get-Variable PSNativeCommandArgumentPassing -Scope Global -ErrorAction SilentlyContinue
$originalArgumentMode = if ($argumentMode) { $argumentMode.Value } else { $null }
# A separate data-only launcher feeds the core exact arguments. The baseline
# must not lose empty strings/quotes in Legacy mode or reuse Blastoff's decoder.
function Invoke-Core {
    param([AllowEmptyCollection()][object[]]$Arguments)
    $encoded=[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes((ConvertTo-Json -Compress -Depth 5 -InputObject @{
        core=(Join-Path $root 'lib/blastoff.py');argv=[string[]]$Arguments
    })))
    $ErrorActionPreference='Continue'
    & $python -I -B $baselineLauncher $encoded
    $global:LASTEXITCODE=$LASTEXITCODE
}
try {
    New-Item -ItemType Directory -Path $temporaryRoot | Out-Null
    $baselineLauncher=Join-Path $temporaryRoot 'independent baseline.py'
    [IO.File]::WriteAllText($baselineLauncher, 'import base64,json,runpy,sys; d=json.loads(base64.b64decode(sys.argv[1])); sys.argv=[d["core"],*d["argv"]]; runpy.run_path(d["core"],run_name="__main__")', $utf8)
    # Resolve Python before changing its home. Do not edit PATH.
    . (Join-Path $root 'powershell/runtime.ps1')
    $selection=Get-BlastoffRuntime
    $runtime=$selection.Executable; $prefixArgs=@($selection.Prefix)
    $resolved = & $runtime @prefixArgs -c 'import sys; assert sys.version_info >= (3,11); print(sys.executable)'
    if ($LASTEXITCODE -ne 0 -or -not $resolved) { throw 'A host-native Python 3.11+ executable is required.' }
    $python = ([string]$resolved).Trim()
    $platform = & $python -c 'import os; print(os.name)'
    if ($LASTEXITCODE -ne 0 -or $platform -ne $(if ($IsWindows) { 'nt' } else { 'posix' })) { throw 'Python must match the PowerShell host platform.' }
    $env:HOME = $temporaryRoot
    $env:USERPROFILE = $temporaryRoot
    $env:BLASTOFF_HOME = Join-Path $temporaryRoot 'store with spaces ü'
    $env:STARSHIP_CONFIG = Join-Path $temporaryRoot 'active config ü/starship.toml'
    $env:XDG_CONFIG_HOME = Join-Path $temporaryRoot 'xdg'
    $env:XDG_CACHE_HOME = Join-Path $temporaryRoot 'cache'
    $env:STARSHIP_CACHE = Join-Path $temporaryRoot 'starship-cache'
    $env:NO_COLOR = '1'
    Write-Output "PowerShell $($PSVersionTable.PSVersion); Python $python; argument mode: $(Get-Variable PSNativeCommandArgumentPassing -ValueOnly -ErrorAction SilentlyContinue)"

    # An argv echo companion isolates the actual module's native-call boundary.
    # Comparing two equally broken native calls is not proof of literal forwarding.
    $probeRoot = Join-Path $temporaryRoot 'argv probe'
    New-Item -ItemType Directory -Path (Join-Path $probeRoot 'lib'),(Join-Path $probeRoot 'powershell'),(Join-Path $probeRoot 'scripts') | Out-Null
    $probeModule = Join-Path $probeRoot 'powershell/blastoff.psm1'
    Copy-Item -LiteralPath (Join-Path $root 'powershell/blastoff.psm1') -Destination $probeModule
    Copy-Item -LiteralPath (Join-Path $root 'powershell/runtime.ps1') -Destination (Join-Path $probeRoot 'powershell/runtime.ps1')
    # Independent probe decoder: assert original argv, not equality between two
    # frontend calls that might both corrupt the same argument.
    [IO.File]::WriteAllText((Join-Path $probeRoot 'lib/blastoff.py'), 'import base64,json,sys; assert sys.argv[1]=="--_powershell-argv-v1"; print(json.dumps(json.loads(base64.b64decode(sys.argv[2]))["argv"]))', $utf8)
    $probeInstaller=Join-Path $probeRoot 'scripts/install.ps1'
    Copy-Item -LiteralPath (Join-Path $root 'scripts/install.ps1') -Destination $probeInstaller
    Copy-Item -LiteralPath (Join-Path $probeRoot 'lib/blastoff.py') -Destination (Join-Path $probeRoot 'scripts/install.py')
    $env:BLASTOFF_PYTHON = $python
    $probe = Import-Module $probeModule -Force -PassThru
    $literal = @('', 'space value', 'Unicode ü λ', 'quote"inside', 'trailing\', '-HELP')
    $modes=if ($argumentMode) {@('Legacy','Standard','Windows')} else {@('default')}
    foreach ($mode in $modes) {
        if ($argumentMode) { $global:PSNativeCommandArgumentPassing=$mode }
        foreach ($frontend in @('module','legacy')) {
            $echoed = @(if ($frontend -eq 'module') { Invoke-Blastoff @literal | ConvertFrom-Json }
                       else { & $probeInstaller @literal | ConvertFrom-Json })
            if ($LASTEXITCODE -ne 0 -or $echoed.Count -ne $literal.Count) { throw "Literal argv count/exit mismatch in $frontend / $mode mode." }
            for ($i = 0; $i -lt $literal.Count; $i++) {
                if ($echoed[$i] -cne $literal[$i]) { throw "Literal argv mismatch at index $i in $frontend / $mode mode" }
            }
        }
    }
    if ($argumentMode) { $global:PSNativeCommandArgumentPassing=$originalArgumentMode }
    Remove-Module -ModuleInfo $probe -Force

    # Import must not start Python or depend on a preexisting active config.
    $env:BLASTOFF_PYTHON = Join-Path $temporaryRoot 'not-present-python.exe'
    $global:LASTEXITCODE = 61
    Import-Module (Join-Path $root 'powershell/blastoff.psd1') -Force
    if ($LASTEXITCODE -ne 61 -or (Test-Path -LiteralPath $env:BLASTOFF_HOME) -or
        (Test-Path -LiteralPath $env:STARSHIP_CONFIG)) { throw 'Module import had runtime/filesystem side effects.' }
    # Exercise the actual missing-runtime boundary, not just import isolation.
    $launchError=Join-Path $temporaryRoot 'missing-runtime.err'
    $launchOutput=(blastoff --version 2> $launchError | Out-String)
    if ($LASTEXITCODE -ne 3 -or $launchOutput.Length -ne 0) { throw 'Missing runtime status/stdout mismatch' }
    $env:BLASTOFF_PYTHON = $python
    $missing = Join-Path $temporaryRoot "missing path ü's.toml"
    $cases = @(
        @{ A=@('--version'); C=0 }, @{ A=@('--help'); C=0 },
        @{ A=@(); C=0 }, @{ A=@('-h'); C=0 },
        @{ A=@('--color','never'); C=0 }, @{ A=@('--verbose','--dry-run'); C=0 },
        @{ A=@('--json'); C=0 }, @{ A=@('--json','--help'); C=0 },
        @{ A=@('--list','--json'); C=0 }, @{ A=@('current','--json'); C=0 },
        @{ A=@('doctor','--json'); C=0 }, @{ A=@('module','list','--json'); C=0 },
        @{ A=@('--json','theme','apply'); C=2 },
        @{ A=@('theme','save','../unsafe','--json'); C=2 },
        @{ A=@('theme','save','','--json'); C=2 },
        @{ A=@('theme','import',$missing,'missing','--json'); C=1 },
        @{ A=@('-help'); C=0 }, @{ A=@('-list','--json'); C=0 },
        @{ A=@('-theme','--json'); C=0 },
        @{ A=@('theme','save','--json'); C=2 },
        @{ A=@('backup','delete','--all','--dry-run','--json'); C=0 },
        @{ A=@('backup','delete','yes','--json'); C=2 },
        @{ A=@('module','show','--json'); C=2 },
        @{ A=@('pick','--fancy','ascii','--dry-run','--json'); C=0 },
        @{ A=@('pick','--fzf','--dry-run','--json'); C=0 },
        @{ A=@('backup','list'); C=0 },
        @{ A=@('--json','backup','list'); C=0 },
        @{ A=@('pick','fancy','--fzf'); C=2 }
    )
    $rootHelp = (Invoke-Core -Arguments @('--help') | Out-String)
    if ($LASTEXITCODE -ne 0) { throw 'Root help failed' }
    $passed = 0
    foreach ($case in $cases) {
        $invocation = $case.A
        $mapped = @($invocation | ForEach-Object {
            if ($_ -ceq '-help') { '--help' } elseif ($_ -ceq '-list') { '--list' }
            elseif ($_ -ceq '-theme') { '--theme' } else { $_ }
        })
        $baselineError = Join-Path $temporaryRoot 'baseline.err'
        $moduleError = Join-Path $temporaryRoot 'module.err'
        $baseline = (Invoke-Core -Arguments $mapped 2> $baselineError | Out-String)
        $baselineCode = $LASTEXITCODE
        $actual = (blastoff @invocation 2> $moduleError | Out-String)
        $actualCode = $LASTEXITCODE
        $errorText = [IO.File]::ReadAllText($moduleError)
        if ($baselineCode -ne $case.C -or $actualCode -ne $case.C -or $baseline -cne $actual -or
            [IO.File]::ReadAllText($baselineError) -cne $errorText) {
            throw ('Parity mismatch: ' + ($invocation -join ' ') + "; expected=$($case.C), core=$baselineCode, module=$actualCode; stderr=$errorText")
        }
        if ($case.C -ne 0 -and ($actual.Trim().Length -ne 0 -or -not $errorText.Trim() -or
            ('--json' -in $invocation -and ($errorText | ConvertFrom-Json).code -ne $case.C))) {
            throw 'Error stream/JSON contract mismatch'
        }
        if (($invocation.Count -eq 0 -or ($invocation -join ' ') -in @('-h','--help','--color never','--verbose --dry-run')) -and
            ($actual -cne $rootHelp -or $errorText.Length -ne 0)) {
            throw 'Implicit/explicit root help differs'
        }
        $passed++
    }
    if (Test-Path -LiteralPath $env:BLASTOFF_HOME) { throw 'Read-only cases created storage.' }
    $themeDir = Join-Path $env:BLASTOFF_HOME 'themes'
    New-Item -ItemType Directory -Path $themeDir -Force | Out-Null
    [IO.File]::WriteAllText((Join-Path $themeDir 'purple.toml'), "[directory]`nstyle = 'purple'`n", $utf8)
    blastoff -theme purple --json | Out-Null
    if ($LASTEXITCODE -ne 0 -or !(Test-Path -LiteralPath $env:STARSHIP_CONFIG)) { throw 'Legacy theme alias failed' }
    $originalActive = [IO.File]::ReadAllText($env:STARSHIP_CONFIG)
    $listNoColor = $env:NO_COLOR
    try {
        foreach ($modified in @($false,$true)) {
            if ($modified) { [IO.File]::WriteAllText($env:STARSHIP_CONFIG, $originalActive+"# edited`n", $utf8) }
            foreach ($flags in @(@('--color','never'),@('--color','always'),@('--json'))) {
                [Environment]::SetEnvironmentVariable('NO_COLOR', $null, 'Process')
                $baseline = (Invoke-Core -Arguments (@('list')+$flags) 2> (Join-Path $temporaryRoot 'list-core.err') | Out-String)
                $baselineCode = $LASTEXITCODE
                $actual = (blastoff list @flags 2> (Join-Path $temporaryRoot 'list-module.err') | Out-String)
                if ($baselineCode -ne 0 -or $LASTEXITCODE -ne 0 -or $actual -cne $baseline) { throw 'Theme-list output parity mismatch' }
                if ([IO.File]::ReadAllText((Join-Path $temporaryRoot 'list-core.err')) -cne [IO.File]::ReadAllText((Join-Path $temporaryRoot 'list-module.err'))) { throw 'Theme-list diagnostic parity mismatch' }
                if ($flags[0] -ne '--json') {
                    $marker = if ($modified) { '[last loaded; modified]' } else { '[current]' }
                    if (-not $actual.Contains($marker)) { throw 'Theme-list origin marker missing' }
                }
            }
        }
    } finally {
        $env:NO_COLOR = $listNoColor
        [IO.File]::WriteAllText($env:STARSHIP_CONFIG, $originalActive, $utf8)
    }
    blastoff module save directory compact --json | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Module save failed' }
    blastoff module load compact --json | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Module load failed' }
    blastoff module show compact --json | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Module show failed' }
    $raw=(blastoff module show compact | Out-String)
    $rawStatus=$LASTEXITCODE
    $expectedRaw=(Invoke-Core -Arguments @('module','show','compact') | Out-String)
    if ($rawStatus -ne 0 -or $LASTEXITCODE -ne 0 -or $raw -cne $expectedRaw) { throw 'Redirected raw TOML parity mismatch' }
    $backup = blastoff backup create --json | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0) { throw 'Backup create failed' }
    $savedColumns=$env:COLUMNS
    try {
        foreach ($columns in @('80','24')) {
            $env:COLUMNS=$columns
            foreach ($flags in @(@('--color','never'),@('--json'))) {
                $baseline=(Invoke-Core -Arguments (@('backup','list')+$flags) | Out-String)
                $baselineCode=$LASTEXITCODE
                $actual=(blastoff backup list @flags | Out-String)
                if ($baselineCode -ne 0 -or $LASTEXITCODE -ne 0 -or $actual -cne $baseline) { throw 'Populated backup-list parity mismatch' }
                if ($flags[0] -eq '--color' -and $columns -eq '24' -and $actual -notmatch '(?m)^  Size: ') { throw 'Narrow backup size row missing' }
            }
        }
    } finally { $env:COLUMNS=$savedColumns }
    blastoff backup delete $backup.backup --yes --json | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Backup delete failed' }
    # Run the same mutation sequence in independent roots. Compare the active
    # bytes and stored payloads, not generated backup IDs or path-associated hashes.
    $scenarioResults=@()
    foreach ($frontend in @('core','module')) {
        $scenario=Join-Path $temporaryRoot ('scenario '+$frontend)
        New-Item -ItemType Directory -Path $scenario | Out-Null
        $env:BLASTOFF_HOME=Join-Path $scenario 'store'
        $env:STARSHIP_CONFIG=Join-Path $scenario 'active.toml'
        $inputFile=Join-Path $scenario "source ' ü.toml"
        [IO.File]::WriteAllText($inputFile,"[directory]`nstyle = 'purple'`n[character]`nsuccess_symbol = 'ok'`n",$utf8)
        $commands=@(
            @('theme','import',$inputFile,'original','--json'),
            @('theme','apply','local:original','--json'),
            @('theme','save','saved','--json'),
            @('theme','copy','local:saved','copied','--json'),
            @('module','save','directory','compact','--json'),
            @('module','load','compact','--json'),
            @('theme','delete','copied','--json')
        )
        foreach ($command in $commands) {
            $output=if ($frontend -eq 'core') { Invoke-Core -Arguments $command } else { blastoff @command }
            if ($LASTEXITCODE -ne 0) { throw "Mutation failed for $frontend : $command" }
            $null=$output | ConvertFrom-Json -ErrorAction Stop
        }
        $backupArgs=@('backup','create','--json')
        $output=if ($frontend -eq 'core') { Invoke-Core -Arguments $backupArgs } else { blastoff @backupArgs }
        if ($LASTEXITCODE -ne 0) { throw 'Scenario backup failed' }
        $created=$output | ConvertFrom-Json
        [IO.File]::WriteAllText($env:STARSHIP_CONFIG,"[directory]`nstyle = 'red'`n",$utf8)
        foreach ($command in @(@('backup','restore',$created.backup,'--json'),
                               @('backup','delete',$created.backup,'--yes','--json'))) {
            $output=if ($frontend -eq 'core') { Invoke-Core -Arguments $command } else { blastoff @command }
            if ($LASTEXITCODE -ne 0) { throw "Backup operation failed for $frontend" }
            $null=$output | ConvertFrom-Json -ErrorAction Stop
        }
        $result=[ordered]@{active=[IO.File]::ReadAllText($env:STARSHIP_CONFIG)}
        foreach ($relative in @('themes/original.toml','themes/saved.toml','modules/compact.toml')) {
            $result[$relative]=[IO.File]::ReadAllText((Join-Path $env:BLASTOFF_HOME $relative))
        }
        if (Test-Path -LiteralPath (Join-Path $env:BLASTOFF_HOME 'themes/copied.toml')) { throw 'Theme deletion failed' }
        if ($result.active -cne [IO.File]::ReadAllText($inputFile)) { throw 'Restore lost unrelated TOML settings' }
        $currentArgs=@('current','--json')
        $output=if ($frontend -eq 'core') { Invoke-Core -Arguments $currentArgs } else { blastoff @currentArgs }
        if ($LASTEXITCODE -ne 0) { throw 'Scenario provenance query failed' }
        # Compare semantic provenance; inode/time fingerprints differ by fixture.
        $current=$output | ConvertFrom-Json
        foreach ($source in @($current.provenance.last_loaded,$current.provenance.save_target)) {
            if ($source -and $source.PSObject.Properties['fingerprint']) {
                if ($source.fingerprint.Count -ne 6) { throw 'Malformed source fingerprint' }
                $source.PSObject.Properties.Remove('fingerprint')
            }
        }
        $result['current']=($current | ConvertTo-Json -Compress -Depth 20).Replace(($scenario | ConvertTo-Json -Compress).Trim('"'),'SANDBOX')
        $scenarioResults+=($result | ConvertTo-Json -Compress -Depth 10)
    }
    if ($scenarioResults[0] -cne $scenarioResults[1]) { throw 'Core/module mutation or provenance state differs' }
    Write-Output "Passed literal argv/import checks, $passed read/error parity cases and isolated mutation/view/deletion checks."
    $success = $true
} finally {
    if ($argumentMode) { $global:PSNativeCommandArgumentPassing=$originalArgumentMode }
    foreach ($key in $names) { [Environment]::SetEnvironmentVariable($key, $previous[$key], 'Process') }
    if ($success -and -not $KeepSandbox) {
        Remove-Item -LiteralPath $temporaryRoot -Recurse -Force
    } else {
        Write-Warning "Retained disposable fixture for inspection: $temporaryRoot"
    }
}
