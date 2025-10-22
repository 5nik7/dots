$modulePath = $PSScriptRoot

$psdoticon = ''
$labicon = ''
$ps1icon = '󰨊'

function SetupLab
{
  param (
    [string]$labPath,
    [switch]$quiet
  )
  if (!($Env:LAB))
  {
    if ($labPath)
    {
      $env:LAB = $labPath
    }
    else
    {
      if ($env:DOTS)
      {
        $env:LAB = "$env:DOTS\lab"
      }
      else
      {
        $env:LAB = "$Env:USERPROFILE\lab"
      }
    }
    if (-not $quiet)
    {
      wh 'Setting up lab environment in ' Gray "$Env:LAB" blue -box -bb 1 -ba 2
    }
  }
  else
  {
    if ($labPath)
    {
      if (Test-Path $labPath)
      {
        if ($labPath -ne $Env:LAB)
        {
          $oldLab = "$Env:LAB\PowerShell"
          Set-Path -Remove -Path $oldLab
          if (-not $quiet)
          {
            wh 'Removed ' Gray "$oldLab" magenta ' from the PATH' Gray -box -bb 1 -ba 2
          }
          $Env:LAB = $labPath
          if (-not $quiet)
          {
            wh 'Setting up lab environment in ' Gray "$Env:LAB" blue -box -bb 1 -ba 2
          }
        }
        else
        {
          if (-not $quiet)
          {
            wh 'Lab environment already set up in ' Gray "$Env:LAB" blue -box -bb 1 -ba 2
          }
          return
        }
      }
      else
      {
        if (-not $quiet)
        {
          Write-Err $Path Magenta ' does not exist.' Gray -box
        }
        return
      }
    }
  }
  $labPath = $Env:LAB
  $Global:LAB = $env:LAB

  if (!(Test-Path($env:LAB)))
  {
    New-Item -ItemType Directory -Path $env:LAB -ErrorAction Stop | Out-Null
    if (-not $quiet)
    {
      Write-Success 'Created lab directory: ' Gray "$env:LAB" Blue -box
    }
  }
  $env:PSLAB = "$env:LAB\PowerShell"
  $Global:PSLAB = $env:PSLAB
  if (!(Test-Path($env:PSLAB)))
  {
    New-Item -ItemType Directory -Path $env:PSLAB -ErrorAction Stop | Out-Null
    if (-not $quiet)
    {
      Write-Success 'Created lab directory: ' Gray "$env:LAB" Blue -box

    }
  }
  if ($env:PATH -notlike "*$env:PSLAB*")
  {
    Set-Path -Add -Path $env:PSLAB
    if (-not $quiet)
    {
      Write-Success 'Added ' Gray "$env:PSLAB" Blue ' to the PATH' Gray -box
    }

  }
  if (-not $quiet)
  {
    Write-Success 'Lab environment set up in ' Gray "$env:LAB" Blue -box
  }
}
if (!($env:LAB))
{
  SetupLab -quiet
}

if ($env:PSCRIPTS)
{
  if (Test-Path -Path $env:PSCRIPTS)
  {
    $Global:PSCRIPTS = $env:PSCRIPTS
  }
}
else
{
  $PSScriptsDir = (Get-ItemProperty -Path $PROFILE).DirectoryName + '\Scripts'
  if (Test-Path -Path $PSScriptsDir)
  {
    $env:PSCRIPTS = $PSScriptsDir
    $Global:PSCRIPTS = $env:PSCRIPTS
  }
}

function Get-LabUsage
{
  $bannerPath = Join-Path -Path $modulePath -ChildPath 'banner'
  if (Test-Path -Path $bannerPath)
  {
    Write-Host
    Get-Content -Path $bannerPath | Write-Host
  }
  else
  {
    wh 'LAB' cyan
  }
  wh '  Usage: ' blue 'lab' cyan -padin 3 -bb 1 -ba 0
  Write-Output @'
 [-new] [-edit] [-tested] [-delete] [-filename <string>] [-list] [-help] [-dot] [-cat] [-setup] [-labPath <string>] [-quiet]

    -new       : Creates a new script in the lab.
    -edit      : Edit lab script.
    -tested    : Indicates if the script has been tested.
    -delete    : Removes the script from the lab.
    -filename  : The name of the file to be created, moved, edited, or deleted.
    -list      : Lists all lab scripts.
    -help      : Displays this help message.
    -dot       : Indicates that the script should be moved to the scripts directory.
    -cat       : Displays the content of the script file.
    -setup     : Sets up the lab environment.
    -labPath   : Specifies the path to the lab directory.
    -quiet     : Suppresses output messages.
'@
  linebreak
  return
}


