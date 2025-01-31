<#
.DESCRIPTION
    Provides functions to update the PowerShell profile
#>
$env:PSDOTPROFILE = "$env:PSDOT\profile.ps1"
$Global:PSDOTPROFILE = $env:PSDOTPROFILE
$ProfileTargets = ("Microsoft.PowerShell_profile.ps1", "Microsoft.VSCode_profile.ps1")
$ProfileDocVersions = ("PowerShell", "WindowsPowerShell")

function Join-Profile {
    param(
        [switch] $v,
        [switch] $i
    )
    Write-Host ''
    Write-Host ' Setting up PoowerShell Profile links...' -ForegroundColor Cyan
    foreach ( $ProfileDocVersions in $ProfileDocVersions) {
        foreach ( $ProfileTarget in $ProfileTargets ) {
            Set-link $PSDOTPROFILE "$env:DOCUMENTS\$ProfileDocVersions\$ProfileTargets" -v:$v -i:$i
        }
    }
    Write-Host ''
}
