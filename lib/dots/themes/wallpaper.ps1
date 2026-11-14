# Private Windows WinRT adapter. Paths are JSON stdin, never shell source.
param([switch]$Check)

function Test-DotsLockScreenSupport {
    try {
        $settings = [Windows.System.UserProfile.UserProfilePersonalizationSettings,Windows.System.UserProfile,ContentType=WindowsRuntime]
        return [Environment]::Is64BitProcess -and $settings::IsSupported()
    } catch { return $false }
}

function Wait-DotsWallpaperTask {
    param([System.Threading.Tasks.Task]$Task, [DateTime]$Deadline)
    $remaining = [Math]::Max(1, [int]($Deadline - [DateTime]::UtcNow).TotalMilliseconds)
    if (-not $Task.Wait($remaining)) { throw 'Windows wallpaper operation timed out.' }
    $Task.GetAwaiter().GetResult()
}

function Get-DotsLockScreenFile {
    param([string]$Path, [DateTime]$Deadline)
    if (-not [IO.Path]::IsPathRooted($Path) -or -not [IO.File]::Exists($Path)) {
        throw 'An existing absolute image path is required.'
    }
    Add-Type -AssemblyName System.Runtime.WindowsRuntime -ErrorAction Stop
    $storage = [Windows.Storage.StorageFile,Windows.Storage,ContentType=WindowsRuntime]
    $operation = $storage::GetFileFromPathAsync($Path)
    $method = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
        $_.Name -eq 'AsTask' -and $_.IsGenericMethodDefinition -and
        $_.GetGenericArguments().Count -eq 1 -and $_.GetParameters().Count -eq 1 -and
        $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'
    } | Select-Object -First 1
    $task = $method.MakeGenericMethod($storage).Invoke($null, @($operation))
    Wait-DotsWallpaperTask $task $Deadline
}

function Wait-DotsWallpaperAction {
    param($Operation, [DateTime]$Deadline)
    $method = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
        $_.Name -eq 'AsTask' -and -not $_.IsGenericMethod -and
        $_.GetParameters().Count -eq 1 -and
        $_.GetParameters()[0].ParameterType.FullName -eq 'Windows.Foundation.IAsyncAction'
    } | Select-Object -First 1
    $task = $method.Invoke($null, @($Operation))
    $null = Wait-DotsWallpaperTask $task $Deadline
}

function Set-DotsLockScreenFile {
    param($File, [DateTime]$Deadline)
    $screen = [Windows.System.UserProfile.LockScreen,Windows.System.UserProfile,ContentType=WindowsRuntime]
    Wait-DotsWallpaperAction ($screen::SetImageFileAsync($File)) $Deadline
}

function Invoke-DotsLockScreenRequest {
    param([string]$Request)
    if (-not (Test-DotsLockScreenSupport)) { throw 'Windows lock-screen API is unavailable.' }
    $document = $Request | ConvertFrom-Json -ErrorAction Stop
    if ($document.path -isnot [string] -or $document.path.IndexOf([char]0) -ge 0) {
        throw 'An image path is required.'
    }
    $deadline = [DateTime]::UtcNow.AddSeconds(12)
    $file = Get-DotsLockScreenFile $document.path $deadline
    Set-DotsLockScreenFile $file $deadline
    @{applied=$true} | ConvertTo-Json -Compress
}

if ($MyInvocation.InvocationName -ne '.') {
    $ErrorActionPreference = 'Stop'
    $ProgressPreference = 'SilentlyContinue'
    [Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)
    [Console]::InputEncoding = [Text.UTF8Encoding]::new($false)
    try {
        if ($Check) { @{supported=(Test-DotsLockScreenSupport)} | ConvertTo-Json -Compress }
        else { Invoke-DotsLockScreenRequest ([Console]::In.ReadToEnd()) }
        exit 0
    } catch {
        [Console]::Error.WriteLine('Windows lock-screen adapter failed.')
        exit 1
    }
}