function Get-LabScripts
{
  # PowerShellIcon = $psdoticon

  <#
    .SYNOPSIS
        Provides functions for testing PowerShell scripts.
    .DESCRIPTION
        This module contains functions and utilities to assist with testing PowerShell scripts.
    .EXAMPLE
        Import-Module -Name lab
        # This will import the lab module for use in your PowerShell session.
    .NOTES
        Author: njen
        Version: 1.0.0
    #>
  param (
    [string]$TargetScriptDir,
    [string]$targeticon,
    [string]$targetcolor
  )

  $sysparams = @(
    'Verbose', 'Debug', 'ErrorAction', 'WarningAction', 'InformationAction', 'ErrorVariable',
    'WarningVariable', 'InformationVariable', 'OutVariable', 'OutBuffer', 'PipelineVariable'
  )

  $aliases = @{}

  Get-Alias | ForEach-Object { if ($null -eq $aliases[$_.Definition]) { $aliases.Add($_.Definition, $_.Name) } }

  $scriptsPath = $TargetScriptDir

  Get-Command -CommandType ExternalScript | ForEach-Object `
  {
    $name = [IO.Path]::GetFileNameWithoutExtension($_.Name)
    if ($_.Source -like "$scriptsPath\*")
    {
      if ($catppuccin) { Write-Host "$($Flavor.sapphire.Foreground())  $ps1icon $($Flavor.text.Foreground())$name" -NoNewline }
      else
      {
        wh -pad 3 '󰨊' DarkBlue $name Gray
      }
      $parameters = $_.Parameters
      if ($null -ne $parameters)
      {
        $parameters.Keys | Where-Object { $sysparams -notcontains $_ } | ForEach-Object `
        {
          $p = $parameters[$_]
          $c = if ($p.ParameterType -like 'Switch') { 'DarkYellow' } else { 'DarkGray' }
          wh "-$_" $c
        }
      }

      $alias = $aliases[$name]
      if ($alias)
      {
        wh "($alias)" DarkGreen
      }
      linebreak
    }
  }
  linebreak
}


