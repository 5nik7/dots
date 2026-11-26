param([Parameter(Mandatory=$true)][string]$Request)
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)

function Get-ScopedPackageIds($Factory, $Manager, $Catalog, $Scope) {
    $options = $Factory.CreateCreateCompositePackageCatalogOptions()
    $options.CompositeSearchBehavior = 'LocalCatalogs'
    $options.InstalledScope = $Scope
    # Windows PowerShell exposes WinRT collections as __ComObject. Use their
    # declared collection interfaces on both engines for Add, Count and Item.
    $catalogsType = $options.GetType().GetProperty('Catalogs').PropertyType
    $add = $catalogsType.GetInterface('ICollection`1').GetMethod('Add')
    [void]$add.Invoke($options.Catalogs, @($Catalog))
    $connection = $Manager.CreateCompositePackageCatalog($options).Connect()
    if ($connection.Status -ne 'Ok') {
        throw "Could not open the WinGet $Scope catalog ($($connection.Status))."
    }
    $result = $connection.PackageCatalog.FindPackages($Factory.CreateFindPackagesOptions())
    if ($result.Status -ne 'Ok' -or $result.WasLimitExceeded) {
        throw "Incomplete WinGet $Scope inventory ($($result.Status), truncated=$($result.WasLimitExceeded))."
    }
    $items = $result.Matches
    $listType = $result.GetType().GetProperty('Matches').PropertyType
    $count = $listType.GetInterface('IReadOnlyCollection`1').GetProperty('Count').GetValue($items)
    $item = $listType.GetProperty('Item')
    for ($i = 0; $i -lt $count; $i++) {
        $package = $item.GetValue($items, @($i)).CatalogPackage
        if ($package.DefaultInstallVersion.PackageCatalog.Info.Name -eq 'winget') { $package.Id }
    }
}

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
    $scopeMatches = $null
    switch ($inputData.action) {
        # Keep uncorrelated installations visible. The controller disables
        # anything outside the verified community source or proven scope.
        'installed' {
            $packages = @(Get-WinGetPackage)
            # The cmdlet returns unscoped records. Use its activation factory
            # when available to open the community catalog once per scope.
            $factoryType = $source[0].GetType().Assembly.GetType('Microsoft.WinGet.Client.Engine.Helpers.ManagementDeploymentFactory')
            if ($factoryType -and $factoryType.GetMethod('CreateCreateCompositePackageCatalogOptions')) {
                $factory = $factoryType::Instance
                $manager = $factory.CreatePackageManager()
                $catalog = $manager.GetPackageCatalogByName('winget')
                $scopeMatches = @{}
                foreach ($scope in 'user','machine') {
                    $nativeScope = if ($scope -eq 'user') { 'User' } else { 'System' }
                    foreach ($id in (Get-ScopedPackageIds $factory $manager $catalog $nativeScope)) {
                        if (!$scopeMatches.ContainsKey($id)) { $scopeMatches[$id] = @() }
                        $scopeMatches[$id] += $scope
                    }
                }
            }
        }
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
        $row = @{id=[string]$_.Id; name=[string]$_.Name; source=[string]$_.Source;
          installed_version=$installed; version=$latest; versions=$versions;
          update_available=[bool]$_.IsUpdateAvailable}
        if ($null -ne $scopeMatches) {
            $row.scope_matches = [string[]]@()
            if ($scopeMatches.ContainsKey($row.id)) { $row.scope_matches = $scopeMatches[$row.id] }
        }
        $row
    })
    @{schema=1; packages=$rows} | ConvertTo-Json -Depth 8 -Compress
} catch {
    [Console]::Error.WriteLine($_.Exception.Message)
    exit 1
}
