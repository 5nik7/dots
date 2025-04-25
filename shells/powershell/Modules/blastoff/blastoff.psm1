$modulePath = $PSScriptRoot



function Show-BlastoffUsage {

  linebreak 2
  Get-Content -Path $bannerPath | Write-Host
  linebreak
  Write-Host -foregroundColor DarkMagenta ' Dotfiles utility for PowerShell.'
  linebreak
  Write-Host ' Usage: dots [options]'
  linebreak
  Write-Host -foregroundColor Yellow "`t-help: " -NoNewline
  Write-Host 'Display this help message.'
  linebreak 2

}

function Invoke-Blastoff {
  <#
    .SYNOPSIS
        Sets up PowerShell profile links.
    .DESCRIPTION
        This function sets up symbolic links for PowerShell profiles to a specified profile script.
    .PARAMETER help
        Displays usage information for the dots command when specified.
    .EXAMPLE
        dots -help
        # This will display the usage information for the dots command.
    .NOTES
        Author: njen
        Version: 1.0.0
    #>
  param (
    [switch]$help,
    [switch]$list,
    [switch]$Name
  )
  if ($help) {
    Show-BlastoffUsage
    return
  }
  else {
    Show-BlastoffUsage
  }

}
