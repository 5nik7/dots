param([Parameter(Mandatory=$true)][string]$Request)
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
try {
    $inputData = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($Request)) | ConvertFrom-Json
    if ($inputData.action -eq 'install-module') {
        # Setup offers this exact prerequisite separately. Never bootstrap a
        # provider, register a repository or change repository trust implicitly.
        $providers = @(Get-PackageProvider -Name NuGet -ListAvailable -ErrorAction SilentlyContinue |
            Where-Object { [version]$_.Version -ge [version]'2.8.5.201' })
        if (-not $providers.Count) {
            throw 'NuGet provider 2.8.5.201 or newer is required; install it explicitly before the WinGet module.'
        }
        $repository = Get-PSRepository -Name PSGallery
        if ($repository.SourceLocation.TrimEnd('/') -ne 'https://www.powershellgallery.com/api/v2') {
            throw 'PSGallery source differs from the official repository; review it manually.'
        }
        Install-Module Microsoft.WinGet.Client -RequiredVersion '1.29.380' -Scope CurrentUser -Repository PSGallery -Force -AcceptLicense
    }
    if (-not (Get-Module -ListAvailable Microsoft.WinGet.Client)) {
        if ($inputData.action -eq 'capabilities') {
            @{schema=1; module=$null; missing=$true} | ConvertTo-Json -Compress
            exit 0
        }
        throw 'Microsoft.WinGet.Client is missing. Setup with --with-dependencies offers its current-user installation.'
    }
    Import-Module Microsoft.WinGet.Client
    $source = @(Get-WinGetSource -Name winget)
    if ($source.Count -ne 1 -or $source[0].Argument.TrimEnd('/') -ne 'https://cdn.winget.microsoft.com/cache' -or $source[0].Type -ne 'Microsoft.PreIndexed.Package') {
        throw 'The winget source is not the official community catalog; review sources explicitly.'
    }
    if ($inputData.action -in @('capabilities', 'install-module')) {
        @{schema=1; module=(Get-Module Microsoft.WinGet.Client).Version.ToString()} | ConvertTo-Json -Compress
        exit 0
    }
    $packages = @()
    switch ($inputData.action) {
        # Keep uncorrelated installations visible. The controller disables
        # anything outside the verified community source or proven scope.
        'installed' { $packages = @(Get-WinGetPackage) }
        'search' { $packages = @(Find-WinGetPackage -Source winget -Query ([string]$inputData.query) -Count 200) }
        'info' { $packages = @(Find-WinGetPackage -Source winget -Id ([string]$inputData.id) -MatchOption EqualsCaseInsensitive) }
        default { throw 'Unknown WinGet bridge operation' }
    }
    $rows = @($packages | ForEach-Object {
        $versions = @($_.AvailableVersions)
        $installed = ''
        if ($inputData.action -eq 'installed') { $installed = [string]$_.InstalledVersion }
        $latest = ''
        if ($versions.Count) { $latest = [string]$versions[0] }
        @{id=[string]$_.Id; name=[string]$_.Name; source=[string]$_.Source;
          installed_version=$installed; version=$latest; versions=$versions;
          update_available=[bool]$_.IsUpdateAvailable}
    })
    @{schema=1; packages=$rows} | ConvertTo-Json -Depth 8 -Compress
} catch {
    [Console]::Error.WriteLine($_.Exception.Message)
    exit 1
}
