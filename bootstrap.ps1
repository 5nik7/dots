# Standalone native Windows first stage. No Bash/WSL dependency.
$ErrorActionPreference = 'Stop'
$bootstrap = @{ Destination = ''; Source = 'https://github.com/5nik7/dots.git'; Ref = 'main'; Yes = $false; DryRun = $false; Offline = $false; NonInteractive = $false; Json = $false; DeveloperMode = $false }
$forward = New-Object 'System.Collections.Generic.List[string]'
$inputArguments = @($args | ForEach-Object { [string] $_ })
for ($i = 0; $i -lt $inputArguments.Count; $i++) {
    $argument = $inputArguments[$i]
    switch -Regex ($argument) {
        '^--?(destination|source|ref)$' {
            $name = $Matches[1]
            if (++$i -ge $inputArguments.Count) { throw "Missing value for $argument" }
            $bootstrap[$name] = $inputArguments[$i]; continue
        }
        '^(-y|--?yes)$' { $bootstrap.Yes = $true; continue }
        '^--?(dry-run|DryRun)$' { $bootstrap.DryRun = $true; continue }
        '^--?offline$' { $bootstrap.Offline = $true; continue }
        '^--?(non-interactive|NonInteractive)$' { $bootstrap.NonInteractive = $true; continue }
        '^--?json$' { $bootstrap.Json = $true; continue }
        '^--?(developer-mode|DeveloperMode)$' { $bootstrap.DeveloperMode = $true; continue }
        '^(-h|--?help)$' {
            'Usage: bootstrap.ps1 [-Destination PATH] [-Source HTTPS_OR_LOCAL_REPO] [-Ref REF]'
            '                     [-DryRun] [-Yes] [-Offline] [-DeveloperMode] [INSTALLER OPTIONS...]'
            'Double-dash spellings are also accepted. Configure installed PowerShell engines; no Bash is required.'
            return
        }
        default { $forward.Add($argument) }
    }
}

