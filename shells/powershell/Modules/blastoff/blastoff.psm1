$modulePath = $PSScriptRoot
$PadddingOut += ' ' * $env:padding

function WriteParams {
    param (
      [string]$paramtext,
      [string]$desctext
    )

    $format = "{0,-32} {1}"
    $paramout = $flavor.Teal.Foreground() + ($PadddingOut * 2) + "$paramtext"
    $descout = $flavor.Text.Foreground() + "$desctext"
    Write-Host ($format -f $paramout, $descout)
    linebreak
}

function Show-BlastoffUsage {
  $bannerPath = Join-Path -Path $modulePath -ChildPath 'banner'
  $bodesc = $flavor.Maroon.Foreground() + $PadddingOut + "Starship prompt theme switcher for PowerShell"

  if (Test-Path -Path $bannerPath) {
    linebreak 2
    Get-Content -Path $bannerPath | Write-Host
  }
  Write-Host $bodesc
  linebreak
  wh -bb 0 -ba 0 -nl -pad $env:padding 'Usage: ' DarkGray 'blastoff ' Magenta '[options]' Cyan
  linebreak
  WriteParams -paramtext '-theme' -desctext 'Set the Starship theme.'
  WriteParams -paramtext '-list' -desctext 'List all available themes.'
  WriteParams -paramtext '-help' -desctext 'Display this help message.'
  linebreak

}

function Get-StarshipThemes {

  wh -box -bb 1 -ba 1 -pad $env:padding 'Listing Starship Thenes.' Magenta

  Get-ChildItem $env:STARSHIP_THEMES | ForEach-Object `
  {
    $name = [IO.Path]::GetFileNameWithoutExtension($_.Name)

    if ($name -eq $currentStarshipTheme) {
      $color = 'Green'
      $output = wh -bb 0 -ba 0 -nl -pad $env:padding '  ' DarkGray $name $color ' (current)' 'DarkGray'
    } else {
      $color = 'Gray'
      $output = wh -bb 0 -ba 0 -nl -pad $env:padding '  ' DarkGray $name $color
    }

    $output
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
  $currentStarshipTheme = [IO.Path]::GetFileNameWithoutExtension((Get-Item -Path $env:STARSHIP_CONFIG | Select-Object -ExpandProperty Target))
  $targetDir = (Get-Item -Path $env:STARSHIP_CONFIG | Select-Object -ExpandProperty Directory)

  if ($theme) {
    $curretDir = Get-Location
    $sourcePath = "themes\$theme.toml"
    $targetPath = "starship.toml"

    if (-not (Test-Path -Path "$env:STARSHIP_DIR\themes\$theme.toml")) {
      Write-Err "$theme not found"
      return
    } else {

    Set-Location -Path $targetDir
    New-Item -ItemType SymbolicLink -Path $targetPath -Target $sourcePath -Force | Out-Null
    Set-Location -Path $curretDir
    $currentStarshipTheme = $theme
    wh -box -border 0 -bb 1 -ba 1 -pad $env:padding '  ' red $theme green
    return
    }
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
}



New-Alias -Name blastoff -Scope Global -Value Invoke-Blastoff -ErrorAction Ignore
