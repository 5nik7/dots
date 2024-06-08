# Copyright (c) Thomas Nieto - All Rights Reserved
# You may use, distribute and modify this code under the
# terms of the MIT license.

using module AnyPackage
using namespace AnyPackage.Provider
using namespace NuGet.Versioning
using namespace System.Management.Automation

[PackageProvider('Scoop')]
class ScoopProvider : PackageProvider, IFindPackage, IGetPackage,
    IInstallPackage, IUpdatePackage, IUninstallPackage, IGetSource, ISetSource {
    [PackageProviderInfo] Initialize([PackageProviderInfo] $providerInfo) {
        return [ScoopProviderInfo]::new($providerInfo)
    }

    [void] FindPackage([PackageRequest] $request) {
        Find-ScoopApp -Name $request.Name |
        Write-Package -Request $request -OfficialSources $this.ProviderInfo.OfficialSources
    }

    [void] GetPackage([PackageRequest] $request) {
        Get-ScoopApp -Name $request.Name |
        Write-Package -Request $request -OfficialSources $this.ProviderInfo.OfficialSources
    }

    [void] InstallPackage([PackageRequest] $request) {
        $installScoopAppParams = @{ }

        if ($request.DynamicParameters.Architecture) {
            $installScoopAppParams['Architecture'] = $request.DynamicParameters.Architecture
        }

        if ($request.DynamicParameters.SkipDependencies) {
            $installScoopAppParams['SkipDependencies'] = $request.DynamicParameters.SkipDependencies
        }

        if ($request.DynamicParameters.NoCache) {
            $installScoopAppParams['NoCache'] = $request.DynamicParameters.NoCache
        }

        if ($request.DynamicParameters.SkipHashCheck) {
            $installScoopAppParams['SkipHashCheck'] = $request.DynamicParameters.SkipHashCheck
        }

        if ($request.DynamicParameters.Scope -eq 'AllUsers') {
            $installScoopAppParams['Global'] = $true
        }

        $findPackageParameters = @{ Name = $request.Name }

        if ($request.Source) { $findPackageParameters['Bucket'] = $request.Source }

        Find-ScoopApp @findPackageParameters |
        Where-Object { $request.IsMatch([PackageVersion]$_.Version) } |
        Select-Object -Property Name |
        Install-ScoopApp @installScoopAppParams

        Get-ScoopApp -Name $request.Name |
        Write-Package -Request $request -OfficialSources $this.ProviderInfo.OfficialSources
    }

    [void] UpdatePackage([PackageRequest] $request) {
        $installScoopAppParams = @{ }

        if ($request.DynamicParameters.SkipDependencies) {
            $installScoopAppParams['SkipDependencies'] = $request.DynamicParameters.SkipDependencies
        }

        if ($request.DynamicParameters.NoCache) {
            $installScoopAppParams['NoCache'] = $request.DynamicParameters.NoCache
        }

        if ($request.DynamicParameters.SkipHashCheck) {
            $installScoopAppParams['SkipHashCheck'] = $request.DynamicParameters.SkipHashCheck
        }

        if ($request.DynamicParameters.Scope -eq 'AllUsers') {
            $installScoopAppParams['Global'] = $true
        }

        if ($request.DynamicParameters.Reinstall) {
            $installScoopAppParams['Force'] = $true
        }

        $getPackageParameters = @{ Name = $request.Name}
        $findPackageParameters = @{ }

        if ($request.Source) { $findPackageParameters['Bucket'] = $request.Source }

        Get-ScoopApp @getPackageParameters |
        Find-ScoopApp @findPackageParameters |
        Where-Object { $request.IsMatch([PackageVersion]$_.Version) } |
        Select-Object -Property Name |
        Update-ScoopApp @installScoopAppParams

        Get-ScoopApp -Name $request.Name |
        Write-Package -Request $request -OfficialSources $this.ProviderInfo.OfficialSources
    }

    [void] UninstallPackage([PackageRequest] $request) {
        $uninstallScoopAppParams = @{ }

        if ($request.DynamicParameters.RemoveData) {
            $uninstallScoopAppParams['Purge'] = $request.DynamicParameters.RemoveData
        }

        if ($request.DynamicParameters.Scope -eq 'AllUsers') {
            $uninstallScoopAppParams['Global'] = $true
        }

        $package = Get-ScoopApp -Name $request.Name |
        Where-Object { $request.IsMatch([PackageVersion]$_.Version) }

        $package | Uninstall-ScoopApp @uninstallScoopAppParams

        if (-not ($package | Get-ScoopApp)) {
            $package |
            Write-Package -Request $request -OfficialSources $this.PackageInfo.OfficialSources
        }
    }

    [void] GetSource([SourceRequest] $sourceRequest) {
        Get-ScoopBucket |
        Write-Source -Request $sourceRequest -OfficialSources $this.ProviderInfo.OfficialSources
    }

    [void] RegisterSource([SourceRequest] $sourceRequest) {
        if ($sourceRequest.Trusted) {
            throw 'Scoop provider does not support Trusted parameter.'
        }

        $registerBucketParams = @{
            Force = $sourceRequest.Force
        }

        if ($sourceRequest.Name) {
            $name = $sourceRequest.Name
            $registerBucketParams['Name'] = $sourceRequest.Name
            $registerBucketParams['Uri'] = $sourceRequest.Location
        }
        else {
            if (-not ($sourceRequest.DynamicParameters.Official -in $this.ProviderInfo.OfficialSources.Keys)) {
                throw "'$($sourceRequest.DynamicParameters.Official)' is not an official source."
            }

            $name = $sourceRequest.DynamicParameters.Official
            $registerBucketParams['Official'] = $sourceRequest.DynamicParameters.Official
        }

        if ((Get-ScoopBucket -Name $name) -and -not $sourceRequest.Force) {
            throw "Source '$name' already exists. Use -Force to recreate the source."
        }

        Register-ScoopBucket @registerBucketParams

        Get-ScoopBucket -Name $name |
        Write-Source -Request $sourceRequest -OfficialSources $this.ProviderInfo.OfficialSources
    }

    [void] SetSource([SourceRequest] $sourceRequest) {
        if ($sourceRequest.Trusted) {
            throw 'Scoop provider does not support Trusted parameter.'
        }

        Register-ScoopBucket -Name $sourceRequest.Name -Uri $sourceRequest.Location -Force

        $this.GetSource($sourceRequest)
    }

    [void] UnregisterSource([SourceRequest] $sourceRequest) {
        $source = Get-ScoopBucket -Name $sourceRequest.Name

        if (-not $source) { return }

        Unregister-ScoopBucket -Name $sourceRequest.Name

        $source |
        Write-Source -Request $sourceRequest -OfficialSources $this.ProviderInfo.OfficialSources
    }

    [object] GetDynamicParameters([string] $commandName) {
        return $(switch ($commandName) {
            'Register-PackageSource' { [RegisterPackageSourceDynamicParameters]::new() }
            'Install-Package' { [InstallPackageDynamicParameters]::new() }
            'Uninstall-Package' { [UninstallPackageDynamicParameters]::new() }
            'Update-Package' { [UpdatePackageDynamicParameters]::new() }
            default { $null }
        })
    }
}