function Test-DotsCheckout([string] $Path) {
    return (Test-Path -LiteralPath (Join-Path $Path 'install.ps1') -PathType Leaf) -and
        (Test-Path -LiteralPath (Join-Path $Path 'bin/dots.ps1') -PathType Leaf) -and
        (Test-Path -LiteralPath (Join-Path $Path 'lib/dots/files/install.py') -PathType Leaf)
}
function Confirm-DotsBootstrap([string] $Message, [switch] $Explicit) {
    if ($bootstrap.Yes -and -not $Explicit) { return $true }
    if ($bootstrap.NonInteractive -or [Console]::IsInputRedirected) {
        throw ($Message + ': explicit approval is required; use -Yes for preparation or -DeveloperMode for the Windows setting')
    }
    $answer = Read-Host ($Message + ' [y/N]')
    return $answer -in @('y','yes')
}
function Update-DotsBootstrapPath {
    $entries = @($env:PATH -split ';') + @([Environment]::GetEnvironmentVariable('Path','User') -split ';') + @([Environment]::GetEnvironmentVariable('Path','Machine') -split ';')
    $env:PATH = (($entries | Where-Object { $_ } | Select-Object -Unique) -join ';')
}
function Find-DotsBootstrapPython {
    # A discovery probe must not trigger Python Manager/launcher installation.
    $oldAutomatic, $oldLauncher = $env:PYTHON_MANAGER_AUTOMATIC_INSTALL, $env:PYLAUNCHER_ALLOW_INSTALL
    try {
        $env:PYTHON_MANAGER_AUTOMATIC_INSTALL = 'false'; $env:PYLAUNCHER_ALLOW_INSTALL = '0'
        foreach ($candidate in @(Get-Command py, python3, python -CommandType Application -ErrorAction SilentlyContinue)) {
            if ($candidate.Source -like '*\WindowsApps\*' -and $candidate.Name -ne 'py.exe') { continue }
            $prefix = @(); if ($candidate.Name -in @('py','py.exe')) { $prefix = @('-3') }
            try { $found = & $candidate.Source @prefix -B -c 'import sys;sys.exit(1) if sys.version_info < (3,11) else print(sys.executable)' 2>$null } catch { continue }
            if ($LASTEXITCODE -eq 0 -and $found -and (Test-Path -LiteralPath ([string]@($found)[-1]) -PathType Leaf)) { return [string]@($found)[-1] }
        }
    } finally { $env:PYTHON_MANAGER_AUTOMATIC_INSTALL = $oldAutomatic; $env:PYLAUNCHER_ALLOW_INSTALL = $oldLauncher }
    return $null
}
function Invoke-DotsBootstrapNative([string] $Command, [string[]] $Arguments) {
    & $Command @Arguments 1>&2
    if ($LASTEXITCODE -ne 0) { throw ('Prerequisite command failed (' + $LASTEXITCODE + '); completed package changes remain. Resume after resolving the error.') }
}
function Install-DotsOfficialGit {
    $oldTls = [Net.ServicePointManager]::SecurityProtocol
    try {
        [Net.ServicePointManager]::SecurityProtocol = $oldTls -bor [Net.SecurityProtocolType]::Tls12
        $release = Invoke-RestMethod -Uri 'https://api.github.com/repos/git-for-windows/git/releases/latest' -Headers @{ Accept = 'application/vnd.github+json'; 'User-Agent' = 'dots-bootstrap' }
        $architecture = if ($env:PROCESSOR_ARCHITECTURE -eq 'ARM64' -or $env:PROCESSOR_ARCHITEW6432 -eq 'ARM64') { 'arm64' } else { '64-bit' }
        $assets = @($release.assets | Where-Object { $_.name -match ('^Git-[0-9.]+-' + $architecture + '\.exe$') })
        if ($assets.Count -ne 1) { throw 'No unambiguous official Git installer is available for this architecture; install Git explicitly and resume.' }
        $asset = $assets[0]
        if ($asset.browser_download_url -notmatch '^https://github\.com/git-for-windows/git/releases/download/[^/]+/Git-[0-9.]+-(64-bit|arm64)\.exe$' -or $asset.digest -notmatch '^sha256:([0-9a-f]{64})$') { throw 'Official Git installer metadata lacks a verifiable SHA-256 digest.' }
        $expectedHash = $asset.digest.Substring(7)
        $directory = Join-Path ([IO.Path]::GetTempPath()) ('dots-git-prerequisite-' + [guid]::NewGuid().ToString('N'))
        [void][IO.Directory]::CreateDirectory($directory)
        $installer = Join-Path $directory $asset.name
        Invoke-WebRequest -UseBasicParsing -Uri $asset.browser_download_url -OutFile $installer
        if ((Get-FileHash -Algorithm SHA256 -LiteralPath $installer).Hash -ine $expectedHash) { throw 'Git installer checksum mismatch; the downloaded installer was not executed.' }
        $signature = Get-AuthenticodeSignature -LiteralPath $installer
        if ($signature.Status -ne 'Valid') { throw 'Git installer signature verification failed; the downloaded installer was not executed.' }
        [Console]::Error.WriteLine('Verified Git installer: ' + $asset.name + ' (' + $signature.SignerCertificate.Subject + ')')
        $process = Start-Process -FilePath $installer -ArgumentList @('/VERYSILENT','/NORESTART','/CURRENTUSER','/SP-') -Wait -PassThru
        if ($process.ExitCode -ne 0) { throw ('Git installer failed with exit ' + $process.ExitCode + '; retained download: ' + $directory) }
        Remove-Item -LiteralPath $installer -Force
    } finally { [Net.ServicePointManager]::SecurityProtocol = $oldTls }
}
function Install-DotsOfficialPython {
    # Windows validates the signed MSIX package; Python Manager validates its
    # official runtime feed. Do not uninstall or overwrite an existing launcher.
    $manager = Get-Command pymanager -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $manager) {
        Add-AppxPackage -AppInstallerFile 'https://www.python.org/ftp/python/pymanager/pymanager.appinstaller' -ErrorAction Stop
        Update-DotsBootstrapPath
        $manager = Get-Command pymanager -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    }
    if (-not $manager) { throw 'Python Manager was installed but is not discoverable; open a new terminal and resume bootstrap.' }
    Invoke-DotsBootstrapNative $manager.Source @('install','--yes','3.14')
}
function Test-DotsBootstrapLinks([string] $Python, [string] $Parent) {
    # This probe runs only after approval, in an owned temporary directory.
    & $Python -B -c 'import os,pathlib,tempfile,sys; p=pathlib.Path(sys.argv[1]); p=next((x for x in (p,*p.parents) if x.is_dir())); t=tempfile.TemporaryDirectory(prefix="dots-link-probe-",dir=p); root=pathlib.Path(t.name); (root/"file").write_text("probe"); os.symlink(root/"file",root/"link"); t.cleanup()' $Parent 2>$null
    return $LASTEXITCODE -eq 0
}
function Enable-DotsBootstrapDeveloperMode {
    $command = "New-Item -Path 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\AppModelUnlock' -Force | Out-Null; New-ItemProperty -Path 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\AppModelUnlock' -Name AllowDevelopmentWithoutDevLicense -Value 1 -PropertyType DWord -Force | Out-Null"
    $encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes('$ErrorActionPreference = ''Stop''; ' + $command))
    $engine = Join-Path $env:SystemRoot 'System32/WindowsPowerShell/v1.0/powershell.exe'
    $process = Start-Process -FilePath $engine -ArgumentList @('-NoProfile','-EncodedCommand',$encoded) -Verb RunAs -Wait -PassThru
    if ($process.ExitCode -ne 0) { throw 'Developer Mode was not enabled; required symlinks remain blocked.' }
    [Console]::Error.WriteLine('Developer Mode enabled explicitly. This Windows setting remains enabled if later setup fails.')
}

