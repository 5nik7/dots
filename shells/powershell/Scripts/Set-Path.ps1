function Add-Path
{
  param (
    [Parameter(Mandatory = $true)]
    [string]$Path
  )
  if (Test-Path $Path)
  {
    if (-not ($env:Path -split ';' | Select-String -SimpleMatch $Path))
    {
      $env:Path += ";$Path"
    }
  }
  else
  {
    Write-Err $Path Magenta ' does not exist.'
  }
}
function Add-PrependPath
{
  param (
    [Parameter(Mandatory = $true)]
    [string]$Path
  )
  if (Test-Path $Path)
  {
    if (-not ($env:Path -split ';' | Select-String -SimpleMatch $Path))
    {
      $env:Path = "$Path;$env:Path"
    }
  }
  else
  {
    Write-Err $Path Magenta ' does not exist.'
  }
}
function Remove-Path
{
  param (
    [Parameter(Mandatory = $true)]
    [string]$Path
  )
  if ($env:Path -split ';' | Select-String -SimpleMatch $Path)
  {
    $env:Path = ($env:Path -split ';' | Where-Object { $_ -ne $Path }) -join ';'
  }
  else
  {
    Write-Err $Path Magenta ' does not exist.'
  }
}

function Add-PSModulePath
{
  param (
    [Parameter(Mandatory = $true)]
    [string]$Path
  )
  if (Test-Path $Path)
  {
    if (-not ($env:PSModulePath -split ';' | Select-String -SimpleMatch $Path))
    {
      $env:PSModulePath = $env:PSModulePath + $Path
    }
  }
  else
  {
    Write-Err $Path Magenta ' does not exist.'
  }
}

function Invoke-SetPath
{
  <#
  .SYNOPSIS
    Manage PATH and PSModulePath entries from PowerShell.

  .DESCRIPTION
    Invoke-SetPath is a helper wrapper that calls the local helper functions
    Add-Path, Add-PrependPath, Remove-Path and Add-PSModulePath to modify
    the current session's environment PATH or PSModulePath.

  .PARAMETER Path
    The filesystem path to add/remove. Supports a single path string.

  .PARAMETER Add
    Adds the path to the end of the PATH environment variable.

  .PARAMETER Prepend
    Adds the path to the beginning of the PATH environment variable.

  .PARAMETER Remove
    Removes the path from the PATH environment variable.

  .PARAMETER PSModule
    Adds the path to the PSModulePath environment variable.

  .PARAMETER Usage
    When specified, displays the function help and usage examples.

  .EXAMPLE
    Invoke-SetPath -Add 'C:\Tools' -Path

  .NOTES
    This modifies the environment variables for the current PowerShell session only.
  #>

  [CmdletBinding()]
  param(
    [Parameter(Mandatory = $false, Position = 0)]
    [string]$Path,

    [Parameter(Mandatory = $false)]
    [switch]$Add,

    [Parameter(Mandatory = $false)]
    [switch]$Prepend,

    [Parameter(Mandatory = $false)]
    [switch]$Remove,

    [Parameter(Mandatory = $false)]
    [switch]$PSModule,

    [Parameter(Mandatory = $false)]
    [switch]$Usage
  )

  begin
  {
    # Validate that helper functions exist in the session
    if (-not (Get-Command -Name Add-Path -ErrorAction SilentlyContinue))
    {
      Write-Error "Required helper function 'Add-Path' not found in session."
      return
    }
    if (-not (Get-Command -Name Add-PrependPath -ErrorAction SilentlyContinue))
    {
      Write-Error "Required helper function 'Add-PrependPath' not found in session."
      return
    }
    if (-not (Get-Command -Name Remove-Path -ErrorAction SilentlyContinue))
    {
      Write-Error "Required helper function 'Remove-Path' not found in session."
      return
    }
    if (-not (Get-Command -Name Add-PSModulePath -ErrorAction SilentlyContinue))
    {
      Write-Error "Required helper function 'Add-PSModulePath' not found in session."
      return
    }
  }

  process
  {
    if ($Usage)
    {
      Get-Help -Name Invoke-SetPath -Full -ErrorAction SilentlyContinue
      return
    }

    # If no action flags specified, show brief usage and return
    if (-not ($Add -or $Prepend -or $Remove -or $PSModule))
    {
      Write-Host 'No action specified. Use -Add, -Prepend, -Remove or -PSModule. Use -Usage for help.' -ForegroundColor Yellow
      return
    }

    if (-not $Path -and -not $PSModule)
    {
      Write-Error "-Path is required for Add/Prepend/Remove. Provide -Path '<folder>'"
      return
    }

    # Normalize the path (expand environment vars and resolve relative paths)
    try
    {
      if ($Path)
      {
        $resolved = (Resolve-Path -Path $Path -ErrorAction Stop).ProviderPath
      }
      else
      {
        $resolved = $null
      }
    }
    catch
    {
      Write-Error "Path '$Path' does not exist or cannot be resolved."
      return
    }

    if ($Add)
    {
      Add-Path -Path $resolved
    }

    if ($Prepend)
    {
      Add-PrependPath -Path $resolved
    }

    if ($Remove)
    {
      Remove-Path -Path $resolved
    }

    if ($PSModule)
    {
      if (-not $resolved)
      {
        Write-Error '-Path is required with -PSModule to add a PSModule path.'
        return
      }
      Add-PSModulePath -Path $resolved
    }
  }

  end
  {
    # Optionally output the updated variables for verification
    Write-Verbose "PATH length: $($env:Path.Length)"
  }
}

Invoke-Expression "Invoke-SetPath $args" -Verbose
