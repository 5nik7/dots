# Copyright (c) Thomas Nieto - All Rights Reserved
# You may use, distribute and modify this code under the
# terms of the MIT license.

using module AnyPackage
using module Microsoft.PowerShell.PSResourceGet

using namespace System.Collections.Generic
using namespace AnyPackage.Provider
using namespace Microsoft.PowerShell.PSResourceGet.UtilClasses

[PackageProvider('PSResourceGet')]
class PSResourceGetProvider : PackageProvider, IGetPackage, IFindPackage,
IInstallPackage, ISavePackage, IUninstallPackage,
IUpdatePackage, IPublishPackage, IGetSource, ISetSource {
    #region GetPackage
    [void] GetPackage([PackageRequest] $request) {
        $params = @{
            Name        = $request.Name
            ErrorAction = 'SilentlyContinue'
        }

        if ($request.Version) {
            $params['Version'] = $request.Version
        }

        $request.DynamicParameters |
        ConvertTo-Hashtable -Hashtable $params -IsBound

        Get-InstalledPSResource @params |
        Write-Package -Request $request
    }
    #endregion

    #region FindPackage
    [void] FindPackage([PackageRequest] $request) {
        $params = @{
            Name        = $request.Name
            Prerelease  = $request.Prerelease
            ErrorAction = 'SilentlyContinue'
        }

        if ($request.Version) {
            $params['Version'] = $request.Version
        }

        if ($request.Source) {
            $params['Repository'] = $request.Source
        }

        $request.DynamicParameters |
        ConvertTo-Hashtable -Hashtable $params -Exclude 'Latest' -IsBound

        $resources = Find-PSResource @params

        if ($request.DynamicParameters.Latest) {
            $resources = $resources | Get-Latest
        }

        $resources | Write-Package -Request $request
    }
    #endregion

    #region InstallPackage
    [void] InstallPackage([PackageRequest] $request) {
        $params = @{
            Name        = $request.Name
            Prerelease  = $request.Prerelease
            ErrorAction = 'SilentlyContinue'
        }

        if ($request.Version) {
            $params['Version'] = $request.Version
        }

        if ($request.Source) {
            $params['Repository'] = $request.Source
        }

        $installParams = @{ }

        $request.DynamicParameters |
        ConvertTo-Hashtable -Hashtable $installParams -IsBound

        Find-PSResource @params |
        Get-Latest |
        Install-PSResource @installParams -TrustRepository -PassThru |
        Write-Package -Request $request
    }
    #endregion

    #region SavePackage
    [void] SavePackage([PackageRequest] $request) {
        $params = @{
            Name        = $request.Name
            Prerelease  = $request.Prerelease
            ErrorAction = 'SilentlyContinue'
        }

        if ($request.Version) {
            $params['Version'] = $request.Version
        }

        if ($request.Source) {
            $params['Repository'] = $request.Source
        }

        $saveParams = @{ }

        $request.DynamicParameters |
        ConvertTo-Hashtable -Hashtable $saveParams -IsBound

        Find-PSResource @params |
        Get-Latest |
        Save-PSResource @saveParams -Path $request.Path -TrustRepository -PassThru |
        Write-Package -Request $request
    }
    #endregion

    #region UninstallPackage
    [void] UninstallPackage([PackageRequest] $request) {
        $params = @{
            Name        = $request.Name
            ErrorAction = 'SilentlyContinue'
        }

        if ($request.Version) {
            $params['Version'] = $request.Version
        }

        $uninstallParams = @{ }

        $request.DynamicParameters |
        ConvertTo-Hashtable -Hashtable $uninstallParams -IsBound

        # Issue to get PassThru parameter added
        # https://github.com/PowerShell/PSResourceGet/issues/667

        # Prerelease parameter causes it to silently fail
        # https://github.com/PowerShell/PSResourceGet/issues/842
        Get-InstalledPSResource @params |
        ForEach-Object {
            try {
                $_ | Uninstall-PSResource @uninstallParams -ErrorAction Stop
                $_ | Write-Package -Request $request
            }
            catch {
                $_
            }
        }
    }
    #endregion

    #region UpdatePackage
    [void] UpdatePackage([PackageRequest] $request) {
        $params = @{
            Prerelease  = $request.Prerelease
        }

        if ($request.Version) {
            $params['Version'] = $request.Version
        }

        if ($request.Source) {
            $params['Repository'] = $request.Source
        }

        $updateParams = @{ }

        $request.DynamicParameters |
        ConvertTo-Hashtable -Hashtable $updateParams -IsBound

        # Find-PSResource pipeline input
        # https://github.com/PowerShell/PSResourceGet/issues/666
        Get-InstalledPSResource -Name $request.Name -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty Name -Unique |
        Find-PSResource @params -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty Name -Unique |
        Update-PSResource @params @updateParams -TrustRepository -PassThru |
        Write-Package -Request $request
    }
    #endregion

    #region PublishPackage
    [void] PublishPackage([PackageRequest] $request) {
        $params = @{
            Path = $request.Path
        }

        if ($request.Source) {
            $params['Repository'] = $request.Source
        }

        $request.DynamicParameters |
        ConvertTo-Hashtable -Hashtable $params -IsBound

        try {
            # PassThru parameter
            # https://github.com/PowerShell/PSResourceGet/issues/718
            Publish-PSResource @params -ErrorAction Stop

            $params.Remove('Path')
            $params['Name'] = Get-Item -Path $request.Path |
            Select-Object -ExpandProperty BaseName

            Find-PSResource @params |
            Get-Latest |
            Write-Package -Request $request
        }
        catch {
            throw $_
        }
    }
    #endregion

    #region Source
    [void] GetSource([SourceRequest] $sourceRequest) {
        Get-PSResourceRepository -Name $sourceRequest.Name |
        Write-Source -SourceRequest $sourceRequest
    }

    [void] SetSource([SourceRequest] $sourceRequest) {
        $params = @{
            PassThru = $true
        }

        if ($sourceRequest.Location) {
            $params.Uri = $sourceRequest.Location
        }

        if ($null -ne $sourceRequest.Trusted) {
            $params.Trusted = $sourceRequest.Trusted
        }

        $sourceRequest.DynamicParameters |
        ConvertTo-Hashtable -Hashtable $params -IsBound

        Get-PSResourceRepository -Name $sourceRequest.Name |
        Set-PSResourceRepository @params |
        Write-Source -SourceRequest $sourceRequest
    }

    [void] RegisterSource([SourceRequest] $sourceRequest) {
        $params = @{
            Trusted  = $sourceRequest.Trusted
            PassThru = $true
        }

        if ($sourceRequest.DynamicParameters.PSGallery) {
            $params['PSGallery'] = $true
        }
        else {
            $params['Name'] = $sourceRequest.Name
            $params['Uri'] = $sourceRequest.Location
        }

        $sourceRequest.DynamicParameters |
        ConvertTo-Hashtable -Hashtable $params -Exclude 'PSGallery' -IsBound

        Register-PSResourceRepository @params |
        Write-Source -SourceRequest $sourceRequest
    }

    [void] UnregisterSource([SourceRequest] $sourceRequest) {
        Get-PSResourceRepository -Name $sourceRequest.Name |
        Unregister-PSResourceRepository -PassThru |
        Write-Source -SourceRequest $sourceRequest
    }
    #endregion

    [object] GetDynamicParameters([string] $commandName) {
        return $(switch ($commandName) {
            'Get-Package' { return [GetPackageDynamicParameters]::new() }
            'Find-Package' { return [FindPackageDynamicParameters]::new() }
            'Install-Package' { return [InstallPackageDynamicParameters]::new() }
            'Publish-Package' { return [PublishPackageDynamicParameters]::new() }
            'Save-Package' { return [SavePackageDynamicParameters]::new() }
            'Uninstall-Package' { return [UninstallPackageDynamicParameters]::new() }
            'Update-Package' { return [UpdatePackageDynamicParameters]::new() }
            'Set-PackageSource' { return [SetPackageSourceDynamicParameters]::new() }
            'Register-PackageSource' { return [RegisterPackageSourceDynamicParameters]::new() }
            default { return $null }
        })
    }
}

