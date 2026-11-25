param([string] $Mode = 'offline', [switch] $Utf8,
      [ValidateSet('powershell','nu','xonsh')][string] $Shell = 'powershell')
$ErrorActionPreference = 'Stop'
$nativeEntry = @{ powershell='shells/powershell/profile.ps1'; nu='shells/nushell/init.nu'; xonsh='shells/xonsh/init.xsh' }[$Shell]

function Test-Checkout([string] $Root) {
    $Root -and (Test-Absolute $Root) -and [IO.File]::Exists([IO.Path]::Combine($Root, 'bin/dots.ps1')) -and
        [IO.File]::Exists([IO.Path]::Combine($Root, 'lib/dots/shell/startup.bash')) -and
        [IO.File]::Exists([IO.Path]::Combine($Root, $nativeEntry))
}
function Write-Checkout([string] $Root) {
    # Windows PowerShell 5.1 normally encodes a native pipe with the OEM codepage.
    if ($Utf8) {
        $bytes = [Text.Encoding]::UTF8.GetBytes($Root + "`n")
        [Console]::OpenStandardOutput().Write($bytes, 0, $bytes.Length)
    } else { $Root }
}
function Test-Occupied([string] $Path) {
    try { [void][IO.File]::GetAttributes($Path); return $true }
    catch [IO.FileNotFoundException] { return $false }
    catch [IO.DirectoryNotFoundException] { return $false }
}
function Test-Absolute([string] $Path) {
    if ($windowsHost) { return $Path -match '^(?:[a-z]:[\\/]|\\\\(?![?.]\\)[^\\/]+\\[^\\/]+(?:\\|$))' }
    return $Path.StartsWith('/')
}
function New-PrivateStage([string] $Path) {
    if ($windowsHost) {
        $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
        try {
            $acl = [Security.AccessControl.DirectorySecurity]::new()
            $acl.SetOwner($identity.User)
            $acl.SetAccessRuleProtection($true, $false)
            $rule = [Security.AccessControl.FileSystemAccessRule]::new($identity.User, 'FullControl',
                'ContainerInherit, ObjectInherit', 'None', 'Allow')
            $acl.AddAccessRule($rule)
            $directory = [IO.DirectoryInfo]::new($Path)
            if ($PSVersionTable.PSEdition -eq 'Desktop') { [void]$directory.Create($acl) }
            else { [void][IO.FileSystemAclExtensions]::Create($directory, $acl) }
        } finally { $identity.Dispose() }
    } else {
        # pwsh on Unix uses the same private, create-only semantics.
        & (Get-Command mkdir -CommandType Application -TotalCount 1).Source -m 700 -- $Path
        if ($LASTEXITCODE -ne 0) { throw 'Cannot create private checkout staging.' }
    }
}
function Write-Journal([string] $Name, [string] $Text) {
    $path = [IO.Path]::Combine($stage, $Name)
    $temporary = $path + '.' + [guid]::NewGuid().ToString('N')
    $stream = [IO.File]::Open($temporary, 'CreateNew', 'Write', 'None')
    try {
        $bytes = [Text.Encoding]::UTF8.GetBytes($Text + "`n")
        $stream.Write($bytes, 0, $bytes.Length)
        $stream.Flush($true)
    } finally { $stream.Dispose() }
    if ([IO.File]::Exists($path)) { [IO.File]::Replace($temporary, $path, [Management.Automation.Language.NullString]::Value) }
    else { [IO.File]::Move($temporary, $path) }
}
function Write-Status([string] $Status) {
    Write-Journal 'journal.json' (ConvertTo-Json -Compress @{version=1; destination=$target; ref=$ref; status=$Status})
}
function ConvertTo-NativeArgument([string] $Value) {
    # Windows CRT quoting for .NET Framework, which has no ArgumentList.
    return '"' + [regex]::Replace($Value, '(\\*)("|$)', {
        param($match)
        $slashes = $match.Groups[1].Value
        if ($match.Groups[2].Value) { return $slashes + $slashes + '\"' }
        return $slashes + $slashes
    }) + '"'
}
function Stop-Clone([Diagnostics.Process] $Process) {
    if ($Process.HasExited) { return }
    if ($PSVersionTable.PSEdition -ne 'Desktop') {
        try { $Process.Kill($true); return } catch {}
    }
    if ($windowsHost) {
        # Desktop 5.1 has no process-tree Kill overload.
        $kill = [Diagnostics.ProcessStartInfo]::new()
        $kill.FileName = [IO.Path]::Combine([Environment]::SystemDirectory, 'taskkill.exe')
        $kill.Arguments = '/T /F /PID ' + $Process.Id
        $kill.UseShellExecute = $false
        $kill.CreateNoWindow = $true
        $kill.RedirectStandardOutput = $true
        $kill.RedirectStandardError = $true
        $killer = [Diagnostics.Process]::Start($kill)
        try {
            $null = $killer.StandardOutput.ReadToEndAsync()
            $null = $killer.StandardError.ReadToEndAsync()
            if (-not $killer.WaitForExit(3000)) { $killer.Kill() }
        } finally { $killer.Dispose() }
    }
    if (-not $Process.HasExited) { $Process.Kill() }
}
function Invoke-Clone {
    $start = [Diagnostics.ProcessStartInfo]::new()
    $start.FileName = $git.Source
    $start.WorkingDirectory = $stage
    $start.UseShellExecute = $false
    $start.CreateNoWindow = $true
    $start.RedirectStandardInput = $true
    $start.RedirectStandardOutput = $true
    $start.RedirectStandardError = $true
    $words = @('-c','credential.helper=','-c','core.askPass=','-c','protocol.ext.allow=never',
        '-c','http.lowSpeedLimit=1','-c','http.lowSpeedTime=30','clone','--quiet','--no-recurse-submodules',
        '--single-branch','--branch',$ref,'--',$source,$checkout)
    if ($start.PSObject.Properties['ArgumentList']) {
        foreach ($word in $words) { $start.ArgumentList.Add($word) }
    } else { $start.Arguments = ($words | ForEach-Object { ConvertTo-NativeArgument $_ }) -join ' ' }
    $environment = $start.EnvironmentVariables
    foreach ($name in @($environment.Keys)) {
        if ($name -match '^(GIT_|GCM_|SSH_ASKPASS)') { $environment.Remove($name) }
    }
    $environment['HOME'] = $stage
    $environment['USERPROFILE'] = $stage
    $environment['XDG_CONFIG_HOME'] = $stage
    $environment['GIT_CONFIG_NOSYSTEM'] = '1'
    $environment['GIT_CONFIG_GLOBAL'] = if ($windowsHost) { 'NUL' } else { '/dev/null' }
    $environment['GIT_ALLOW_PROTOCOL'] = if ($localSource) { 'file' } else { 'https' }
    $environment['GIT_TERMINAL_PROMPT'] = '0'
    $environment['GCM_INTERACTIVE'] = 'Never'
    $environment['GIT_LFS_SKIP_SMUDGE'] = '1'
    $process = [Diagnostics.Process]::Start($start)
    try {
        $process.StandardInput.Close()
        $out = $process.StandardOutput.BaseStream.CopyToAsync([IO.Stream]::Null)
        $err = $process.StandardError.BaseStream.CopyToAsync([IO.Stream]::Null)
        $timer = [Diagnostics.Stopwatch]::StartNew()
        while (-not $process.WaitForExit(200)) {
            if ($timer.ElapsedMilliseconds -ge 90000) { throw 'Git clone timed out.' }
        }
        if ($process.ExitCode -ne 0) { throw 'Git clone failed. Check the source/ref and retry.' }
    } finally {
        try {
            if (-not $process.HasExited) {
                Stop-Clone $process
                [void]$process.WaitForExit(3000)
            }
        }
        finally { $process.Dispose() }
    }
}

