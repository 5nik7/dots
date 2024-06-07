#
# Copyright (c) Microsoft.
# Licensed under the MIT license.
#

@{

# Script module or binary module file associated with this manifest.
RootModule = 'Microsoft.PowerShell.ConsoleGuiTools.dll'

# Version number of this module.
# NOTE: This will get updated by build.ps1; the build number will be incremented for each build.
ModuleVersion = '0.7.6.0'

# Supported PSEditions
CompatiblePSEditions = @( 'Core' )

# ID used to uniquely identify this module
GUID = '06028f35-8304-4460-ae73-306741982afe'

# Author of this module
Author = 'PowerShell Team'

# Company or vendor of this module
CompanyName = 'Microsoft'

# Copyright statement for this module
Copyright = '(c) Microsoft Corporation.'

# Description of the functionality provided by this module
Description = 'Cross-platform Console Gui Tools for PowerShell'

# Minimum version of the PowerShell engine required by this module
PowerShellVersion = '7.2'

# Name of the PowerShell host required by this module
# PowerShellHostName = ''

# Minimum version of the PowerShell host required by this module
# PowerShellHostVersion = ''

# Minimum version of Microsoft .NET Framework required by this module. This prerequisite is valid for the PowerShell Desktop edition only.
# DotNetFrameworkVersion = ''

# Minimum version of the common language runtime (CLR) required by this module. This prerequisite is valid for the PowerShell Desktop edition only.
# CLRVersion = ''

# Processor architecture (None, X86, Amd64) required by this module
# ProcessorArchitecture = ''

# Modules that must be imported into the global environment prior to importing this module
# RequiredModules = @()

# Assemblies that must be loaded prior to importing this module
# RequiredAssemblies = @()

# Script files (.ps1) that are run in the caller's environment prior to importing this module.
# ScriptsToProcess = @()

# Type files (.ps1xml) to be loaded when importing this module
# TypesToProcess = @()

# Format files (.ps1xml) to be loaded when importing this module
# FormatsToProcess = @()

# Modules to import as nested modules of the module specified in RootModule/ModuleToProcess
NestedModules = @()

# Functions to export from this module, for best performance, do not use wildcards and do not delete the entry, use an empty array if there are no functions to export.
FunctionsToExport = @()

# Cmdlets to export from this module, for best performance, do not use wildcards and do not delete the entry, use an empty array if there are no cmdlets to export.
CmdletsToExport = @( 'Out-ConsoleGridView', 'Show-ObjectTree' )

# Variables to export from this module
VariablesToExport = '*'

# Aliases to export from this module, for best performance, do not use wildcards and do not delete the entry, use an empty array if there are no aliases to export.
AliasesToExport = @( 'ocgv', 'sot' )

# DSC resources to export from this module
# DscResourcesToExport = @()

# List of all modules packaged with this module
# ModuleList = @()

# List of all files packaged with this module
# FileList = @()

# Private data to pass to the module specified in RootModule/ModuleToProcess. This may also contain a PSData hashtable with additional module metadata used by PowerShell.
PrivateData = @{

    PSData = @{

        # Tags applied to this module. These help with module discovery in online galleries.
        Tags = @('Console', 'Gui', 'Out-GridView', 'Out-ConsoleGridView', 'Show-ObjectTree', 'Terminal.Gui', 'gui.cs', 'MacOS', 'Windows', 'Linux', 'PSEdition_Core')

        # A URL to the license for this module.
        LicenseUri = 'https://github.com/PowerShell/GraphicalTools/blob/master/LICENSE.txt'

        # A URL to the main website for this project.
        ProjectUri = 'https://github.com/PowerShell/GraphicalTools/'

        # A URL to an icon representing this module.
        # IconUri = ''

        # ReleaseNotes of this module
        ReleaseNotes = '# Release Notes
## v0.7.6

* Fix child expand #223

## v0.7.5

* Adds Show-ObjectTree cmdlet #179
* Fix clear last line on Windows Terminal Issue again #207
* Adds support for -Diagnostic switch to Out-ConsoleGridView #208
* Adds support for -UseNetDriver switch to Out-ConsoleGridView #208

## v0.7.4

* Fixes last line not cleared on exit in WT by updating to Terminal.Gui v1.13.5 #205

## v0.7.3

* Build updates and compliant release pipeline #168
* Updates ConsoleGuiTools to Terminal.Gui v1.10 #184
* Fixes #175. Column headers misaligned #185
* Fixes# 148. Move to next row on select #187
* Fixes #174. Changing Filter does not undo previously marked items #186
* Marked are now at top; simplified code; fixed margin #188
* Fixes #189 - Fixed typo in exception text. Added -verbose to launch.json #190
* Fixes #195 - Incompatible with OpenSUS #196
* Bump Newtonsoft.Json from 13.0.1 to 13.0.3 #198
* Bump Newtonsoft.Json from 13.0.1 to 13.0.3 #200
* Bump Microsoft.PowerShell.SDK from 7.2.6 to 7.2.13 #199
* Bump Terminal.Gui from 1.13 to 1.13.4 #197
* Remove PDB files from module #201

## v0.7.2

* Update Terminal.Gui to v1.7.1 #161
* Filter edit chops off first char of filter string passed on command line #151
* Color changes and terminal becomes unreadable #150
If items are selected, then a filter is applied, items now hidden stay selected #121
* Add UI for select-all/select-none #120
* Add ability to minimize UI #116
* Initial focus should be on the results (ListView) #87
* Import-Module causes warning on PowerShell 7 RC3 #44
* Runaway process on Ubuntu 20.4 displaying random characters upon exit. #139
* PSAnsiRenderingFileInfo causes display issues with Out-ConsoleGridView #159
* Removes building and distribution of Out-GridView and the other Avalonia-based components
* Remove ANSI escape sequences from property values #158
        
## v0.7.0

Upgraded to PowerShell 7.2 and .NET target framework `net60`

Updated Terminal.Gui to 1.7

Fixed #131 - Strip ANSI

## v0.6.3

Unreleased!

## v0.6.2

Update Terminal.Gui to 1.0.

Disable mouse mode to fix bug with mouse movement being printed to console.

Gracefully fail when running in remote sessions.

## v0.6.1

Fix off-by-one error with ellipsis so columns should be better aligned.

## v0.6.0

Now supports `-Filter` parameter.

Updated to use the final release of `Terminal.Gui` v0.90 (which is feature complete for 1.0).

## v0.5.0

`Out-ConsoleGridView` has been totally refactored!

First off, no more silly F9 menu to accept!
All you have to do is hit `ENTER` to accept your selection or `ESC` to cancel.

Also, `-OutputMode` works as expected now. `Single` lets you only select one item. `Multiple` is the default.

## v0.4.1

* Fix filter indexing to return correct selected objects

## v0.4.0

* Regex filter
* Newlines rendering fix (Thanks @tig!)

## v0.3.0

* Windows OS support (PS 6.2+)
* dynamic column widths
* Fix arrow key issue on non-Windows

## v0.2.0

Initial Release
'

        # Prerelease string of this module
        # Prerelease = ''

        # Flag to indicate whether the module requires explicit user acceptance for install/update/save
        RequireLicenseAcceptance = 'false'

        # External dependent modules of this module
        # ExternalModuleDependencies = @()

    } # End of PSData hashtable

} # End of PrivateData hashtable

# HelpInfo URI of this module
# HelpInfoURI = ''

# Default prefix for commands exported from this module. Override the default prefix using Import-Module -Prefix.
# DefaultCommandPrefix = ''

}