class GetPackageDynamicParameters {
    [Parameter()]
    [string] $Path

    [Parameter()]
    [ScopeType] $Scope
}

class FindPackageDynamicParameters {
    [Parameter()]
    [switch] $Credential

    [Parameter()]
    [string[]] $Tag

    [Parameter()]
    [ResourceType] $Type

    [Parameter()]
    [switch] $Latest

    [Parameter()]
    [switch] $IncludeDependencies
}

class PublishPackageDynamicParameters {
    [Parameter()]
    [string] $ApiKey

    [Parameter()]
    [switch] $Credential

    [Parameter()]
    [string] $DestinationPath

    [Parameter()]
    [switch] $SkipDependenciesCheck

    [Parameter()]
    [switch] $SkipModuleManifestValidate

    [Parameter()]
    [uri] $Proxy

    [Parameter()]
    [pscredential] $ProxyCredential
}

class InstallDynamicParameters {
    [Parameter()]
    [switch] $AuthenticodeCheck

    [Parameter()]
    [switch] $Credential

    [Parameter()]
    [switch] $SkipDependencyCheck

    [Parameter()]
    [string] $TemporaryPath
}

class InstallUpdateDynamicParameters : InstallDynamicParameters {
    [Parameter()]
    [switch] $AcceptLicense

    [Parameter()]
    [ScopeType] $Scope
}

class InstallPackageDynamicParameters : InstallUpdateDynamicParameters {
    [Parameter()]
    [switch] $Reinstall

    # Install-PSResource -NoClobber fails
    # https://github.com/PowerShell/PSResourceGet/issues/946
    # [Parameter()]
    # [switch] $NoClobber
}

class SavePackageDynamicParameters : InstallDynamicParameters {
    # Pipeline input fails with -AsNupkg
    # https://github.com/PowerShell/PSResourceGet/issues/948
    # [Parameter()]
    # [switch] $AsNupkg

    # Pipeline input fails with -IncludeXml
    # https://github.com/PowerShell/PSResourceGet/issues/949
    # [Parameter()]
    # [switch] $IncludeXml
}

class UninstallPackageDynamicParameters {
    [Parameter()]
    [switch] $SkipDependencyCheck

    [Parameter()]
    [ScopeType] $Scope
}

class UpdatePackageDynamicParameters : InstallUpdateDynamicParameters {
    [Parameter()]
    [switch] $Force
}

class SetPackageSourceDynamicParameters {
    [Parameter()]
    [int] $Priority

    [Parameter()]
    [PSCredentialInfo] $CredentialInfo
}

class RegisterPackageSourceDynamicParameters : SetPackageSourceDynamicParameters {
    [Parameter(ParameterSetName = 'PSGallery')]
    [switch] $PSGallery
}

[guid] $id = 'c9a39544-274b-4935-9cad-7423e8c47e6b'
[PackageProviderManager]::RegisterProvider($id, [PSResourceGetProvider], $MyInvocation.MyCommand.ScriptBlock.Module)

$MyInvocation.MyCommand.ScriptBlock.Module.OnRemove = {
    [PackageProviderManager]::UnregisterProvider($id)
}