class RegisterPackageSourceDynamicParameters {
    [Parameter(Mandatory,
        ParameterSetName = 'Official')]
    [ValidateNotNullOrEmpty()]
    [string]
    $Official
}

class ScopeDynamicParameters {
    [Parameter()]
    [ValidateSet('CurrentUser', 'AllUsers')]
    [string]
    $Scope = 'CurrentUser'
}

class OptionalDynamicParameters : ScopeDynamicParameters {
    [Parameter()]
    [switch]
    $SkipDependencies

    [Parameter()]
    [switch]
    $NoCache

    [Parameter()]
    [switch]
    $SkipHashCheck
}

class InstallPackageDynamicParameters : OptionalDynamicParameters {
    [Parameter()]
    [ValidateSet('32bit', '64bit', 'arm64')]
    [string]
    $Architecture
}

class UpdatePackageDynamicParameters : OptionalDynamicParameters {
    [Parameter()]
    [switch]
    $Reinstall
}

class UninstallPackageDynamicParameters : ScopeDynamicParameters {
    [Parameter()]
    [switch]
    $RemoveData
}

class ScoopProviderInfo : PackageProviderInfo {
    [hashtable] $OfficialSources

    ScoopProviderInfo([PackageProviderInfo] $providerInfo) : base($providerInfo) {
        $this.SetOfficialSources()
    }

