$modulePath = $PSScriptRoot
$padding = 2
$PadddingOut += ' ' * $padding
function Write-Params {
  param (
    [string]$paramtext,
    [string]$desctext
  )

  $format = '{0,-32} {1}'
  $paramout = $flavor.Teal.Foreground() + ($PadddingOut * 2) + "$paramtext"
  $descout = $flavor.Text.Foreground() + "$desctext"
  Write-Host ($format -f $paramout, $descout)
}

function Show-BlastoffUsage {
  $bannerPath = Join-Path -Path $modulePath -ChildPath 'banner'
  $bodesc = $flavor.Maroon.Foreground() + $PadddingOut + 'Starship prompt theme switcher for PowerShell'

  if (Test-Path -Path $bannerPath) {
    Write-Host ''
    Write-Host ''
    Get-Content -Path $bannerPath | Write-Host
  }
  Write-Host $bodesc
  Write-Host ''
  Write-Host -ForegroundColor DarkGray 'Usage: ' -NoNewline
  Write-Host -ForegroundColor Magenta 'blastoff ' -NoNewline
  Write-Host -ForegroundColor Cyan '[options]'
  Write-Host ''
  Write-Params -paramtext '-theme' -desctext 'Set the Starship theme.'
  Write-Params -paramtext '-list' -desctext 'List all available themes.'
  Write-Params -paramtext '-help' -desctext 'Display this help message.'
  Write-Host ''

}
function Get-StarshipThemes {
  function StarshipPresetCheck($name) {
    $presets = & starship preset --list
    return $presets -contains $name
  }
  function StarshipPreset($name) {
    & starship preset $name
  }

  $starshipPresets = & starship preset --list

  Write-Host ''
  Write-Host "$PadddingOut$($flavor.Mauve.Foreground())Themes:$($flavor.Text.Foreground())"

  $themeFiles = Get-ChildItem "$env:STARSHIP_THEMES\*.toml"
  foreach ($themeFile in $themeFiles) {
    $name = [IO.Path]::GetFileNameWithoutExtension($themeFile.Name)
    if (-not ($starshipPresets -contains $name)) {
      Write-Host -NoNewline "$PadddingOut$($flavor.Surface0.Foreground()) "
      if ($name -eq $currentthemename) {
        Write-Host -NoNewline "$($flavor.Sky.Foreground())$name $($flavor.Surface2.Foreground())(current)"
      }
      else {
        Write-Host -NoNewline "$($flavor.Text.Foreground())$name"
      }
      Write-Host "$($flavor.Text.Foreground())"
    }
  }

  Write-Host ''
  Write-Host "$PadddingOut$($flavor.Mauve.Foreground())Presets:$($flavor.Text.Foreground())"

  foreach ($preset in $starshipPresets) {
    if (-not [string]::IsNullOrWhiteSpace($preset)) {
      Write-Host -NoNewline "$PadddingOut$($flavor.Surface0.Foreground()) "
      if ($preset -eq $currentthemename) {
        Write-Host -NoNewline "$($flavor.Sky.Foreground())$preset $($flavor.Surface2.Foreground())(current)"
      }
      else {
        Write-Host -NoNewline "$($flavor.Text.Foreground())$preset"
      }
      Write-Host "$($flavor.Text.Foreground())"
    }
  }
  Write-Host ''
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

  $DotConfig = "$HOME\.config"
  $DefaultConfigPath = "$DotConfig\starship.toml"
  $DefualtStarshipDir = "$DotConfig\starship"
  $DefualtThemeDir = "$DefualtStarshipDir\themes"

  $themedir = if ($env:STARSHIP_THEMES -and (Test-Path $env:STARSHIP_THEMES)) { $env:STARSHIP_THEMES }
  elseif (!(Test-Path -Path $DefualtThemeDir)) {
    New-Item -ItemType Directory -Path $DefualtThemeDir -Force | Out-Null
  }
  else { $DefualtThemeDir }
  
  $config = if ($env:STARSHIP_CONFIG -and (Test-Path $env:STARSHIP_CONFIG)) { $env:STARSHIP_CONFIG }
  else { $DefaultConfigPath }


  $config = Get-Item $config
  $configdir = $config.DirectoryName
  $islink = if ($config.LinkType -eq 'SymbolicLink') { $true } else { $false }
  if ($islink) {
    $currenttheme = Get-Item $config.ResolvedTarget
    $currentthemename = $currenttheme.BaseName
  }
  else {
    $currenttheme = $null
  }

  if ($theme) {
    $currentDir = Get-Location
    $theme = Get-Item "$themedir\$theme.toml"
    $themebase = $theme.BaseName
    $themename = $theme.Name

    if (-not (Test-Path -Path "$theme")) {
      Write-Host -ForegroundColor red "$themename not found in $configdir"
      return
    }
    else {
      if ($currentthemename -eq $themebase) {
        Write-Host ''
        Write-Host -ForegroundColor Yellow "Starship theme is already set to $themebase"
        Write-Host ''
        return
      }
      $relconfig = Get-RelativePath -Path $config -RelativeTo $configdir
      $reltheme = Get-RelativePath -Path $currenttheme -RelativeTo $configdir
      Set-Location -Path $configdir
      New-Item -ItemType SymbolicLink -Path $relconfig -Target $reltheme -Force | Out-Null
      Set-Location -Path $currentDir
      $currenttheme = $theme
      Write-Host ''
      Write-Host -ForegroundColor red '   ' -NoNewline
      Write-Host -ForegroundColor White  'Starship theme set to ' -NoNewLine
      Write-Host -ForegroundColor Magenta "$themebase"
      Write-Host ''
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

Export-ModuleMember -Function Write-Params, Show-BlastoffUsage, Get-StarshipThemes, Invoke-Blastoff

New-Alias -Name blastoff -Scope Global -Value Invoke-Blastoff -ErrorAction Ignore