function ConvertTo-Hashtable {
    [CmdletBinding()]
    [OutputType([hashtable])]
    [Diagnostics.CodeAnalysis.SuppressMessageAttribute('PSUseSingularNouns', '')]
    param (
        [Parameter(Position = 0,
            ValueFromPipeline,
            ValueFromPipelineByPropertyName)]
        [object]
        $InputObject,

        [Parameter()]
        [hashtable]
        $Hashtable = @{ },

        [Parameter()]
        [string[]]
        $Exclude,

        [Parameter()]
        [switch]
        $IsBound
    )

    process {
        if ($null -eq $InputObject) {
            return
        }

        $properties = $InputObject |
            Get-Member -MemberType Properties |
            Where-Object Name -notin $Exclude |
            Select-Object -ExpandProperty Name

        foreach ($property in $properties) {
            if ($IsBound -and -not $InputObject.$property) {
                continue
            }

            $Hashtable[$property] = $InputObject.$property
        }

        $Hashtable
    }
}

function Get-Latest {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory,
            ValueFromPipeline)]
        [PSResourceInfo]
        $Resource
    )

    begin {
        $resources = [List[PSResourceInfo]]::new()
    }

    process {
        $resources.Add($resource)
    }

    end {
        $resources |
        Group-Object -Property Name |
        ForEach-Object {
            # PSResourceGet returns the latest as the first object
            $_.Group | Select-Object -First 1
        }
    }
}

function Write-Source {
    [CmdletBinding()]
    param (
        [Parameter(Mandatory,
            ValueFromPipeline)]
        [PSRepositoryInfo]
        $Source,

        [Parameter(Mandatory)]
        [SourceRequest]
        $SourceRequest
    )

    process {
        $sourceInfo = [PackageSourceInfo]::new($Source.Name,
                                           $Source.Uri,
                                           [bool]::Parse($Source.Trusted),
                                           @{ Priority = $Source.Priority
                                              CredentialInfo = $Source.CredentialInfo },
                                            $SourceRequest.ProviderInfo)
        $SourceRequest.WriteSource($sourceInfo)
    }
}

function Write-Package {
    [CmdletBinding()]
    param (
        [Parameter(Mandatory,
            ValueFromPipeline)]
        [PSResourceInfo]
        $Resource,

        [Parameter(Mandatory)]
        [PackageRequest]
        $Request
    )

    begin {
        $sources = Get-PackageSource -Provider AnyPackage.PSResourceGet\PSResourceGet
    }

    process {
        $ht = ConvertTo-Hashtable $resource

        $deps = [List[PackageDependency]]::new()
        foreach ($dep in $resource.Dependencies) {
            $versionRange = [PackageVersionRange]::new($dep.VersionRange, $true)
            $dependency = [PackageDependency]::new($dep.Name, $versionRange)
            $deps.Add($dependency)
        }

        $source = $sources |
        Where-Object Name -eq $resource.Repository

        # Blank RepositorySourceLocation
        # https://github.com/PowerShell/PSResourceGet/issues/1052
        if (-not $source -and $resource.RepositorySourceLocation) {
            $source = [PackageSourceInfo]::new($resource.Repository, $resource.RepositorySourceLocation, $false, $Request.ProviderInfo)
        }

        if ($resource.Prerelease) {
            $version = "{0}-{1}" -f $resource.Version, $resource.Prerelease
        }
        else {
            $version = $resource.Version
        }

        $package = [PackageInfo]::new($resource.Name, $version, $source, $resource.Description, $deps, $ht, $Request.ProviderInfo)
        $Request.WritePackage($package)
    }
}