    hidden [void] SetOfficialSources() {
        $path = Get-Command -Name Scoop |
        Select-Object -ExpandProperty Path |
        Split-Path |
        Split-Path |
        Join-Path -ChildPath apps\scoop\current\buckets.json

        $sources = Get-Content -Path $path |
        ConvertFrom-Json

        $keys = $sources |
        Get-Member -MemberType NoteProperty |
        Select-Object -ExpandProperty Name

        $ht = @{ }
        foreach ($key in $keys) {
            $ht[$key] = $sources.$key
        }

        $this.OfficialSources = $ht
    }
}

$ScriptBlock = {
    param($commandName, $parameterName, $wordToComplete, $commandAst, $fakeBoundParameters)

    # Suppress PSReviewUnusedParameter warning since suppressing it does not work.
    $null = $commandName, $parameterName, $commandAst, $fakeBoundParameters

    Get-PackageProvider -Name Scoop |
    Select-Object -ExpandProperty OfficialSources |
    Select-Object -ExpandProperty Keys |
    Where-Object Name -Like "$wordToComplete*" |
    ForEach-Object {
        [CompletionResult]::new($_)
    }
}

Register-ArgumentCompleter -CommandName Register-PackageSource -ParameterName Official -ScriptBlock $ScriptBlock

[guid] $id = '28111522-ea7a-4e8a-b598-85389c17f8be'
[PackageProviderManager]::RegisterProvider($id, [ScoopProvider], $MyInvocation.MyCommand.ScriptBlock.Module)

$MyInvocation.MyCommand.ScriptBlock.Module.OnRemove = {
    [PackageProviderManager]::UnregisterProvider($id)
}

function Write-Source {
    [CmdletBinding()]
    param (
        [Parameter(ValueFromPipelineByPropertyName)]
        [string]
        $Name,

        [Parameter(ValueFromPipelineByPropertyName)]
        [Alias('Source')]
        [string]
        $Location,

        [Parameter(ValueFromPipelineByPropertyName)]
        [datetime]
        $Updated,

        [Parameter(ValueFromPipelineByPropertyName)]
        [int]
        $Manifests,

        [Parameter(Mandatory)]
        [SourceRequest]
        $Request,

        [Parameter()]
        [hashtable]
        $OfficialSources
    )

    process {
        if ($Name -like $Request.Name) {
            $trusted = if ($Location -in $OfficialSources.Values) { $true } else { $false }
            $source = [PackageSourceInfo]::new($Name, $Location, $trusted, @{ Updated = $Updated; Manifests = $Manifests }, $Request.ProviderInfo)
            $Request.WriteSource($source)
        }
    }
}

function Write-Package {
    [CmdletBinding()]
    param (
        [Parameter(ValueFromPipelineByPropertyName)]
        [string]
        $Name,

        [Parameter(ValueFromPipelineByPropertyName)]
        [string]
        $Version,

        [Parameter(ValueFromPipelineByPropertyName)]
        [string]
        $Description,

        [Parameter(ValueFromPipelineByPropertyName)]
        [string]
        $Source,

        [Parameter(ValueFromPipelineByPropertyName)]
        [datetime]
        $Updated,

        [Parameter(ValueFromPipelineByPropertyName)]
        [string]
        $Info,

        [Parameter(Mandatory)]
        [PackageRequest]
        $Request,

        [Parameter()]
        [hashtable]
        $OfficialSources
    )

    begin {
        $buckets = Get-ScoopBucket
    }

    process {
        $metadata = @{ }
        if ($Updated) { $metadata['Updated'] = $Updated }
        if ($Info) { $metadata['Info'] = $Info }
        if ($Request.Source -and $Source -ne $Request.Source) { return }

        if ($Source -eq '<auto-generated>' -or (Test-Path -Path $Source)) {
            $sourceInfo = $null
        }
        else {
            $bucket = $buckets | Where-Object Name -eq $Source
            $trusted = if ($bucket.Source -in $OfficialSources.Values) { $true } else { $false }
            $sourceInfo = [PackageSourceInfo]::new($bucket.Name,
                                                   $bucket.Source,
                                                   $trusted,
                                                   @{ Updated = $bucket.Updated; Manifests = $bucket.Manifests },
                                                   $Request.ProviderInfo)
        }

        if ($Request.IsMatch($Name, $Version)) {
            $package = [PackageInfo]::new($Name, $Version, $sourceInfo, $Description, $null, $metadata, $Request.ProviderInfo)
            $Request.WritePackage($package)
        }
    }
}

