$modulePath = $PSScriptRoot

function Show-BlastoffUsage {
  $bannerPath = Join-Path -Path $modulePath -ChildPath 'banner'
  if (Test-Path -Path $bannerPath) {
    linebreak 2
    Get-Content -Path $bannerPath | Write-Host
  }
  linebreak
  Write-Host -foregroundColor DarkMagenta ' Starship prompt theme switcher for PowerShell.'
  linebreak
  Write-Host ' Usage: blastoff [options]'
  linebreak
  Write-Host -foregroundColor Cyan "`t-theme: " -NoNewline
  Write-Host 'Select themes.'
  linebreak
  Write-Host -foregroundColor Cyan "`t-list: " -NoNewline
  Write-Host 'Lists all available themes.'
  linebreak
  Write-Host -foregroundColor Cyan "`t-help: " -NoNewline
  Write-Host 'Display this help message.'
  linebreak 2

}

function Get-StarshipThemes {

  wh -box -bb 1 -ba 1 -pad $env:padding 'Listing Starship Thenes.' Magenta

  Get-ChildItem $env:STARSHIP_THEMES | ForEach-Object `
  {
    $name = [IO.Path]::GetFileNameWithoutExtension($_.Name)
    wh -bb 0 -ba 0 -nl -pad $env:padding '  ' DarkGray $name Gray
  }
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
    [string]$theme
  )
  if ($theme) {
    Get-Content "$env:STARSHIP_THEMES\$theme.toml" > $env:STARSHIP_CONFIG
    wh -box -border 0 -bb 1 -ba 1 -pad $env:padding 'BLASTOFF' white ' │ ' darkgray 'Theme changed to ' white $theme green
    return
  }
  if ($help) {
    Show-BlastoffUsage
    return
  }
  if ($list) {
    Get-StarshipThemes
    return
  }
  Show-BlastoffUsage
  return
}



New-Alias -Name blastoff -Scope Global -Value Invoke-Blastoff -ErrorAction Ignore
