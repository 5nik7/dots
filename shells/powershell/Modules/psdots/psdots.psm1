<#
.DESCRIPTION
    Provides functions to update the PowerShell profile
#>
function Join-Profile {
    param(
        [switch] $v,
        [switch] $i
    )

    Write-Host ''
    Write-Host ' Setting up PoowerShell Profile links...' -ForegroundColor Cyan

    Set-link "$ENV:PSDOT\profile.ps1" "$ENV:DOCUMENTS\PowerShell\profile.ps1" -v:$v -i:$i
    Set-link "$ENV:PSDOT\profile.ps1" "$ENV:DOCUMENTS\PowerShell\Microsoft.PowerShell_profile.ps1" -v:$v -i:$i
    Set-link "$ENV:PSDOT\profile.ps1" "$ENV:DOCUMENTS\PowerShell\Microsoft.VSCode_profile.ps1" -v:$v -i:$i

    Set-link "$ENV:PSDOT\profile.ps1" "$ENV:DOCUMENTS\WindowsPowerShell\pprofile.ps1" -v:$v -i:$i
    Set-link "$ENV:PSDOT\profile.ps1" "$ENV:DOCUMENTS\WindowsPowerShell\Microsoft.PowerShell_profile.ps1" -v:$v -i:$i
    Set-link "$ENV:PSDOT\profile.ps1" "$ENV:DOCUMENTS\WindowsPowerShell\Microsoft.VSCode_profile.ps1" -v:$v -i:$i

    Write-Host ''
}