# SIG # Begin signature block
# MIIlygYJKoZIhvcNAQcCoIIluzCCJbcCAQExDzANBglghkgBZQMEAgEFADB5Bgor
# BgEEAYI3AgEEoGswaTA0BgorBgEEAYI3AgEeMCYCAwEAAAQQH8w7YFlLCE63JNLG
# KX7zUQIBAAIBAAIBAAIBAAIBADAxMA0GCWCGSAFlAwQCAQUABCBLditZyMPglnvC
# Y5AM/rQEQhWqwcm0Xye7ZMQdUHDVIqCCHzUwggVvMIIEV6ADAgECAhBI/JO0YFWU
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
# do7xfCAMKneutaIChrop7rRaALGMq+P5CslUXdS5anSevUiumDCCBvYwggTeoAMC
# AQICEQCQOX+a0ko6E/K9kV8IOKlDMA0GCSqGSIb3DQEBDAUAMH0xCzAJBgNVBAYT
# AkdCMRswGQYDVQQIExJHcmVhdGVyIE1hbmNoZXN0ZXIxEDAOBgNVBAcTB1NhbGZv
# cmQxGDAWBgNVBAoTD1NlY3RpZ28gTGltaXRlZDElMCMGA1UEAxMcU2VjdGlnbyBS
# U0EgVGltZSBTdGFtcGluZyBDQTAeFw0yMjA1MTEwMDAwMDBaFw0zMzA4MTAyMzU5
# NTlaMGoxCzAJBgNVBAYTAkdCMRMwEQYDVQQIEwpNYW5jaGVzdGVyMRgwFgYDVQQK
# Ew9TZWN0aWdvIExpbWl0ZWQxLDAqBgNVBAMMI1NlY3RpZ28gUlNBIFRpbWUgU3Rh
# bXBpbmcgU2lnbmVyICMzMIICIjANBgkqhkiG9w0BAQEFAAOCAg8AMIICCgKCAgEA
# kLJxP3nh1LmKF8zDl8KQlHLtWjpvAUN/c1oonyR8oDVABvqUrwqhg7YT5EsVBl5q
# iiA0cXu7Ja0/WwqkHy9sfS5hUdCMWTc+pl3xHl2AttgfYOPNEmqIH8b+GMuTQ1Z6
# x84D1gBkKFYisUsZ0vCWyUQfOV2csJbtWkmNfnLkQ2t/yaA/bEqt1QBPvQq4g8W9
# mCwHdgFwRd7D8EJp6v8mzANEHxYo4Wp0tpxF+rY6zpTRH72MZar9/MM86A2cOGbV
# /H0em1mMkVpCV1VQFg1LdHLuoCox/CYCNPlkG1n94zrU6LhBKXQBPw3gE3crETz7
# Pc3Q5+GXW1X3KgNt1c1i2s6cHvzqcH3mfUtozlopYdOgXCWzpSdoo1j99S1ryl9k
# x2soDNqseEHeku8Pxeyr3y1vGlRRbDOzjVlg59/oFyKjeUFiz/x785LaruA8Tw9a
# zG7fH7wir7c4EJo0pwv//h1epPPuFjgrP6x2lEGdZB36gP0A4f74OtTDXrtpTXKZ
# 5fEyLVH6Ya1N6iaObfypSJg+8kYNabG3bvQF20EFxhjAUOT4rf6sY2FHkbxGtUZT
# bMX04YYnk4Q5bHXgHQx6WYsuy/RkLEJH9FRYhTflx2mn0iWLlr/GreC9sTf3H99C
# e6rrHOnrPVrd+NKQ1UmaOh2DGld/HAHCzhx9zPuWFcUCAwEAAaOCAYIwggF+MB8G
# A1UdIwQYMBaAFBqh+GEZIA/DQXdFKI7RNV8GEgRVMB0GA1UdDgQWBBQlLmg8a5or
# JBSpH6LfJjrPFKbx4DAOBgNVHQ8BAf8EBAMCBsAwDAYDVR0TAQH/BAIwADAWBgNV
# HSUBAf8EDDAKBggrBgEFBQcDCDBKBgNVHSAEQzBBMDUGDCsGAQQBsjEBAgEDCDAl
# MCMGCCsGAQUFBwIBFhdodHRwczovL3NlY3RpZ28uY29tL0NQUzAIBgZngQwBBAIw
# RAYDVR0fBD0wOzA5oDegNYYzaHR0cDovL2NybC5zZWN0aWdvLmNvbS9TZWN0aWdv
# UlNBVGltZVN0YW1waW5nQ0EuY3JsMHQGCCsGAQUFBwEBBGgwZjA/BggrBgEFBQcw
# AoYzaHR0cDovL2NydC5zZWN0aWdvLmNvbS9TZWN0aWdvUlNBVGltZVN0YW1waW5n
# Q0EuY3J0MCMGCCsGAQUFBzABhhdodHRwOi8vb2NzcC5zZWN0aWdvLmNvbTANBgkq
# hkiG9w0BAQwFAAOCAgEAc9rtaHLLwrlAoTG7tAOjLRR7JOe0WxV9qOn9rdGSDXw9
# NqBp2fOaMNqsadZ0VyQ/fg882fXDeSVsJuiNaJPO8XeJOX+oBAXaNMMU6p8IVKv/
# xH6WbCvTlOu0bOBFTSyy9zs7WrXB+9eJdW2YcnL29wco89Oy0OsZvhUseO/NRaAA
# 5PgEdrtXxZC+d1SQdJ4LT03EqhOPl68BNSvLmxF46fL5iQQ8TuOCEmLrtEQMdUHC
# DzS4iJ3IIvETatsYL254rcQFtOiECJMH+X2D/miYNOR35bHOjJRs2wNtKAVHfpsu
# 8GT726QDMRB8Gvs8GYDRC3C5VV9HvjlkzrfaI1Qy40ayMtjSKYbJFV2Ala8C+7TR
# Lp04fDXgDxztG0dInCJqVYLZ8roIZQPl8SnzSIoJAUymefKithqZlOuXKOG+fRuh
# fO1WgKb0IjOQ5IRT/Cr6wKeXqOq1jXrO5OBLoTOrC3ag1WkWt45mv1/6H8Sof6eh
# SBSRDYL8vU2Z7cnmbDb+d0OZuGktfGEv7aOwSf5bvmkkkf+T/FdpkkvZBT9thnLT
# otDAZNI6QsEaA/vQ7ZohuD+vprJRVNVMxcofEo1XxjntXP/snyZ2rWRmZ+iqMODS
# rbd9sWpBJ24DiqN04IoJgm6/4/a3vJ4LKRhogaGcP24WWUsUCQma5q6/YBXdhvUx
# ggXrMIIF5wIBATBpMFQxCzAJBgNVBAYTAkdCMRgwFgYDVQQKEw9TZWN0aWdvIExp
# bWl0ZWQxKzApBgNVBAMTIlNlY3RpZ28gUHVibGljIENvZGUgU2lnbmluZyBDQSBS
# MzYCEQCk8soRVSLMyoN4keyoUEGiMA0GCWCGSAFlAwQCAQUAoIGEMBgGCisGAQQB
# gjcCAQwxCjAIoAKAAKECgAAwGQYJKoZIhvcNAQkDMQwGCisGAQQBgjcCAQQwHAYK
# KwYBBAGCNwIBCzEOMAwGCisGAQQBgjcCARUwLwYJKoZIhvcNAQkEMSIEIAfNBhSJ
# puQ35/lUyJ/frYGKXIrWfweRR5kwGR8FiEbLMA0GCSqGSIb3DQEBAQUABIIBgLVh
# RsGY7L2ZaU93IdHWmzKJvXhTRFMM9ulCWuFL9mSku+ICVdYWNyWDuhJi/GjuMqpC
# xLRZ/7I4o2PkCbuo2cg1nsZR/gyi+0N626IN8aIsv/ntAbYU2TekRCBcC1UDZcJc
# V1MJRMqMs5pKpw53x636htI/RCsMi/WEWJlJnrJmjl/3dXB/P+pq0SqEZzGkDq2q
# rBnBmO1d9TwdRbR2CQqTEshBphQXOgKTfK451OmzXgVBVYlffvZ5xx4Qla47UEDM
# kNVQ3EN7osngzF5p2d0UPLVqVWnbko87nN2mVBFZEKxdPWN+RZd8FWmKn89WwBEO
# ojN7kULFMEQJnMpCikn3z2ELJ2ScAJYM6Xx4m0zauq+nNaOQ9VdWmiV+24QsSGHD
# hep4FSYBdmpDcYS156i8AfPjUizBhkwrF95mKKD3Sd1P3xUEPA5i2lSFIQS4RtQy
# GUplmFMExThj/ntzNWS9SEB/Wh/KnbO70sYfMT5o992ryUN005/RQ3nr+ufodqGC
# A0wwggNIBgkqhkiG9w0BCQYxggM5MIIDNQIBATCBkjB9MQswCQYDVQQGEwJHQjEb
# MBkGA1UECBMSR3JlYXRlciBNYW5jaGVzdGVyMRAwDgYDVQQHEwdTYWxmb3JkMRgw
# FgYDVQQKEw9TZWN0aWdvIExpbWl0ZWQxJTAjBgNVBAMTHFNlY3RpZ28gUlNBIFRp
# bWUgU3RhbXBpbmcgQ0ECEQCQOX+a0ko6E/K9kV8IOKlDMA0GCWCGSAFlAwQCAgUA
# oHkwGAYJKoZIhvcNAQkDMQsGCSqGSIb3DQEHATAcBgkqhkiG9w0BCQUxDxcNMjMw
# NDA2MDQ1MDE4WjA/BgkqhkiG9w0BCQQxMgQwR6mFTxuXOLQbN2ecjfOnxmzbmU8T
# J2jWzZARXe8kVe22086I+WhlD4ByV8wSYFKSMA0GCSqGSIb3DQEBAQUABIICAH9J
# gWRefdyIabnSKWvae1JmnYS62GQuDv3NpWxEF1XPGUdg8RgYknQrdIedaEXlvZNg
# de3HI4ANqrGBZESLjirQ6Ro27Cwg6lNDlayFVunwQfImkwDCFQstQXIHh3fR2y5n
# chyCogJGRkuEAxjc0PbBFtXvLQ2LAfEXShUL5KVCxv/Gn0p2EN6C6wAaweLW9GUQ
# vdbWcpv/MpcmZYjNt8iqfCzJ9X61pcKw983lU4cTppOU+LljgTvWj4dx1W2bTPxz
# uiLsbvHwTYyOenm2zFLd2JrEIoZNDhdrC+7IbKyhvgG4SFsPvfpP0kvW35+Eo4Ta
# c9bVi8uq7Y6mNxRM47BkF5aDo1fSKO/BFVQcFnF04B/IxvPZS0ddhEl6ylXyawVS
# 3yi/Sk/ToOb9wkozOp83/wXHsEMja0oZ9sY9tqeGgUVk9jDw9L/NkzgtKhKAYZ3Y
# OYT8NJaKHndDlMaSBciTt+x2kB7fBb/uPouMVBDYFmIsf2d8AVU4hBDdAiDWvula
# kMqWXTgEoKMgoKIn2dzHNImUSuYMDKsBe6mS+CWNRpkxdEzB6MwDvuBJxJVlFqtW
# wbgnDAe2TxQmGoTOEYE5g6wdNBOlmcJ0NlvvWtRnzlVkFkjNlwDbiKKaS+AK+2yv
# WYMWf2L1QGrdn3FWdpjS5m9JxO1th1+wfI/yJEm8
# SIG # End signature block