function lab
{
  <#
    .SYNOPSIS
        Powershell script management for lab environment.
    .DESCRIPTION
        This function provides options to create, test, list, edit, and delete PowerShell scripts within the lab environment.
    .PARAMETER new
        Creates a new script in the lab.
    .PARAMETER tested
        Moves the tested script from the lab to the scripts directory.
    .PARAMETER edit
        Edits an existing script in the lab.
    .PARAMETER delete
        Removes the script from the lab.
    .PARAMETER filename
        The name of the file to be created, moved, edited, or deleted.
    .PARAMETER list
        Lists all the lab scripts.
    .PARAMETER help
        Displays the help message for this function.
    .PARAMETER dot
        Indicates that the script should be moved to the scripts directory.
    .PARAMETER cat
        Displays the content of the script file.
    .PARAMETER setup
        Sets up the lab environment.
    .PARAMETER labPath
        Specifies the path to the lab directory.
    .PARAMETER quiet
        Suppresses output messages.
    .EXAMPLE
        lab -new -filename "NewScript"
        # This will create a new script "NewScript.ps1" in the lab.
    .EXAMPLE
        lab -tested -filename "TestScript"
        # This will move the tested script "TestScript.ps1" from the lab to the scripts directory.
    .EXAMPLE
        lab -edit -filename "EditScript"
        # This will open the script "EditScript.ps1" in the default editor.
    .EXAMPLE
        lab -delete -filename "OldScript"
        # This will delete the script "OldScript.ps1" from the lab.
    .EXAMPLE
        lab -list
        # This will list all the lab scripts.
    .EXAMPLE
        lab -help
        # This will display the help message.
    .EXAMPLE
        lab -cat -filename "ViewScript"
        # This will display the content of the script "ViewScript.ps1".
    .NOTES
        Author: njen
        Version: 1.0.0
    #>
  param (
    [switch]$help,
    [switch]$fzf,
    [switch]$dot,
    [switch]$new,
    [switch]$edit,
    [switch]$tested,
    [switch]$delete,
    [string]$filename,
    [switch]$list,
    [switch]$cat,
    [switch]$setup,
    [string]$labPath,
    [switch]$quiet = $false
  )

  $TargetScriptDir = $env:PSLAB
  $targeticon = $labicon
  $targetcolor = $labiconcolor


  if ($setup)
  {
    if ($labPath)
    {
      SetupLab -labPath $labPath -quiet:$quiet
      return
    }
    SetupLab -quiet:$quiet
    return
  }



  if ($dot)
  {
    $TargetScriptDir = $env:PSCRIPTS
    $targeticon = $psdoticon
    $targetcolor = $pscriptscolor
  }

  if ($help)
  {
    Get-LabUsage
    return
  }

  if ($new)
  {
    $filePath = "$TargetScriptDir\$filename.ps1"
    if (!(Test-Path $filePath))
    {
      New-Item -Path $filePath -ItemType File -ErrorAction Stop | Out-Null
      Write-Success 'Created: ' Green "$TargetScriptDir\" darkblue "$filename" gray '.ps1' white -box -bb 1 -ba 2
      return
    }
    else
    {
      Write-Warn "$filename" cyan '.ps1' DarkCyan ' already exists in ' Gray $TargetScriptDir blue -box
      return
    }
  }

  if ($edit)
  {
    if ($edit -eq '')
    {
      $Path = "$TargetScriptDir"
      $patherror = "'$TargetScriptDir' not found."
    }
    else
    {
      $Path = "$TargetScriptDir\$filename.ps1"
      $patherror = "File '$filename.ps1' not found in '$TargetScriptDir'."
    }
    if (Test-Path $Path)
    {
      if ($env:EDITOR)
      {
        & $env:EDITOR $Path
        return
      }
      else
      {
        Write-Err '$EDITOR' Magenta ' environment variable not set.' Gray -box
        return
      }
    }
    else
    {
      Write-Err "$patherror" magenta -box
      return
    }
  }

  if ($tested)
  {
    $filePath = "$PSLAB\$filename.ps1"
    if (Test-Path $filePath)
    {
      $destination = "$env:PSCRIPTS\$filename.ps1"
      Move-Item -Path $filePath -Destination $destination -ErrorAction Stop | Out-Null
      wh ' ' cyan "$filename.ps1" white ' --> ' DarkBlue "$env:PSCRIPTS\" Blue "$filename.ps1" Green -box -bb 1 -ba 1
      return
    }
    else
    {
      Write-Err "$filename" cyan '.ps1' DarkCyan ' already exists in ' Gray "$PSLAB" blue -box -bb 1 -ba 1
      return
    }
  }

  if ($delete)
  {
    $filePath = "$TargetScriptDir\$filename.ps1"
    if (Test-Path $filePath)
    {
      Remove-Item -Path $filePath -ErrorAction Stop | Out-Null
      wh '  ' red 'Deleted ' magenta "$TargetScriptDir\" darkred "$filename.ps1" magenta -box -bb 1 -ba 2
      return
    }
    else
    {
      Write-Err "$filename.ps1 " magenta 'not found in ' Gray "$TargetScriptDir" darkmagenta -box -bb 1 -ba 1
      return
    }
  }

  if ($cat)
  {
    $command = if (Test-CommandExists bat) { 'bat' }
    elseif (Test-CommandExists cat) { 'cat' }
    else
    {
      Write-Err 'No command found to display file contents' Gray -box
      return
    }
    $filePath = "$TargetScriptDir\$filename.ps1"
    if (Test-Path $filePath)
    {
      & $command $filePath
      return
    }
    else
    {
      Write-Err "$filename.ps1 " magenta 'not found in ' Gray "$TargetScriptDir" darkred -box
      return
    }
  }

  if ($list)
  {
    wh 'Listing scripts in ' darkcyan "$TargetScriptDir" blue -box -bb 1 -ba 2
    Get-LabScripts $TargetScriptDir $targeticon $targetcolor
    return
  }
  Get-LabUsage
  return
}