# SIG # Begin signature block
# MIIoKgYJKoZIhvcNAQcCoIIoGzCCKBcCAQExDzANBglghkgBZQMEAgEFADB5Bgor
# BgEEAYI3AgEEoGswaTA0BgorBgEEAYI3AgEeMCYCAwEAAAQQH8w7YFlLCE63JNLG
# KX7zUQIBAAIBAAIBAAIBAAIBADAxMA0GCWCGSAFlAwQCAQUABCDRdhDlq4/HT1m6
# 1RqMyfr+oCcXVP/tJYuizXO3VRpyvaCCDXYwggX0MIID3KADAgECAhMzAAADTrU8
# esGEb+srAAAAAANOMA0GCSqGSIb3DQEBCwUAMH4xCzAJBgNVBAYTAlVTMRMwEQYD
# VQQIEwpXYXNoaW5ndG9uMRAwDgYDVQQHEwdSZWRtb25kMR4wHAYDVQQKExVNaWNy
# b3NvZnQgQ29ycG9yYXRpb24xKDAmBgNVBAMTH01pY3Jvc29mdCBDb2RlIFNpZ25p
# bmcgUENBIDIwMTEwHhcNMjMwMzE2MTg0MzI5WhcNMjQwMzE0MTg0MzI5WjB0MQsw
# CQYDVQQGEwJVUzETMBEGA1UECBMKV2FzaGluZ3RvbjEQMA4GA1UEBxMHUmVkbW9u
# ZDEeMBwGA1UEChMVTWljcm9zb2Z0IENvcnBvcmF0aW9uMR4wHAYDVQQDExVNaWNy
# b3NvZnQgQ29ycG9yYXRpb24wggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAwggEKAoIB
# AQDdCKiNI6IBFWuvJUmf6WdOJqZmIwYs5G7AJD5UbcL6tsC+EBPDbr36pFGo1bsU
# p53nRyFYnncoMg8FK0d8jLlw0lgexDDr7gicf2zOBFWqfv/nSLwzJFNP5W03DF/1
# 1oZ12rSFqGlm+O46cRjTDFBpMRCZZGddZlRBjivby0eI1VgTD1TvAdfBYQe82fhm
# WQkYR/lWmAK+vW/1+bO7jHaxXTNCxLIBW07F8PBjUcwFxxyfbe2mHB4h1L4U0Ofa
# +HX/aREQ7SqYZz59sXM2ySOfvYyIjnqSO80NGBaz5DvzIG88J0+BNhOu2jl6Dfcq
# jYQs1H/PMSQIK6E7lXDXSpXzAgMBAAGjggFzMIIBbzAfBgNVHSUEGDAWBgorBgEE
# AYI3TAgBBggrBgEFBQcDAzAdBgNVHQ4EFgQUnMc7Zn/ukKBsBiWkwdNfsN5pdwAw
# RQYDVR0RBD4wPKQ6MDgxHjAcBgNVBAsTFU1pY3Jvc29mdCBDb3Jwb3JhdGlvbjEW
# MBQGA1UEBRMNMjMwMDEyKzUwMDUxNjAfBgNVHSMEGDAWgBRIbmTlUAXTgqoXNzci
# tW2oynUClTBUBgNVHR8ETTBLMEmgR6BFhkNodHRwOi8vd3d3Lm1pY3Jvc29mdC5j
# b20vcGtpb3BzL2NybC9NaWNDb2RTaWdQQ0EyMDExXzIwMTEtMDctMDguY3JsMGEG
# CCsGAQUFBwEBBFUwUzBRBggrBgEFBQcwAoZFaHR0cDovL3d3dy5taWNyb3NvZnQu
# Y29tL3BraW9wcy9jZXJ0cy9NaWNDb2RTaWdQQ0EyMDExXzIwMTEtMDctMDguY3J0
# MAwGA1UdEwEB/wQCMAAwDQYJKoZIhvcNAQELBQADggIBAD21v9pHoLdBSNlFAjmk
# mx4XxOZAPsVxxXbDyQv1+kGDe9XpgBnT1lXnx7JDpFMKBwAyIwdInmvhK9pGBa31
# TyeL3p7R2s0L8SABPPRJHAEk4NHpBXxHjm4TKjezAbSqqbgsy10Y7KApy+9UrKa2
# kGmsuASsk95PVm5vem7OmTs42vm0BJUU+JPQLg8Y/sdj3TtSfLYYZAaJwTAIgi7d
# hzn5hatLo7Dhz+4T+MrFd+6LUa2U3zr97QwzDthx+RP9/RZnur4inzSQsG5DCVIM
# pA1l2NWEA3KAca0tI2l6hQNYsaKL1kefdfHCrPxEry8onJjyGGv9YKoLv6AOO7Oh
# JEmbQlz/xksYG2N/JSOJ+QqYpGTEuYFYVWain7He6jgb41JbpOGKDdE/b+V2q/gX
# UgFe2gdwTpCDsvh8SMRoq1/BNXcr7iTAU38Vgr83iVtPYmFhZOVM0ULp/kKTVoir
# IpP2KCxT4OekOctt8grYnhJ16QMjmMv5o53hjNFXOxigkQWYzUO+6w50g0FAeFa8
# 5ugCCB6lXEk21FFB1FdIHpjSQf+LP/W2OV/HfhC3uTPgKbRtXo83TZYEudooyZ/A
# Vu08sibZ3MkGOJORLERNwKm2G7oqdOv4Qj8Z0JrGgMzj46NFKAxkLSpE5oHQYP1H
# tPx1lPfD7iNSbJsP6LiUHXH1MIIHejCCBWKgAwIBAgIKYQ6Q0gAAAAAAAzANBgkq
# hkiG9w0BAQsFADCBiDELMAkGA1UEBhMCVVMxEzARBgNVBAgTCldhc2hpbmd0b24x
# EDAOBgNVBAcTB1JlZG1vbmQxHjAcBgNVBAoTFU1pY3Jvc29mdCBDb3Jwb3JhdGlv
# bjEyMDAGA1UEAxMpTWljcm9zb2Z0IFJvb3QgQ2VydGlmaWNhdGUgQXV0aG9yaXR5
# IDIwMTEwHhcNMTEwNzA4MjA1OTA5WhcNMjYwNzA4MjEwOTA5WjB+MQswCQYDVQQG
# EwJVUzETMBEGA1UECBMKV2FzaGluZ3RvbjEQMA4GA1UEBxMHUmVkbW9uZDEeMBwG
# A1UEChMVTWljcm9zb2Z0IENvcnBvcmF0aW9uMSgwJgYDVQQDEx9NaWNyb3NvZnQg
# Q29kZSBTaWduaW5nIFBDQSAyMDExMIICIjANBgkqhkiG9w0BAQEFAAOCAg8AMIIC
# CgKCAgEAq/D6chAcLq3YbqqCEE00uvK2WCGfQhsqa+laUKq4BjgaBEm6f8MMHt03
# a8YS2AvwOMKZBrDIOdUBFDFC04kNeWSHfpRgJGyvnkmc6Whe0t+bU7IKLMOv2akr
# rnoJr9eWWcpgGgXpZnboMlImEi/nqwhQz7NEt13YxC4Ddato88tt8zpcoRb0Rrrg
# OGSsbmQ1eKagYw8t00CT+OPeBw3VXHmlSSnnDb6gE3e+lD3v++MrWhAfTVYoonpy
# 4BI6t0le2O3tQ5GD2Xuye4Yb2T6xjF3oiU+EGvKhL1nkkDstrjNYxbc+/jLTswM9
# sbKvkjh+0p2ALPVOVpEhNSXDOW5kf1O6nA+tGSOEy/S6A4aN91/w0FK/jJSHvMAh
# dCVfGCi2zCcoOCWYOUo2z3yxkq4cI6epZuxhH2rhKEmdX4jiJV3TIUs+UsS1Vz8k
# A/DRelsv1SPjcF0PUUZ3s/gA4bysAoJf28AVs70b1FVL5zmhD+kjSbwYuER8ReTB
# w3J64HLnJN+/RpnF78IcV9uDjexNSTCnq47f7Fufr/zdsGbiwZeBe+3W7UvnSSmn
# Eyimp31ngOaKYnhfsi+E11ecXL93KCjx7W3DKI8sj0A3T8HhhUSJxAlMxdSlQy90
# lfdu+HggWCwTXWCVmj5PM4TasIgX3p5O9JawvEagbJjS4NaIjAsCAwEAAaOCAe0w
# ggHpMBAGCSsGAQQBgjcVAQQDAgEAMB0GA1UdDgQWBBRIbmTlUAXTgqoXNzcitW2o
# ynUClTAZBgkrBgEEAYI3FAIEDB4KAFMAdQBiAEMAQTALBgNVHQ8EBAMCAYYwDwYD
# VR0TAQH/BAUwAwEB/zAfBgNVHSMEGDAWgBRyLToCMZBDuRQFTuHqp8cx0SOJNDBa
# BgNVHR8EUzBRME+gTaBLhklodHRwOi8vY3JsLm1pY3Jvc29mdC5jb20vcGtpL2Ny
# bC9wcm9kdWN0cy9NaWNSb29DZXJBdXQyMDExXzIwMTFfMDNfMjIuY3JsMF4GCCsG
# AQUFBwEBBFIwUDBOBggrBgEFBQcwAoZCaHR0cDovL3d3dy5taWNyb3NvZnQuY29t
# L3BraS9jZXJ0cy9NaWNSb29DZXJBdXQyMDExXzIwMTFfMDNfMjIuY3J0MIGfBgNV
# HSAEgZcwgZQwgZEGCSsGAQQBgjcuAzCBgzA/BggrBgEFBQcCARYzaHR0cDovL3d3
# dy5taWNyb3NvZnQuY29tL3BraW9wcy9kb2NzL3ByaW1hcnljcHMuaHRtMEAGCCsG
# AQUFBwICMDQeMiAdAEwAZQBnAGEAbABfAHAAbwBsAGkAYwB5AF8AcwB0AGEAdABl
# AG0AZQBuAHQALiAdMA0GCSqGSIb3DQEBCwUAA4ICAQBn8oalmOBUeRou09h0ZyKb
# C5YR4WOSmUKWfdJ5DJDBZV8uLD74w3LRbYP+vj/oCso7v0epo/Np22O/IjWll11l
# hJB9i0ZQVdgMknzSGksc8zxCi1LQsP1r4z4HLimb5j0bpdS1HXeUOeLpZMlEPXh6
# I/MTfaaQdION9MsmAkYqwooQu6SpBQyb7Wj6aC6VoCo/KmtYSWMfCWluWpiW5IP0
# wI/zRive/DvQvTXvbiWu5a8n7dDd8w6vmSiXmE0OPQvyCInWH8MyGOLwxS3OW560
# STkKxgrCxq2u5bLZ2xWIUUVYODJxJxp/sfQn+N4sOiBpmLJZiWhub6e3dMNABQam
# ASooPoI/E01mC8CzTfXhj38cbxV9Rad25UAqZaPDXVJihsMdYzaXht/a8/jyFqGa
# J+HNpZfQ7l1jQeNbB5yHPgZ3BtEGsXUfFL5hYbXw3MYbBL7fQccOKO7eZS/sl/ah
# XJbYANahRr1Z85elCUtIEJmAH9AAKcWxm6U/RXceNcbSoqKfenoi+kiVH6v7RyOA
# 9Z74v2u3S5fi63V4GuzqN5l5GEv/1rMjaHXmr/r8i+sLgOppO6/8MO0ETI7f33Vt
# Y5E90Z1WTk+/gFcioXgRMiF670EKsT/7qMykXcGhiJtXcVZOSEXAQsmbdlsKgEhr
# /Xmfwb1tbWrJUnMTDXpQzTGCGgowghoGAgEBMIGVMH4xCzAJBgNVBAYTAlVTMRMw
# EQYDVQQIEwpXYXNoaW5ndG9uMRAwDgYDVQQHEwdSZWRtb25kMR4wHAYDVQQKExVN
# aWNyb3NvZnQgQ29ycG9yYXRpb24xKDAmBgNVBAMTH01pY3Jvc29mdCBDb2RlIFNp
# Z25pbmcgUENBIDIwMTECEzMAAANOtTx6wYRv6ysAAAAAA04wDQYJYIZIAWUDBAIB
# BQCgga4wGQYJKoZIhvcNAQkDMQwGCisGAQQBgjcCAQQwHAYKKwYBBAGCNwIBCzEO
# MAwGCisGAQQBgjcCARUwLwYJKoZIhvcNAQkEMSIEIERm1JOEL32rS/15mBfYK588
# SJVYrlQ0PZ8FnE4WjGBEMEIGCisGAQQBgjcCAQwxNDAyoBSAEgBNAGkAYwByAG8A
# cwBvAGYAdKEagBhodHRwOi8vd3d3Lm1pY3Jvc29mdC5jb20wDQYJKoZIhvcNAQEB
# BQAEggEAxv7b4BJ0txOWIYHFxn4OWDStYGOhJZM5LRz3UugbXteV68vVLXPc01iF
# YrP1fRImJTWIVGMDAjeG+B/cz0TO3PzU6U9p1WhGf8z4Rv5r1csyoFbgm+EFL3M1
# ju4U+5wx78Y2mOtjR15vdy3kAvO+T6GdTKoP24x3/HurHJPJ+x3T6Lh/e2DA6Fbg
# jwIxbORJ5tdGQq1cXQwCYvBCxB1ZWMVzEYXk5Rz0mIQN7TsPQG1RspFkDC93Wpvl
# ODfGeGhaQ1n7VVD6HdykVy7HP9JGzlH/iorHj+kOY6ao4c9pwrS1P2p0RV0AEwZV
# NUkc6Y9mBmW0xiePkQe67FNuLSPiZKGCF5QwgheQBgorBgEEAYI3AwMBMYIXgDCC
# F3wGCSqGSIb3DQEHAqCCF20wghdpAgEDMQ8wDQYJYIZIAWUDBAIBBQAwggFSBgsq
# hkiG9w0BCRABBKCCAUEEggE9MIIBOQIBAQYKKwYBBAGEWQoDATAxMA0GCWCGSAFl
# AwQCAQUABCBCy3K0MFbZThHVzJlxxHtHPOdMzJblEpJDg4Q+v+6i0AIGZShkRmqL
# GBMyMDIzMTAyNzIwMDk0Ny41NTNaMASAAgH0oIHRpIHOMIHLMQswCQYDVQQGEwJV
# UzETMBEGA1UECBMKV2FzaGluZ3RvbjEQMA4GA1UEBxMHUmVkbW9uZDEeMBwGA1UE
# ChMVTWljcm9zb2Z0IENvcnBvcmF0aW9uMSUwIwYDVQQLExxNaWNyb3NvZnQgQW1l
# cmljYSBPcGVyYXRpb25zMScwJQYDVQQLEx5uU2hpZWxkIFRTUyBFU046QTkzNS0w
# M0UwLUQ5NDcxJTAjBgNVBAMTHE1pY3Jvc29mdCBUaW1lLVN0YW1wIFNlcnZpY2Wg
# ghHqMIIHIDCCBQigAwIBAgITMwAAAdGyW0AobC7SRQABAAAB0TANBgkqhkiG9w0B
# AQsFADB8MQswCQYDVQQGEwJVUzETMBEGA1UECBMKV2FzaGluZ3RvbjEQMA4GA1UE
# BxMHUmVkbW9uZDEeMBwGA1UEChMVTWljcm9zb2Z0IENvcnBvcmF0aW9uMSYwJAYD
# VQQDEx1NaWNyb3NvZnQgVGltZS1TdGFtcCBQQ0EgMjAxMDAeFw0yMzA1MjUxOTEy
# MThaFw0yNDAyMDExOTEyMThaMIHLMQswCQYDVQQGEwJVUzETMBEGA1UECBMKV2Fz
# aGluZ3RvbjEQMA4GA1UEBxMHUmVkbW9uZDEeMBwGA1UEChMVTWljcm9zb2Z0IENv
# cnBvcmF0aW9uMSUwIwYDVQQLExxNaWNyb3NvZnQgQW1lcmljYSBPcGVyYXRpb25z
# MScwJQYDVQQLEx5uU2hpZWxkIFRTUyBFU046QTkzNS0wM0UwLUQ5NDcxJTAjBgNV
# BAMTHE1pY3Jvc29mdCBUaW1lLVN0YW1wIFNlcnZpY2UwggIiMA0GCSqGSIb3DQEB
# AQUAA4ICDwAwggIKAoICAQCZTNo0OeGz2XFd2gLg5nTlBm8XOpuwJIiXsMU61rwq
# 1ZKDpa443RrSG/pH8Gz6XNnFQKGnCqNCtmvoKULApwrT/s7/e1X0lNFKmj7U7X4p
# 00S0uQbW6LwSn/zWHaG2c54ZXsGY+BYfhWDgbFpCTxRzTnRCG62bkWPp6ZHbZPg4
# Ht1CRCAMhhOGTR8wI4G7wwWZwdMc6UvUUlq0ql9AxAfzkYRpi2tRvDHMdmZ3vyXp
# qhFwvRG8cgCH/TTCjW5q6aNbdqKL3BFDPzUtuCNsPXL3/E0dR2bDMqa0aNH+iIfh
# GC4/vcwuteOMCPUIDVSqDCNfIaPDEwYci1fd9gu1zVw+HEhDZM7Ea3nxIUrzt+Rf
# p5ToMMj4QAmJ6Uadm+TPbDbo8kFIK70ShmW8wn8fJk9ReQQEpTtIN43eRv9QmXy3
# Ued80osOBE+WkdMvSCFh+qgCsKdzQxQJG62cTeoU2eqNhH3oppXmyfVUwbsefQzM
# PtbinCZd0FUlmlM/dH+4OniqQyaHvrtYy3wqIafY3zeFITlVAoP9q9vF4W7KHR/u
# F0mvTpAL5NaTDN1plQS0MdjMkgzZK5gtwqOe/3rTlqBzxwa7YYp3urP5yWkTzISG
# nhNWIZOxOyQIOxZfbiIbAHbm3M8hj73KQWcCR5JavgkwUmncFHESaQf4Drqs+/1L
# 1QIDAQABo4IBSTCCAUUwHQYDVR0OBBYEFAuO8UzF7DcH0mmsF4XQxxHQvS2jMB8G
# A1UdIwQYMBaAFJ+nFV0AXmJdg/Tl0mWnG1M1GelyMF8GA1UdHwRYMFYwVKBSoFCG
# Tmh0dHA6Ly93d3cubWljcm9zb2Z0LmNvbS9wa2lvcHMvY3JsL01pY3Jvc29mdCUy
# MFRpbWUtU3RhbXAlMjBQQ0ElMjAyMDEwKDEpLmNybDBsBggrBgEFBQcBAQRgMF4w
# XAYIKwYBBQUHMAKGUGh0dHA6Ly93d3cubWljcm9zb2Z0LmNvbS9wa2lvcHMvY2Vy
# dHMvTWljcm9zb2Z0JTIwVGltZS1TdGFtcCUyMFBDQSUyMDIwMTAoMSkuY3J0MAwG
# A1UdEwEB/wQCMAAwFgYDVR0lAQH/BAwwCgYIKwYBBQUHAwgwDgYDVR0PAQH/BAQD
# AgeAMA0GCSqGSIb3DQEBCwUAA4ICAQCbu9rTAHV24mY0qoG5eEnImz5akGXTviBw
# Kp2Y51s26w8oDrWor+m00R4/3BcDmYlUK8Nrx/auYFYidZddcUjw42QxSStmv/qW
# nCQi/2OnH32KVHQ+kMOZPABQTG1XkcnYPUOOEEor6f/3Js1uj4wjHzE4V4aumYXB
# Asr4L5KR8vKes5tFxhMkWND/O7W/RaHYwJMjMkxVosBok7V21sJAlxScEXxfJa+/
# qkqUr7CZgw3R4jCHRkPqQhMWibXPMYar/iF0ZuLB9O89DMJNhjK9BSf6iqgZoMuz
# IVt+EBoTzpv/9p4wQ6xoBCs29mkj/EIWFdc+5a30kuCQOSEOj07+WI29A4k6QIRB
# 5w+eMmZ0Jec0sSyeQB5KjxE51iYMhtlMrUKcr06nBqCsSKPYsSAITAzgssJD+Z/c
# TS7Cu35fJrWhM9NYX24uAxYLAW0ipNtWptIeV6akuZEeEV6BNtM3VTk+mAlV5/eC
# /0Y17aVSjK5/gyDoLNmrgVwv5TAaBmq/wgRRFHmW9UJ3zv8Lmk6mIoAyTpqBbuUj
# MLyrtajuSsA/m2DnKMO0Qiz1v+FSVbqM38J/PTlhCTUbFOx0kLT7Y/7+ZyrilVCz
# yAYfFIinDIjWlM85tDeU8ZfJCjFKwq3DsRxV4JY18xww8TTmod3lkr9NqGQ54Lmy
# PVc+5ibNrjCCB3EwggVZoAMCAQICEzMAAAAVxedrngKbSZkAAAAAABUwDQYJKoZI
# hvcNAQELBQAwgYgxCzAJBgNVBAYTAlVTMRMwEQYDVQQIEwpXYXNoaW5ndG9uMRAw
# DgYDVQQHEwdSZWRtb25kMR4wHAYDVQQKExVNaWNyb3NvZnQgQ29ycG9yYXRpb24x
# MjAwBgNVBAMTKU1pY3Jvc29mdCBSb290IENlcnRpZmljYXRlIEF1dGhvcml0eSAy
# MDEwMB4XDTIxMDkzMDE4MjIyNVoXDTMwMDkzMDE4MzIyNVowfDELMAkGA1UEBhMC
# VVMxEzARBgNVBAgTCldhc2hpbmd0b24xEDAOBgNVBAcTB1JlZG1vbmQxHjAcBgNV
# BAoTFU1pY3Jvc29mdCBDb3Jwb3JhdGlvbjEmMCQGA1UEAxMdTWljcm9zb2Z0IFRp
# bWUtU3RhbXAgUENBIDIwMTAwggIiMA0GCSqGSIb3DQEBAQUAA4ICDwAwggIKAoIC
# AQDk4aZM57RyIQt5osvXJHm9DtWC0/3unAcH0qlsTnXIyjVX9gF/bErg4r25Phdg
# M/9cT8dm95VTcVrifkpa/rg2Z4VGIwy1jRPPdzLAEBjoYH1qUoNEt6aORmsHFPPF
# dvWGUNzBRMhxXFExN6AKOG6N7dcP2CZTfDlhAnrEqv1yaa8dq6z2Nr41JmTamDu6
# GnszrYBbfowQHJ1S/rboYiXcag/PXfT+jlPP1uyFVk3v3byNpOORj7I5LFGc6XBp
# Dco2LXCOMcg1KL3jtIckw+DJj361VI/c+gVVmG1oO5pGve2krnopN6zL64NF50Zu
# yjLVwIYwXE8s4mKyzbnijYjklqwBSru+cakXW2dg3viSkR4dPf0gz3N9QZpGdc3E
# XzTdEonW/aUgfX782Z5F37ZyL9t9X4C626p+Nuw2TPYrbqgSUei/BQOj0XOmTTd0
# lBw0gg/wEPK3Rxjtp+iZfD9M269ewvPV2HM9Q07BMzlMjgK8QmguEOqEUUbi0b1q
# GFphAXPKZ6Je1yh2AuIzGHLXpyDwwvoSCtdjbwzJNmSLW6CmgyFdXzB0kZSU2LlQ
# +QuJYfM2BjUYhEfb3BvR/bLUHMVr9lxSUV0S2yW6r1AFemzFER1y7435UsSFF5PA
# PBXbGjfHCBUYP3irRbb1Hode2o+eFnJpxq57t7c+auIurQIDAQABo4IB3TCCAdkw
# EgYJKwYBBAGCNxUBBAUCAwEAATAjBgkrBgEEAYI3FQIEFgQUKqdS/mTEmr6CkTxG
# NSnPEP8vBO4wHQYDVR0OBBYEFJ+nFV0AXmJdg/Tl0mWnG1M1GelyMFwGA1UdIARV
# MFMwUQYMKwYBBAGCN0yDfQEBMEEwPwYIKwYBBQUHAgEWM2h0dHA6Ly93d3cubWlj
# cm9zb2Z0LmNvbS9wa2lvcHMvRG9jcy9SZXBvc2l0b3J5Lmh0bTATBgNVHSUEDDAK
# BggrBgEFBQcDCDAZBgkrBgEEAYI3FAIEDB4KAFMAdQBiAEMAQTALBgNVHQ8EBAMC
# AYYwDwYDVR0TAQH/BAUwAwEB/zAfBgNVHSMEGDAWgBTV9lbLj+iiXGJo0T2UkFvX
# zpoYxDBWBgNVHR8ETzBNMEugSaBHhkVodHRwOi8vY3JsLm1pY3Jvc29mdC5jb20v
# cGtpL2NybC9wcm9kdWN0cy9NaWNSb29DZXJBdXRfMjAxMC0wNi0yMy5jcmwwWgYI
# KwYBBQUHAQEETjBMMEoGCCsGAQUFBzAChj5odHRwOi8vd3d3Lm1pY3Jvc29mdC5j
# b20vcGtpL2NlcnRzL01pY1Jvb0NlckF1dF8yMDEwLTA2LTIzLmNydDANBgkqhkiG
# 9w0BAQsFAAOCAgEAnVV9/Cqt4SwfZwExJFvhnnJL/Klv6lwUtj5OR2R4sQaTlz0x
# M7U518JxNj/aZGx80HU5bbsPMeTCj/ts0aGUGCLu6WZnOlNN3Zi6th542DYunKmC
# VgADsAW+iehp4LoJ7nvfam++Kctu2D9IdQHZGN5tggz1bSNU5HhTdSRXud2f8449
# xvNo32X2pFaq95W2KFUn0CS9QKC/GbYSEhFdPSfgQJY4rPf5KYnDvBewVIVCs/wM
# nosZiefwC2qBwoEZQhlSdYo2wh3DYXMuLGt7bj8sCXgU6ZGyqVvfSaN0DLzskYDS
# PeZKPmY7T7uG+jIa2Zb0j/aRAfbOxnT99kxybxCrdTDFNLB62FD+CljdQDzHVG2d
# Y3RILLFORy3BFARxv2T5JL5zbcqOCb2zAVdJVGTZc9d/HltEAY5aGZFrDZ+kKNxn
# GSgkujhLmm77IVRrakURR6nxt67I6IleT53S0Ex2tVdUCbFpAUR+fKFhbHP+Crvs
# QWY9af3LwUFJfn6Tvsv4O+S3Fb+0zj6lMVGEvL8CwYKiexcdFYmNcP7ntdAoGokL
# jzbaukz5m/8K6TT4JDVnK+ANuOaMmdbhIurwJ0I9JZTmdHRbatGePu1+oDEzfbzL
# 6Xu/OHBE0ZDxyKs6ijoIYn/ZcGNTTY3ugm2lBRDBcQZqELQdVTNYs6FwZvKhggNN
# MIICNQIBATCB+aGB0aSBzjCByzELMAkGA1UEBhMCVVMxEzARBgNVBAgTCldhc2hp
# bmd0b24xEDAOBgNVBAcTB1JlZG1vbmQxHjAcBgNVBAoTFU1pY3Jvc29mdCBDb3Jw
# b3JhdGlvbjElMCMGA1UECxMcTWljcm9zb2Z0IEFtZXJpY2EgT3BlcmF0aW9uczEn
# MCUGA1UECxMeblNoaWVsZCBUU1MgRVNOOkE5MzUtMDNFMC1EOTQ3MSUwIwYDVQQD
# ExxNaWNyb3NvZnQgVGltZS1TdGFtcCBTZXJ2aWNloiMKAQEwBwYFKw4DAhoDFQBH
# JY2Fv+GhLQtRDR2vIzBaSv/7LKCBgzCBgKR+MHwxCzAJBgNVBAYTAlVTMRMwEQYD
# VQQIEwpXYXNoaW5ndG9uMRAwDgYDVQQHEwdSZWRtb25kMR4wHAYDVQQKExVNaWNy
# b3NvZnQgQ29ycG9yYXRpb24xJjAkBgNVBAMTHU1pY3Jvc29mdCBUaW1lLVN0YW1w
# IFBDQSAyMDEwMA0GCSqGSIb3DQEBCwUAAgUA6OX/xzAiGA8yMDIzMTAyNzA5MjIx
# NVoYDzIwMjMxMDI4MDkyMjE1WjB0MDoGCisGAQQBhFkKBAExLDAqMAoCBQDo5f/H
# AgEAMAcCAQACAhYfMAcCAQACAhNbMAoCBQDo51FHAgEAMDYGCisGAQQBhFkKBAIx
# KDAmMAwGCisGAQQBhFkKAwKgCjAIAgEAAgMHoSChCjAIAgEAAgMBhqAwDQYJKoZI
# hvcNAQELBQADggEBAKwRudAtTFk3UKBeKY3mGmUDqP8pTeRkXokou3MJYuoel2S6
# +zwGb42QD/80DT2aZ2DheS3sZmrOX/0xS43fewa3Cpu2NEWIIva4f756f/Hdb6iF
# yhqxNlI572KcL1B6gwMT6XC+TLB6+9Ab0LavSk69NEr6fWMCMI5jQN5SL1W8jSMA
# dxzv7eYWnMB4ODoRCzNHRDeSzPqV7ML+f3wFKCmCfvKxlLfQOyFlmP7e9KBiSrSq
# /ajj2QAB6AMzi+9enjsQcIyxw8CrQPPBwj2hZjecDFy+tk2X2i0tyiC6prooavru
# qqZv7fmaSlMvpySXLqNUG87ycHqbqvWB6aos7zExggQNMIIECQIBATCBkzB8MQsw
# CQYDVQQGEwJVUzETMBEGA1UECBMKV2FzaGluZ3RvbjEQMA4GA1UEBxMHUmVkbW9u
# ZDEeMBwGA1UEChMVTWljcm9zb2Z0IENvcnBvcmF0aW9uMSYwJAYDVQQDEx1NaWNy
# b3NvZnQgVGltZS1TdGFtcCBQQ0EgMjAxMAITMwAAAdGyW0AobC7SRQABAAAB0TAN
# BglghkgBZQMEAgEFAKCCAUowGgYJKoZIhvcNAQkDMQ0GCyqGSIb3DQEJEAEEMC8G
# CSqGSIb3DQEJBDEiBCAp+1g9RpT87oxFFrsqP+tDpiBxQ7S41v+JDRvCmmxRTTCB
# +gYLKoZIhvcNAQkQAi8xgeowgecwgeQwgb0EIMy8YXkCALv57c5sRhrPTub1q4Tw
# J6oVA36k8IiI/AcMMIGYMIGApH4wfDELMAkGA1UEBhMCVVMxEzARBgNVBAgTCldh
# c2hpbmd0b24xEDAOBgNVBAcTB1JlZG1vbmQxHjAcBgNVBAoTFU1pY3Jvc29mdCBD
# b3Jwb3JhdGlvbjEmMCQGA1UEAxMdTWljcm9zb2Z0IFRpbWUtU3RhbXAgUENBIDIw
# MTACEzMAAAHRsltAKGwu0kUAAQAAAdEwIgQgaeRrQUNpw/7qN1FhiFvxCw+2RWcQ
# NEneSARL2J8GQLQwDQYJKoZIhvcNAQELBQAEggIAOSOHZHtWlfOPWGseOBx27vzc
# hDuYPxSqCg4n+9sYFNquRAg0jqNYu+csQRgMp90nYoc3fF2nCxKLyHeA7HAUA1+H
# nfADUbnczRFuQNc6/WLSQ4gSFylnnNN6HL9vMQpli7ajA9u/uWwDiAAvQgXTPkpU
# RMwVJMiYju4dCMv3DtNJ3I5dxNtksLCGt1MUqQ++WY1HmbauH63Lg0PFclpXNHOf
# o9bJW+num9awFvE4aaSwb5ssXCu3p97aJQviyfNvn3NI/O06ir4K77zUMZhlnBrA
# eprKZs0MCwBUBvaX9muNmMvDORNQWe0d1rIcSmacaENBKTgh9ySyKnhokCb6w8FT
# BozlOe5DHEjS/cDbka9PjPRuZDhvIhg1zd2fpQ46h796bOo2k757Jyge5Mbog0LC
# OIr17a1DeDKR/b0vzciobivf/s+i9ka8F7OztXT17pdtddw9sD9yMYoME92Rt8QS
# hfCf+y/i21+YIMHDi4wW9ZACzLA2DVmmJxIyXD8f2+8EaIhEGYZUUmjoVN/cGkvb
# 1Fx1CrrDiMsFswJqsZ2IJkY6tGPIkQWRJSd/t/3CAIOp6yGFNZGSgx3dx5vEp18Y
# +S3VRjbJ6uc1GN6rQpwoG826xaVj4azHZ2FmIbxbt6eOi16LACr9gQfiZoSsf3Y6
# H+mV1HoHlVCEZtCvhQ4=
# SIG # End signature block