try {
    if ($env:OS -ne 'Windows_NT') { throw 'Use bootstrap.sh for Termux/Linux/WSL; bootstrap.ps1 is the native Windows adapter.' }
    if (-not $bootstrap.Destination) { $bootstrap.Destination = if (Test-DotsCheckout $PSScriptRoot) { $PSScriptRoot } else { Join-Path $HOME 'dots' } }
    if ($bootstrap.Destination.StartsWith('~/') -or $bootstrap.Destination.StartsWith('~\')) { $bootstrap.Destination = Join-Path $HOME $bootstrap.Destination.Substring(2) }
    $bootstrap.Destination = [IO.Path]::GetFullPath($bootstrap.Destination)
    if (-not $bootstrap.Ref -or $bootstrap.Ref.StartsWith('-') -or $bootstrap.Ref -match '\s|[\x00-\x1f]') { throw 'Invalid bootstrap ref.' }
    if (-not [IO.Path]::IsPathRooted($bootstrap.Source)) {
        $sourceUri = [Uri]$bootstrap.Source
        if ($sourceUri.Scheme -ne 'https' -or $sourceUri.UserInfo -or $sourceUri.Query -or $sourceUri.Fragment) { throw 'Source must be HTTPS without credentials/parameters, or an absolute local repository path.' }
    }
    if (($bootstrap.Source + $bootstrap.Destination) -match '[\x00-\x1f\x7f]') { throw 'Bootstrap paths must not contain control characters.' }
    $existing = Test-Path -LiteralPath $bootstrap.Destination
    if ($existing -and -not (Test-DotsCheckout $bootstrap.Destination)) { throw 'Destination is occupied by something other than a Dots checkout.' }
    $python = Find-DotsBootstrapPython
    $git = Get-Command git -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    $winget = Get-Command winget -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    $missing = @(); if (-not $python) { $missing += 'Python 3.11+' }; if (-not $existing -and -not $git) { $missing += 'Git' }
    if ($bootstrap.DryRun -and (-not $existing -or $missing.Count)) {
        $preview = @{ schema = 1; status = 'planned'; destination = $bootstrap.Destination; source = $bootstrap.Source; ref = $bootstrap.Ref; missing = $missing; manager = if ($winget) { 'winget' } else { 'official-installers' }; symlinks = 'capability checked after approval' }
        if ($bootstrap.Json) { $preview | ConvertTo-Json -Depth 5 -Compress } else { $preview | Format-List; 'No changes made.' }
        return
    }
    if ($missing.Count) {
        if ($bootstrap.Offline) { throw ('Offline setup requires preinstalled ' + ($missing -join ', ')) }
        [Console]::Error.WriteLine('Prepare: ' + ($missing -join ', ') + $(if ($winget) { ' using WinGet (user scope)' } else { ' using official signed installers' }))
        if (-not (Confirm-DotsBootstrap 'Install these prerequisites? Package changes remain if later setup fails.')) { exit 130 }
        if (-not $python) {
            if ($winget) { Invoke-DotsBootstrapNative $winget.Source @('install','--id','Python.Python.3.14','--exact','--source','winget','--scope','user','--accept-package-agreements','--disable-interactivity') }
            else { Install-DotsOfficialPython }
        }
        if (-not $existing -and -not $git) {
            if ($winget) { Invoke-DotsBootstrapNative $winget.Source @('install','--id','Git.Git','--exact','--source','winget','--scope','user','--accept-package-agreements','--disable-interactivity') }
            else { Install-DotsOfficialGit }
        }
        Update-DotsBootstrapPath
        $python = Find-DotsBootstrapPython
        $git = Get-Command git -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
        if (-not $python -or (-not $existing -and -not $git)) { throw 'Installed prerequisites are not available yet. Open a new terminal and resume; completed package changes remain.' }
    }
    if (-not $existing) {
        if ($bootstrap.Offline) { throw 'Offline bootstrap requires an existing checkout.' }
        if (-not (Confirm-DotsBootstrap ('Fetch ' + $bootstrap.Source + ' at ' + $bootstrap.Ref + ' into ' + $bootstrap.Destination + '?'))) { exit 130 }
        $parent = Split-Path -Parent $bootstrap.Destination
        [void][IO.Directory]::CreateDirectory($parent)
        $stage = Join-Path $parent ('.dots-bootstrap-' + [guid]::NewGuid().ToString('N'))
        [void][IO.Directory]::CreateDirectory($stage)
        $checkout = Join-Path $stage 'checkout'
        $journal = Join-Path $stage 'journal.json'
        $record = @{ schema = 1; status = 'preparing'; destination = $bootstrap.Destination; source = $bootstrap.Source; ref = $bootstrap.Ref }
        $record | ConvertTo-Json | Set-Content -LiteralPath $journal -Encoding UTF8
        $oldGit = @{}
        foreach ($key in @('GIT_DIR','GIT_WORK_TREE','GIT_COMMON_DIR','GIT_INDEX_FILE','GIT_OBJECT_DIRECTORY','GIT_ALTERNATE_OBJECT_DIRECTORIES','GIT_TERMINAL_PROMPT','GCM_INTERACTIVE')) { $oldGit[$key] = [Environment]::GetEnvironmentVariable($key); [Environment]::SetEnvironmentVariable($key,$null,'Process') }
        try {
            $env:GIT_TERMINAL_PROMPT = '0'; $env:GCM_INTERACTIVE = 'Never'
            Invoke-DotsBootstrapNative $git.Source @('init','--',$checkout)
            Invoke-DotsBootstrapNative $git.Source @('-C',$checkout,'remote','add','origin',$bootstrap.Source)
            Invoke-DotsBootstrapNative $git.Source @('-C',$checkout,'-c','submodule.recurse=false','-c','protocol.ext.allow=never','fetch','--depth=1','--no-recurse-submodules','origin',$bootstrap.Ref)
            Invoke-DotsBootstrapNative $git.Source @('-C',$checkout,'checkout','--detach','FETCH_HEAD')
            if (-not (Test-DotsCheckout $checkout)) { throw 'Acquired source lacks the Dots setup layout.' }
            $record.commit = [string](& $git.Source -C $checkout rev-parse HEAD)
            if ($LASTEXITCODE -ne 0) { throw 'Cannot determine the acquired commit.' }
            $record.status = 'prepared'; $record | ConvertTo-Json | Set-Content -LiteralPath $journal -Encoding UTF8
            [IO.Directory]::Move($checkout,$bootstrap.Destination)
            $record.status = 'committed'; $record | ConvertTo-Json | Set-Content -LiteralPath $journal -Encoding UTF8
        } catch {
            $record.status = 'failed'; $record | ConvertTo-Json | Set-Content -LiteralPath $journal -Encoding UTF8
            throw ('Checkout preparation failed. Retained journal: ' + $journal)
        } finally { foreach ($key in $oldGit.Keys) { [Environment]::SetEnvironmentVariable($key,$oldGit[$key],'Process') } }
    }
    if (-not $bootstrap.DryRun -and -not (Test-DotsBootstrapLinks $python $bootstrap.Destination)) {
        if (-not $bootstrap.DeveloperMode -and -not (Confirm-DotsBootstrap 'Enable Windows Developer Mode for symlinks? Administrator approval is required.' -Explicit)) { throw 'Symlink capability was declined; managed setup was not applied.' }
        Enable-DotsBootstrapDeveloperMode
        if (-not (Test-DotsBootstrapLinks $python $bootstrap.Destination)) { throw 'Symlinks are still unavailable on this filesystem; managed setup was not applied.' }
    }
    $cli = @('install','--with-dependencies') + $forward.ToArray()
    if ($bootstrap.Offline) { $cli += '--offline' }
    if ($bootstrap.Yes) { $cli += '--yes' }; if ($bootstrap.DryRun) { $cli += '--dry-run' }
    if ($bootstrap.NonInteractive) { $cli += '--non-interactive' }; if ($bootstrap.Json) { $cli += '--json' }
    $env:DOTS_BOOTSTRAP_READY = '1'
    . (Join-Path $bootstrap.Destination 'lib/dots/files/entry.ps1')
    Invoke-DotsFiles $bootstrap.Destination 'install' $cli @{} $python
    exit $script:DotsFilesExitCode
} catch {
    [Console]::Error.WriteLine('dots bootstrap: ' + $_.Exception.Message)
    exit 1
}
