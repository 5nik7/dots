$modulePath = $PSScriptRoot

function Add-Path {
  param (
    [Parameter(Mandatory = $true)]
    [string]$Path
  )
  if (Test-Path $Path) {
    if (-not ($env:Path -split ';' | Select-String -SimpleMatch $Path)) {
      $env:Path += ";$Path"
    }
  }
  else {
    Write-Err "Path $Path does not exist"
  }
}


function Add-PrependPath {
  param (
    [Parameter(Mandatory = $true)]
    [string]$Path
  )
  if (Test-Path $Path) {
    if (-not ($env:Path -split ';' | Select-String -SimpleMatch $Path)) {
      $env:Path = "$Path;$env:Path"
    }
  }
  else {
    Write-Err "Path $Path does not exist"
  }
}

function Remove-Path {
  param (
    [Parameter(Mandatory = $true)]
    [string]$Path
  )
  if ($env:Path -split ';' | Select-String -SimpleMatch $Path) {
    $env:Path = ($env:Path -split ';' | Where-Object { $_ -ne $Path }) -join ';'
  }
  else {
    Write-Err "Path $Path does not exist"
  }
}

function Remove-DuplicatePaths {
  $paths = $env:Path -split ';'
  $uniquePaths = [System.Collections.Generic.HashSet[string]]::new()
  $newPath = @()

  foreach ($path in $paths) {
    if ($uniquePaths.Add($path)) {
      $newPath += $path
    }
    else {
      Write-Verbose "Duplicate path detected and removed: $path"
    }
  }

  $env:Path = $newPath -join ';'
  Write-Verbose "Duplicate paths have been removed. Updated PATH: $env:Path"
}

function powerpath {
  [CmdletBinding()]
  param (
    [switch]$help,
    [switch]$v,
    [switch]$i,
    [string]$Path,
    [switch]$rm,
    [switch]$append,
    [switch]$prepend,
    [switch]$fix
  )

  if ($help -or $path -eq '') {
    $bannerPath = Join-Path -Path $modulePath -ChildPath 'banner'
    if (Test-Path -Path $bannerPath) {
      linebreak
      Get-Content -Path $bannerPath | Write-Host
    }
    wh 'Options:' darkgray -bb 1 -ba 1 -padout $env:padding
    wh '  -Path ' yellow ' <string>' green '   The path to add or remove.' Gray -bb 1 -ba 1 -padout $env:padding
    wh '  -v' yellow '                Verbose output.' Gray -bb 1 -ba 1 -padout $env:padding
    wh '  -i' yellow '                Interactive mode.' Gray -bb 1 -ba 1 -padout $env:padding
    wh '  -append' yellow '           Append the path.' Gray -bb 1 -ba 1 -padout $env:padding
    wh '  -prepend' yellow '          Prepend the path.' Gray -bb 1 -ba 1 -padout $env:padding
    wh '  -rm' yellow '               Remove the path.' Gray -bb 1 -ba 1 -padout $env:padding
    wh '  -help' yellow '             Show this help message.' Gray -bb 1 -ba 1 -padout $env:padding

  }
}

of ($fix) {
  $env:Path = $env:Path -split ';' | Where-Object { $_ -ne '' } | Sort-Object -Unique -CaseSensitive -Descending | Out-String
  $env:Path = $env:Path -replace '\s+', ' '
  $env:Path = $env:Path.Trim()
  Write-Info 'PATH fixed.'
}

if (Test-Path -PathType Container -Path $Path) {
  $Path = Resolve-Path $Path
  if ($v) { Write-Info 'Path exists.' }
  if ($rm) {
    if ($env:Path -split ';' | Select-String -SimpleMatch $Path) {
      if ($v) { Write-Info "$Path is on the Path." }
      if ($i) {
        $chice = (ask "Would you like to remove $Path from the path?")
        if ($chice -eq $true) {
          Remove-Path -Path $Path
          if ($v) { Write-Success "$Path has been removed." }
        }
        else {
          if ($v) { Write-Host 'Exiting.' }
          return
        }
      }
      else {
        Remove-Path -Path $Path
        if ($v) { Write-Success "$Path has been removed." }
      }
    }
    else {
      if ($v) { Write-Info "$Path is not on the path." }
    }
  }
  if ($append) {
    if ($i) {
      $chice = (ask "Would you like to add $Path to the end of the path?")
      if ($chice -eq $true) {
        Add-Path -Path $Path
        if ($v) { Write-Success "$Path has been added to the end of the path." }
      }
      else {
        if ($v) { Write-Warn 'Exiting...' }
      }
    }
    else {
      Add-Path -Path $Path
      if ($v) { Write-Success "$Path has been added to the end of the path." }
    }
    elseif ($prepend) {
      if ($i) {
        $chice = (ask "Would you like to add $Path to the beginning of the path?")
        if ($chice -eq $true) {
          Add-PrependPath -Path $Path
          if ($v) { Write-Success "$Path has been added to the beginning of the path." }
        }
        else {
          if ($v) { Write-Warn 'Exiting...' }
        }
      }
      else {
        Add-PrependPath -Path $Path
        if ($v) { Write-Success "$Path has been added to the beginning of the path." }
      }
    }
    Remove-DuplicatePaths
    if ($v) { Write-Info 'Duplicate paths removed.' }
  }
}

else {
  if ($v) { Write-Warn 'Path does not exist.' }
}
