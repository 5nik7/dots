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
      if ($name -eq $CurrentStarshipTheme) {
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
      if ($preset -eq $CurrentStarshipTheme) {
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
    [string]$theme = ''
  )

  $DotConfig = "$HOME\.config"
  $DefaultConfigPath = "$DotConfig\starship.toml"
  $DefaultStarshipDir = "$DotConfig\starship"

  $config = if ($env:STARSHIP_CONFIG -and (Test-Path $env:STARSHIP_CONFIG)) { $env:STARSHIP_CONFIG }
  else { $DefaultConfigPath }
  

  $item = Get-Item $config
  $configdir = $item.DirectoryName.ToString()
  $islink = if ($item.LinkType -eq 'SymbolicLink') { $true } else { $false }
  if ($islink) {
    $CurrentStarshipTheme = $item.ResolvedTarget | ForEach-Object {
      $_.ToString()
    } | Split-Path -Leaf | ForEach-Object {
      [IO.Path]::GetFileNameWithoutExtension($_)
    }
  }

  if ($theme -ne '') {
    $DefaultThemeDir = "$DefaultStarshipDir\themes"
    
    $themedir = if ($env:STARSHIP_THEMES -and (Test-Path $env:STARSHIP_THEMES)) { $env:STARSHIP_THEMES }
    elseif (!(Test-Path -Path $DefaultThemeDir)) {
      New-Item -ItemType Directory -Path $DefaultThemeDir -Force | Out-Null
    }
    else { $DefaultThemeDir }
  

    $currentDir = Get-Location
    $themepath = "$themedir\$theme.toml"
    $item = Get-Item $themepath -ErrorAction SilentlyContinue
    $themebase = $item.BaseName | ForEach-Object {
      $_.ToString()
    }

    if (Test-Path -Path $themepath) {
      if (!($theme -eq $CurrentStarshipTheme)) {
        Set-Location -Path $configdir
        $relconfig = Get-RelativePath -Path $config -RelativeTo $configdir
        $reltheme = Get-RelativePath -Path $themepath -RelativeTo $configdir  
        New-Item -ItemType SymbolicLink -Path $relconfig -Target $reltheme -Force | Out-Null
        Set-Location -Path $currentDir
        $CurrentStarshipTheme = $theme
        Write-Host ''
        Write-Host -ForegroundColor red '   ' -NoNewline
        Write-Host -ForegroundColor White  'Starship theme set to ' -NoNewLine
        Write-Host -ForegroundColor Magenta "$theme"
        Write-Host ''
        return
      }
      else {
        Write-Host ''
        Write-Host -ForegroundColor Yellow "Starship theme is already set to $theme"
        Write-Host ''
      }
    }
    else {    
      Write-Host -ForegroundColor red "$themebase.toml not found in $configdir"
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

Export-ModuleMember -Function * -Alias * -Variable *