# SIG # Begin signature block
# MIIlyAYJKoZIhvcNAQcCoIIluTCCJbUCAQExDzANBglghkgBZQMEAgEFADB5Bgor
# BgEEAYI3AgEEoGswaTA0BgorBgEEAYI3AgEeMCYCAwEAAAQQH8w7YFlLCE63JNLG
# KX7zUQIBAAIBAAIBAAIBAAIBADAxMA0GCWCGSAFlAwQCAQUABCDbvAkf2zvpyTZn
# VH5IdHlK2Fe0o3LHKaVh4kq1zPXPcqCCHzQwggVvMIIEV6ADAgECAhBI/JO0YFWU
# jTanyYqJ1pQWMA0GCSqGSIb3DQEBDAUAMHsxCzAJBgNVBAYTAkdCMRswGQYDVQQI
# DBJHcmVhdGVyIE1hbmNoZXN0ZXIxEDAOBgNVBAcMB1NhbGZvcmQxGjAYBgNVBAoM
# EUNvbW9kbyBDQSBMaW1pdGVkMSEwHwYDVQQDDBhBQUEgQ2VydGlmaWNhdGUgU2Vy
# dmljZXMwHhcNMjEwNTI1MDAwMDAwWhcNMjgxMjMxMjM1OTU5WjBWMQswCQYDVQQG
# EwJHQjEYMBYGA1UEChMPU2VjdGlnbyBMaW1pdGVkMS0wKwYDVQQDEyRTZWN0aWdv
# IFB1YmxpYyBDb2RlIFNpZ25pbmcgUm9vdCBSNDYwggIiMA0GCSqGSIb3DQEBAQUA
# A4ICDwAwggIKAoICAQCN55QSIgQkdC7/FiMCkoq2rjaFrEfUI5ErPtx94jGgUW+s
# hJHjUoq14pbe0IdjJImK/+8Skzt9u7aKvb0Ffyeba2XTpQxpsbxJOZrxbW6q5KCD
# J9qaDStQ6Utbs7hkNqR+Sj2pcaths3OzPAsM79szV+W+NDfjlxtd/R8SPYIDdub7
# P2bSlDFp+m2zNKzBenjcklDyZMeqLQSrw2rq4C+np9xu1+j/2iGrQL+57g2extme
# me/G3h+pDHazJyCh1rr9gOcB0u/rgimVcI3/uxXP/tEPNqIuTzKQdEZrRzUTdwUz
# T2MuuC3hv2WnBGsY2HH6zAjybYmZELGt2z4s5KoYsMYHAXVn3m3pY2MeNn9pib6q
# RT5uWl+PoVvLnTCGMOgDs0DGDQ84zWeoU4j6uDBl+m/H5x2xg3RpPqzEaDux5mcz
# mrYI4IAFSEDu9oJkRqj1c7AGlfJsZZ+/VVscnFcax3hGfHCqlBuCF6yH6bbJDoEc
# QNYWFyn8XJwYK+pF9e+91WdPKF4F7pBMeufG9ND8+s0+MkYTIDaKBOq3qgdGnA2T
# OglmmVhcKaO5DKYwODzQRjY1fJy67sPV+Qp2+n4FG0DKkjXp1XrRtX8ArqmQqsV/
# AZwQsRb8zG4Y3G9i/qZQp7h7uJ0VP/4gDHXIIloTlRmQAOka1cKG8eOO7F/05QID
# AQABo4IBEjCCAQ4wHwYDVR0jBBgwFoAUoBEKIz6W8Qfs4q8p74Klf9AwpLQwHQYD
# VR0OBBYEFDLrkpr/NZZILyhAQnAgNpFcF4XmMA4GA1UdDwEB/wQEAwIBhjAPBgNV
# HRMBAf8EBTADAQH/MBMGA1UdJQQMMAoGCCsGAQUFBwMDMBsGA1UdIAQUMBIwBgYE
# VR0gADAIBgZngQwBBAEwQwYDVR0fBDwwOjA4oDagNIYyaHR0cDovL2NybC5jb21v
# ZG9jYS5jb20vQUFBQ2VydGlmaWNhdGVTZXJ2aWNlcy5jcmwwNAYIKwYBBQUHAQEE
# KDAmMCQGCCsGAQUFBzABhhhodHRwOi8vb2NzcC5jb21vZG9jYS5jb20wDQYJKoZI
# hvcNAQEMBQADggEBABK/oe+LdJqYRLhpRrWrJAoMpIpnuDqBv0WKfVIHqI0fTiGF
# OaNrXi0ghr8QuK55O1PNtPvYRL4G2VxjZ9RAFodEhnIq1jIV9RKDwvnhXRFAZ/ZC
# J3LFI+ICOBpMIOLbAffNRk8monxmwFE2tokCVMf8WPtsAO7+mKYulaEMUykfb9gZ
# pk+e96wJ6l2CxouvgKe9gUhShDHaMuwV5KZMPWw5c9QLhTkg4IUaaOGnSDip0TYl
# d8GNGRbFiExmfS9jzpjoad+sPKhdnckcW67Y8y90z7h+9teDnRGWYpquRRPaf9xH
# +9/DUp/mBlXpnYzyOmJRvOwkDynUWICE5EV7WtgwggW2MIIEHqADAgECAhEApPLK
# EVUizMqDeJHsqFBBojANBgkqhkiG9w0BAQwFADBUMQswCQYDVQQGEwJHQjEYMBYG
# A1UEChMPU2VjdGlnbyBMaW1pdGVkMSswKQYDVQQDEyJTZWN0aWdvIFB1YmxpYyBD
# b2RlIFNpZ25pbmcgQ0EgUjM2MB4XDTIyMTIwNjAwMDAwMFoXDTI1MTIwNTIzNTk1
# OVowTDELMAkGA1UEBhMCVVMxDzANBgNVBAgMBkthbnNhczEVMBMGA1UECgwMVGhv
# bWFzIE5pZXRvMRUwEwYDVQQDDAxUaG9tYXMgTmlldG8wggGiMA0GCSqGSIb3DQEB
# AQUAA4IBjwAwggGKAoIBgQDKp+8DxaXlIDZh+gMApqRZ4hD4IDTdRkUEZZqSnUwx
# QnD5k8VpbDeqrEkmww2TKUeOWQbSRMT70T/8R8+ld2GrwzLDQ83k5mrGXIXSXCHR
# iLIZUnLmVjDtf/4FXTEni+acu8dddbCS0GAAzDfnINFgVRQR9GdoaYLqoipRVpLV
# RBzbeR2gSCtzwmpuX1d4NR58NvfUkfzNxy0kaLfqamHl9ae0JHyGvyzrHgOUyt2t
# tA/FidNo8KudwGau/gfyko5egOAURpEqgJHrcaekTVio+GRQs2IFNHIvNnfF9Rm7
# kn5wPZuxWL4UaV5xGyYWLupny3Lpp1n+XlVg6UgYZX25BWwbdbfLvsDPHnlbPB2L
# 0WgCCeG6ZOZjB2dmFaYHhwozRzcvX0FLoYXv1/Vo9QviUTm2QIqb/gaxt3xl/rtc
# CZOjly518iHNR2f1ClS+dPiD7KO5r2owmUsaMZiPVeMnD8/dKT8c9jPhyRBntbX9
# V6hoRXD6J2mf5SKSql8pwC8CAwEAAaOCAYkwggGFMB8GA1UdIwQYMBaAFA8qyyCH
# KLjsb0iuK1SmKaoXpM0MMB0GA1UdDgQWBBQOV7tpbOOE2AnSg3DwNoU56VePWzAO
# BgNVHQ8BAf8EBAMCB4AwDAYDVR0TAQH/BAIwADATBgNVHSUEDDAKBggrBgEFBQcD
# AzBKBgNVHSAEQzBBMDUGDCsGAQQBsjEBAgEDAjAlMCMGCCsGAQUFBwIBFhdodHRw
# czovL3NlY3RpZ28uY29tL0NQUzAIBgZngQwBBAEwSQYDVR0fBEIwQDA+oDygOoY4
# aHR0cDovL2NybC5zZWN0aWdvLmNvbS9TZWN0aWdvUHVibGljQ29kZVNpZ25pbmdD
# QVIzNi5jcmwweQYIKwYBBQUHAQEEbTBrMEQGCCsGAQUFBzAChjhodHRwOi8vY3J0
# LnNlY3RpZ28uY29tL1NlY3RpZ29QdWJsaWNDb2RlU2lnbmluZ0NBUjM2LmNydDAj
# BggrBgEFBQcwAYYXaHR0cDovL29jc3Auc2VjdGlnby5jb20wDQYJKoZIhvcNAQEM
# BQADggGBADWsCefpJbT4oKIh1SXIR4hnfGN/YqI6g3aFIntNgoiurd5uxLkow2WS
# pfaCiXjWjMubDpBvynVvaBsRfcrwT0WGBTwz4miuITPKKkIXYIVb5dCf33ghMJ4U
# D+zHP73ioUtDV545Yeb5WVLrPN8ZCC++u0kX+jck30w56LCvng6gDpPHU/KNroQx
# ENjGpcycTf7Gq9tkcEVbGersD6R64NhI6r8uDH6l0s5NMep1x4yTs0MBPmlB6ZHK
# +88YGDVdfTSYbLpQuvmLkEMHNaPOL0YyTjJJbeaHvGuTfqQb17HDLFJGd70CKrQu
# mvcICrJM9il3B+bNsSKjTLQtGbp5JdJ5paUahybiJKyZlDw5QPRrFEnwHiWaTI/9
# zfRciZyX4kYnLkPpp8rlZFXBqfIzf0gRhgCjVVZoMwZHWqyZNL7gS4C6uvEn2t/3
# BqM7548OuoPLH7W07orz8T7iP7aNYtJpAttZOhAbqB2EKoY3qcKClqKOMQGvc12/
# 16mAKE7E+TCCBhowggQCoAMCAQICEGIdbQxSAZ47kHkVIIkhHAowDQYJKoZIhvcN
# AQEMBQAwVjELMAkGA1UEBhMCR0IxGDAWBgNVBAoTD1NlY3RpZ28gTGltaXRlZDEt
# MCsGA1UEAxMkU2VjdGlnbyBQdWJsaWMgQ29kZSBTaWduaW5nIFJvb3QgUjQ2MB4X
# DTIxMDMyMjAwMDAwMFoXDTM2MDMyMTIzNTk1OVowVDELMAkGA1UEBhMCR0IxGDAW
# BgNVBAoTD1NlY3RpZ28gTGltaXRlZDErMCkGA1UEAxMiU2VjdGlnbyBQdWJsaWMg
# Q29kZSBTaWduaW5nIENBIFIzNjCCAaIwDQYJKoZIhvcNAQEBBQADggGPADCCAYoC
# ggGBAJsrnVP6NT+OYAZDasDP9X/2yFNTGMjO02x+/FgHlRd5ZTMLER4ARkZsQ3hA
# yAKwktlQqFZOGP/I+rLSJJmFeRno+DYDY1UOAWKA4xjMHY4qF2p9YZWhhbeFpPb0
# 9JNqFiTCYy/Rv/zedt4QJuIxeFI61tqb7/foXT1/LW2wHyN79FXSYiTxcv+18Irp
# w+5gcTbXnDOsrSHVJYdPE9s+5iRF2Q/TlnCZGZOcA7n9qudjzeN43OE/TpKF2dGq
# 1mVXn37zK/4oiETkgsyqA5lgAQ0c1f1IkOb6rGnhWqkHcxX+HnfKXjVodTmmV52L
# 2UIFsf0l4iQ0UgKJUc2RGarhOnG3B++OxR53LPys3J9AnL9o6zlviz5pzsgfrQH4
# lrtNUz4Qq/Va5MbBwuahTcWk4UxuY+PynPjgw9nV/35gRAhC3L81B3/bIaBb659+
# Vxn9kT2jUztrkmep/aLb+4xJbKZHyvahAEx2XKHafkeKtjiMqcUf/2BG935A591G
# sllvWwIDAQABo4IBZDCCAWAwHwYDVR0jBBgwFoAUMuuSmv81lkgvKEBCcCA2kVwX
# heYwHQYDVR0OBBYEFA8qyyCHKLjsb0iuK1SmKaoXpM0MMA4GA1UdDwEB/wQEAwIB
# hjASBgNVHRMBAf8ECDAGAQH/AgEAMBMGA1UdJQQMMAoGCCsGAQUFBwMDMBsGA1Ud
# IAQUMBIwBgYEVR0gADAIBgZngQwBBAEwSwYDVR0fBEQwQjBAoD6gPIY6aHR0cDov
# L2NybC5zZWN0aWdvLmNvbS9TZWN0aWdvUHVibGljQ29kZVNpZ25pbmdSb290UjQ2
# LmNybDB7BggrBgEFBQcBAQRvMG0wRgYIKwYBBQUHMAKGOmh0dHA6Ly9jcnQuc2Vj
# dGlnby5jb20vU2VjdGlnb1B1YmxpY0NvZGVTaWduaW5nUm9vdFI0Ni5wN2MwIwYI
# KwYBBQUHMAGGF2h0dHA6Ly9vY3NwLnNlY3RpZ28uY29tMA0GCSqGSIb3DQEBDAUA
# A4ICAQAG/4Lhd2M2bnuhFSCbE/8E/ph1RGHDVpVx0ZE/haHrQECxyNbgcv2FymQ5
# PPmNS6Dah66dtgCjBsULYAor5wxxcgEPRl05pZOzI3IEGwwsepp+8iGsLKaVpL3z
# 5CmgELIqmk/Q5zFgR1TSGmxqoEEhk60FqONzDn7D8p4W89h8sX+V1imaUb693TGq
# Wp3T32IKGfIgy9jkd7GM7YCa2xulWfQ6E1xZtYNEX/ewGnp9ZeHPsNwwviJMBZL4
# xVd40uPWUnOJUoSiugaz0yWLODRtQxs5qU6E58KKmfHwJotl5WZ7nIQuDT0mWjwE
# x7zSM7fs9Tx6N+Q/3+49qTtUvAQsrEAxwmzOTJ6Jp6uWmHCgrHW4dHM3ITpvG5Ip
# y62KyqYovk5O6cC+040Si15KJpuQ9VJnbPvqYqfMB9nEKX/d2rd1Q3DiuDexMKCC
# QdJGpOqUsxLuCOuFOoGbO7Uv3RjUpY39jkkp0a+yls6tN85fJe+Y8voTnbPU1knp
# y24wUFBkfenBa+pRFHwCBB1QtS+vGNRhsceP3kSPNrrfN2sRzFYsNfrFaWz8YOdU
# 254qNZQfd9O/VjxZ2Gjr3xgANHtM3HxfzPYF6/pKK8EE4dj66qKKtm2DTL1KFCg/
# OYJyfrdLJq1q2/HXntgr2GVw+ZWhrWgMTn8v1SjZsLlrgIfZHDCCBuwwggTUoAMC
# AQICEDAPb6zdZph0fKlGNqd4LbkwDQYJKoZIhvcNAQEMBQAwgYgxCzAJBgNVBAYT
# AlVTMRMwEQYDVQQIEwpOZXcgSmVyc2V5MRQwEgYDVQQHEwtKZXJzZXkgQ2l0eTEe
# MBwGA1UEChMVVGhlIFVTRVJUUlVTVCBOZXR3b3JrMS4wLAYDVQQDEyVVU0VSVHJ1
# c3QgUlNBIENlcnRpZmljYXRpb24gQXV0aG9yaXR5MB4XDTE5MDUwMjAwMDAwMFoX
# DTM4MDExODIzNTk1OVowfTELMAkGA1UEBhMCR0IxGzAZBgNVBAgTEkdyZWF0ZXIg
# TWFuY2hlc3RlcjEQMA4GA1UEBxMHU2FsZm9yZDEYMBYGA1UEChMPU2VjdGlnbyBM
# aW1pdGVkMSUwIwYDVQQDExxTZWN0aWdvIFJTQSBUaW1lIFN0YW1waW5nIENBMIIC
# IjANBgkqhkiG9w0BAQEFAAOCAg8AMIICCgKCAgEAyBsBr9ksfoiZfQGYPyCQvZyA
# IVSTuc+gPlPvs1rAdtYaBKXOR4O168TMSTTL80VlufmnZBYmCfvVMlJ5LsljwhOb
# toY/AQWSZm8hq9VxEHmH9EYqzcRaydvXXUlNclYP3MnjU5g6Kh78zlhJ07/zObu5
# pCNCrNAVw3+eolzXOPEWsnDTo8Tfs8VyrC4Kd/wNlFK3/B+VcyQ9ASi8Dw1Ps5EB
# jm6dJ3VV0Rc7NCF7lwGUr3+Az9ERCleEyX9W4L1GnIK+lJ2/tCCwYH64TfUNP9vQ
# 6oWMilZx0S2UTMiMPNMUopy9Jv/TUyDHYGmbWApU9AXn/TGs+ciFF8e4KRmkKS9G
# 493bkV+fPzY+DjBnK0a3Na+WvtpMYMyou58NFNQYxDCYdIIhz2JWtSFzEh79qsoI
# WId3pBXrGVX/0DlULSbuRRo6b83XhPDX8CjFT2SDAtT74t7xvAIo9G3aJ4oG0paH
# 3uhrDvBbfel2aZMgHEqXLHcZK5OVmJyXnuuOwXhWxkQl3wYSmgYtnwNe/YOiU2fK
# sfqNoWTJiJJZy6hGwMnypv99V9sSdvqKQSTUG/xypRSi1K1DHKRJi0E5FAMeKfob
# pSKupcNNgtCN2mu32/cYQFdz8HGj+0p9RTbB942C+rnJDVOAffq2OVgy728YUInX
# T50zvRq1naHelUF6p4MCAwEAAaOCAVowggFWMB8GA1UdIwQYMBaAFFN5v1qqK0rP
# VIDh2JvAnfKyA2bLMB0GA1UdDgQWBBQaofhhGSAPw0F3RSiO0TVfBhIEVTAOBgNV
# HQ8BAf8EBAMCAYYwEgYDVR0TAQH/BAgwBgEB/wIBADATBgNVHSUEDDAKBggrBgEF
# BQcDCDARBgNVHSAECjAIMAYGBFUdIAAwUAYDVR0fBEkwRzBFoEOgQYY/aHR0cDov
# L2NybC51c2VydHJ1c3QuY29tL1VTRVJUcnVzdFJTQUNlcnRpZmljYXRpb25BdXRo
# b3JpdHkuY3JsMHYGCCsGAQUFBwEBBGowaDA/BggrBgEFBQcwAoYzaHR0cDovL2Ny
# dC51c2VydHJ1c3QuY29tL1VTRVJUcnVzdFJTQUFkZFRydXN0Q0EuY3J0MCUGCCsG
# AQUFBzABhhlodHRwOi8vb2NzcC51c2VydHJ1c3QuY29tMA0GCSqGSIb3DQEBDAUA
# A4ICAQBtVIGlM10W4bVTgZF13wN6MgstJYQRsrDbKn0qBfW8Oyf0WqC5SVmQKWxh
# y7VQ2+J9+Z8A70DDrdPi5Fb5WEHP8ULlEH3/sHQfj8ZcCfkzXuqgHCZYXPO0EQ/V
# 1cPivNVYeL9IduFEZ22PsEMQD43k+ThivxMBxYWjTMXMslMwlaTW9JZWCLjNXH8B
# lr5yUmo7Qjd8Fng5k5OUm7Hcsm1BbWfNyW+QPX9FcsEbI9bCVYRm5LPFZgb289ZL
# Xq2jK0KKIZL+qG9aJXBigXNjXqC72NzXStM9r4MGOBIdJIct5PwC1j53BLwENrXn
# d8ucLo0jGLmjwkcd8F3WoXNXBWiap8k3ZR2+6rzYQoNDBaWLpgn/0aGUpk6qPQn1
# BWy30mRa2Coiwkud8TleTN5IPZs0lpoJX47997FSkc4/ifYcobWpdR9xv1tDXWU9
# UIFuq/DQ0/yysx+2mZYm9Dx5i1xkzM3uJ5rloMAMcofBbk1a0x7q8ETmMm8c6xdO
# lMN4ZSA7D0GqH+mhQZ3+sbigZSo04N6o+TzmwTC7wKBjLPxcFgCo0MR/6hGdHgbG
# pm0yXbQ4CStJB6r97DDa8acvz7f9+tCjhNknnvsBZne5VhDhIG7GrrH5trrINV0z
# do7xfCAMKneutaIChrop7rRaALGMq+P5CslUXdS5anSevUiumDCCBvUwggTdoAMC
# AQICEDlMJeF8oG0nqGXiO9kdItQwDQYJKoZIhvcNAQEMBQAwfTELMAkGA1UEBhMC
# R0IxGzAZBgNVBAgTEkdyZWF0ZXIgTWFuY2hlc3RlcjEQMA4GA1UEBxMHU2FsZm9y
# ZDEYMBYGA1UEChMPU2VjdGlnbyBMaW1pdGVkMSUwIwYDVQQDExxTZWN0aWdvIFJT
# QSBUaW1lIFN0YW1waW5nIENBMB4XDTIzMDUwMzAwMDAwMFoXDTM0MDgwMjIzNTk1
# OVowajELMAkGA1UEBhMCR0IxEzARBgNVBAgTCk1hbmNoZXN0ZXIxGDAWBgNVBAoT
# D1NlY3RpZ28gTGltaXRlZDEsMCoGA1UEAwwjU2VjdGlnbyBSU0EgVGltZSBTdGFt
# cGluZyBTaWduZXIgIzQwggIiMA0GCSqGSIb3DQEBAQUAA4ICDwAwggIKAoICAQCk
# kyhSS88nh3akKRyZOMDnDtTRHOxoywFk5IrNd7BxZYK8n/yLu7uVmPslEY5aiAlm
# ERRYsroiW+b2MvFdLcB6og7g4FZk7aHlgSByIGRBbMfDCPrzfV3vIZrCftcsw7oR
# mB780yAIQrNfv3+IWDKrMLPYjHqWShkTXKz856vpHBYusLA4lUrPhVCrZwMlobs4
# 6Q9vqVqakSgTNbkf8z3hJMhrsZnoDe+7TeU9jFQDkdD8Lc9VMzh6CRwH0SLgY4an
# vv3Sg3MSFJuaTAlGvTS84UtQe3LgW/0Zux88ahl7brstRCq+PEzMrIoEk8ZXhqBz
# NiuBl/obm36Ih9hSeYn+bnc317tQn/oYJU8T8l58qbEgWimro0KHd+D0TAJI3Vil
# U6ajoO0ZlmUVKcXtMzAl5paDgZr2YGaQWAeAzUJ1rPu0kdDF3QFAaraoEO72jXq3
# nnWv06VLGKEMn1ewXiVHkXTNdRLRnG/kXg2b7HUm7v7T9ZIvUoXo2kRRKqLMAMqH
# ZkOjGwDvorWWnWKtJwvyG0rJw5RCN4gghKiHrsO6I3J7+FTv+GsnsIX1p0OF2Cs5
# dNtadwLRpPr1zZw9zB+uUdB7bNgdLRFCU3F0wuU1qi1SEtklz/DT0JFDEtcyfZhs
# 43dByP8fJFTvbq3GPlV78VyHOmTxYEsFT++5L+wJEwIDAQABo4IBgjCCAX4wHwYD
# VR0jBBgwFoAUGqH4YRkgD8NBd0UojtE1XwYSBFUwHQYDVR0OBBYEFAMPMciRKpO9
# Y/PRXU2kNA/SlQEYMA4GA1UdDwEB/wQEAwIGwDAMBgNVHRMBAf8EAjAAMBYGA1Ud
# JQEB/wQMMAoGCCsGAQUFBwMIMEoGA1UdIARDMEEwNQYMKwYBBAGyMQECAQMIMCUw
# IwYIKwYBBQUHAgEWF2h0dHBzOi8vc2VjdGlnby5jb20vQ1BTMAgGBmeBDAEEAjBE
# BgNVHR8EPTA7MDmgN6A1hjNodHRwOi8vY3JsLnNlY3RpZ28uY29tL1NlY3RpZ29S
# U0FUaW1lU3RhbXBpbmdDQS5jcmwwdAYIKwYBBQUHAQEEaDBmMD8GCCsGAQUFBzAC
# hjNodHRwOi8vY3J0LnNlY3RpZ28uY29tL1NlY3RpZ29SU0FUaW1lU3RhbXBpbmdD
# QS5jcnQwIwYIKwYBBQUHMAGGF2h0dHA6Ly9vY3NwLnNlY3RpZ28uY29tMA0GCSqG
# SIb3DQEBDAUAA4ICAQBMm2VY+uB5z+8VwzJt3jOR63dY4uu9y0o8dd5+lG3DIscE
# ld9laWETDPYMnvWJIF7Bh8cDJMrHpfAm3/j4MWUN4OttUVemjIRSCEYcKsLe8tqK
# RfO+9/YuxH7t+O1ov3pWSOlh5Zo5d7y+upFkiHX/XYUWNCfSKcv/7S3a/76TDOxt
# og3Mw/FuvSGRGiMAUq2X1GJ4KoR5qNc9rCGPcMMkeTqX8Q2jo1tT2KsAulj7NYBP
# XyhxbBlewoNykK7gxtjymfvqtJJlfAd8NUQdrVgYa2L73mzECqls0yFGcNwvjXVM
# I8JB0HqWO8NL3c2SJnR2XDegmiSeTl9O048P5RNPWURlS0Nkz0j4Z2e5Tb/MDbE6
# MNChPUitemXk7N/gAfCzKko5rMGk+al9NdAyQKCxGSoYIbLIfQVxGksnNqrgmByD
# defHfkuEQ81D+5CXdioSrEDBcFuZCkD6gG2UYXvIbrnIZ2ckXFCNASDeB/cB1Pgu
# Ec2dg+X4yiUcRD0n5bCGRyoLG4R2fXtoT4239xO07aAt7nMP2RC6nZksfNd1H48Q
# xJTmfiTllUqIjCfWhWYd+a5kdpHoSP7IVQrtKcMf3jimwBT7Mj34qYNiNsjDvgCH
# HKv6SkIciQPc9Vx8cNldeE7un14g5glqfCsIo0j1FfwET9/NIRx65fWOGtS5QDGC
# BeowggXmAgEBMGkwVDELMAkGA1UEBhMCR0IxGDAWBgNVBAoTD1NlY3RpZ28gTGlt
# aXRlZDErMCkGA1UEAxMiU2VjdGlnbyBQdWJsaWMgQ29kZSBTaWduaW5nIENBIFIz
# NgIRAKTyyhFVIszKg3iR7KhQQaIwDQYJYIZIAWUDBAIBBQCggYQwGAYKKwYBBAGC
# NwIBDDEKMAigAoAAoQKAADAZBgkqhkiG9w0BCQMxDAYKKwYBBAGCNwIBBDAcBgor
# BgEEAYI3AgELMQ4wDAYKKwYBBAGCNwIBFTAvBgkqhkiG9w0BCQQxIgQgyz9ngudU
# FfD0Pz1O38PGNq010WtrI1XLmhnNYYETFwowDQYJKoZIhvcNAQEBBQAEggGAlhNs
# dzes2cO4hNE+PGHPphh7tx0kmLNlFttqZQmDTGKXl87t6e2AcEpyUwjGy1KjE9G7
# XRyN8yxXtii4ismBARjbHCAK/aVfGFzj/V1tciXWxuTsi3ItoKO1QUbw6AS/zB4j
# 0ybyRmno6Xb3jtQ6N/Q4etpnvxpKDzEmzVxIno02scTkiVeHyhVTgRSChgmTxYJM
# Au6smSdB8ttMI7CprU/lI6HoO7khFW6dXQmaFWVDFzey0JJp+vGDrbVdzlY+0dGP
# AIGyZ6bJGVwDZ7XaLbQXHJPoMP9Kh/Lx+4q+axPk7iDdbPbtklZN2xnSYjkCuS4D
# Kf903GFD243xqYstLpPxG9kHXz/COwPznILJmlJnzAay9WFZTBcma95CBVHS+/Ab
# k/fM7uMAzDNYWg8kPx/9dSMdTUUcoxnL7lr/r+g7+H64pVKm8eCNe+I6DvcrS3lR
# N4YHk4AZpQp4FIsaxIynCjxQLB/VKXSLvtzWEua4pluTw4Sfu9dK2s/N4JFroYID
# SzCCA0cGCSqGSIb3DQEJBjGCAzgwggM0AgEBMIGRMH0xCzAJBgNVBAYTAkdCMRsw
# GQYDVQQIExJHcmVhdGVyIE1hbmNoZXN0ZXIxEDAOBgNVBAcTB1NhbGZvcmQxGDAW
# BgNVBAoTD1NlY3RpZ28gTGltaXRlZDElMCMGA1UEAxMcU2VjdGlnbyBSU0EgVGlt
# ZSBTdGFtcGluZyBDQQIQOUwl4XygbSeoZeI72R0i1DANBglghkgBZQMEAgIFAKB5
# MBgGCSqGSIb3DQEJAzELBgkqhkiG9w0BBwEwHAYJKoZIhvcNAQkFMQ8XDTIzMDcy
# NzIwMjEyNVowPwYJKoZIhvcNAQkEMTIEMPGuIewbk8+BNM/sVXV+89Go9jZm0prT
# GrC/W90ujW4Aem6lUXZRqCPnctYXYa419DANBgkqhkiG9w0BAQEFAASCAgApXK0Y
# 76iiNwDnxlGpbM5+H6p+pYZno/eY13GUmn728ZbyVHjnWEjWwO8MvlCMVZdpEUyc
# 8grtEb6t4NW5JvBkgJXD/M3gmJxweNkrZEwNsa0J1ybEopaL7nil6IE8+RwAyA0/
# aWP9CGA+V61ryFsglj/94TWH/f3k4kVGgj3+42oNqondPCeCjQXhgNOIaD99aqUx
# ws1BlwJ2XIAbtle0f8mk+oLQ9qS3SyGdKAy6T+MtLUApyz5yfu06QLCgrc6T/Ymr
# 6k4DWt8hKFkPgCZVJeleLGkSpZbUNsuzxTM1dzN9dVX2XTGtF0Qlg9VCyiZSDULJ
# nPUY982lMnlb8i5qFQa5bekKtGYjEdL9L714z4ITsHLvsc3HwsmoWPUbqgFu+Z1w
# g5ZYKeT+WEj6lyj29Xi9zHIVc4iLNtmu485yAvsMbEO4w7e6TXgCq7UT9LjB93FD
# c43SdcLLmrefEIr9iUNQCsjrM2bIJ260P739yL3/eP9TxAnJWAK7Yb6JIQrBGq1m
# jqIBzHEo/R5TMppzDMU+cSUYUMnMxE8NVaiTkhMnp6tcgWPKkmMjyDojKjXxoq4R
# 4qfGyo0SvZVlN85RYqqQh2kuJ1xgx6lagJB6kDfsupfykcbvfKbxtwisMnBi61GV
# 1yiTL5TGWXiwcSXgV/J8wvCD0huJUeH+8ibT0g==
# SIG # End signature block