try {
    $windowsHost = [IO.Path]::DirectorySeparatorChar -eq '\'
    $target = $env:DOTS_BOOTSTRAP_DIR
    if ($target -and ($target -match '\p{Cc}' -or -not (Test-Absolute $target))) { throw 'DOTS_BOOTSTRAP_DIR must be absolute.' }
    if (-not $target) {
        $target = Join-Path $HOME 'dots'
        $command = Get-Command dots.ps1 -CommandType ExternalScript -TotalCount 1 -ErrorAction SilentlyContinue
        if ($command) {
            $root = Split-Path -Parent (Split-Path -Parent $command.Path)
            if (Test-Checkout $root) { Write-Checkout $root; return }
        }
        $pin = Join-Path $HOME '.local/share/dots/bootstrap/checkout'
        if ([IO.File]::Exists($pin)) {
            $root = [IO.File]::ReadAllText($pin).TrimEnd([char]13, [char]10)
            if (Test-Checkout $root) { Write-Checkout $root; return }
        }
    }
    if (Test-Checkout $target) { Write-Checkout $target; return }
    if ($Mode -ne 'interactive') { return }
    $target = [IO.Path]::GetFullPath($target)
    if ($target -eq [IO.Path]::GetPathRoot($target)) { throw 'Checkout destination is occupied.' }
    $target = $target.TrimEnd([IO.Path]::DirectorySeparatorChar)
    $git = Get-Command git -CommandType Application -All -ErrorAction SilentlyContinue |
        Where-Object { -not $windowsHost -or [IO.Path]::GetExtension($_.Source) -ieq '.exe' } | Select-Object -First 1
    if (-not $git) { throw 'Install Git or set DOTS_BOOTSTRAP_DIR to an existing checkout.' }
    $source = $env:DOTS_BOOTSTRAP_SOURCE
    if (-not $source) { $source = 'https://github.com/5nik7/dots.git' }
    $ref = $env:DOTS_BOOTSTRAP_REF
    if (-not $ref) { $ref = 'main' }
    if ($ref -match '^-|\s|\p{Cc}' -or $source -match '\p{Cc}') { throw 'Invalid bootstrap source or ref.' }
    $localSource = (Test-Absolute $source) -and (-not $windowsHost -or $source -match '^[a-z]:[\\/]')
    if (-not $localSource -and $source -match '^file:///' -and $source -notmatch '[?#]') {
        $localUri = $null
        if ([uri]::TryCreate($source, 'Absolute', [ref]$localUri) -and $localUri.IsFile -and -not $localUri.Host) {
            $source = $localUri.LocalPath
            $localSource = Test-Absolute $source
        }
    } elseif (-not $localSource -and $source -notmatch '^[-/\\]|:' -and [IO.Directory]::Exists($source)) {
        $source = [IO.Path]::GetFullPath($source)
        $localSource = $true
    }
    if (-not $localSource) {
        $uri = $null
        if ($source -notmatch '^https://' -or -not [uri]::TryCreate($source, 'Absolute', [ref]$uri) -or
            -not $uri.Host -or $uri.UserInfo -or $source -match '^https://[^/]*@|[?#\\]') { throw 'Use a credential-free HTTPS or absolute local source.' }
    }
    $parent = [IO.Directory]::GetParent($target)
    if (-not $parent) { throw 'Invalid checkout destination.' }
    $key = if ($windowsHost) { $target.ToUpperInvariant() } else { $target }
    $hash = [Security.Cryptography.SHA256]::Create()
    try { $digest = [BitConverter]::ToString($hash.ComputeHash([Text.Encoding]::UTF8.GetBytes($key))) }
    finally { $hash.Dispose() }
    $mutex = [Threading.Mutex]::new($false, 'Dots.ShellBootstrap.' + $digest)
    $held = $false
    try {
        try { $held = $mutex.WaitOne(95000) } catch [Threading.AbandonedMutexException] { $held = $true }
        if (Test-Checkout $target) { Write-Checkout $target; return }
        if (-not $held) { throw 'Acquisition is busy. Retry after the other shell finishes.' }
        if (Test-Occupied $target) { throw 'Checkout destination is occupied.' }
        [void][IO.Directory]::CreateDirectory($parent.FullName)
        $stage = [IO.Path]::Combine($parent.FullName, '.' + [IO.Path]::GetFileName($target) + '.bootstrap-' + [guid]::NewGuid().ToString('N'))
        New-PrivateStage $stage
        $checkout = [IO.Path]::Combine($stage, 'checkout')
        Write-Status 'preparing'
        $status = 'failed'
        try {
            Invoke-Clone
            if (-not (Test-Checkout $checkout)) { throw 'Source lacks Dots startup files.' }
            Write-Status 'prepared'
            try { [IO.Directory]::Move($checkout, $target); $status = 'committed' }
            catch [IO.IOException] {
                if (-not (Test-Checkout $target)) { throw 'Checkout destination became occupied.' }
                $status = 'superseded'
            }
        } finally { Write-Status $status }
    } finally {
        if ($held) { $mutex.ReleaseMutex() }
        $mutex.Dispose()
    }
    Write-Checkout $target
} catch {
    $reason = if ($_.Exception -is [Management.Automation.RuntimeException] -and $_.FullyQualifiedErrorId -eq $_.Exception.Message) {
        $_.Exception.Message
    } else { 'Checkout acquisition failed. Check the destination and retry.' }
    [Console]::Error.WriteLine('dots bootstrap: ' + $reason)
}
