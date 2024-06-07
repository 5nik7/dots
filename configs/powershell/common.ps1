function Fresh {
  & $PROFILE
  Write-Host ''
  Write-Host -ForegroundColor Black '┌───────────────────┐'
  Write-Host -ForegroundColor Black '│' -NoNewline
  Write-Host -ForegroundColor DarkCyan ' Profile reloaded. ' -NoNewline
  Write-Host -ForegroundColor Black '│'
  Write-Host -ForegroundColor Black '└───────────────────┘'
}
Set-Alias -Name rlp -Value Fresh

function ya {
  $tmp = [System.IO.Path]::GetTempFileName()
  yazi $args --cwd-file="$tmp"
  $cwd = Get-Content -Path $tmp
  if (-not [String]::IsNullOrEmpty($cwd) -and $cwd -ne $PWD.Path) {
    Set-Location -Path $cwd
  }
  Remove-Item -Path $tmp
}
Set-Alias -Name d -Value ya

function fbak {
  $command = "fd --hidden --follow -e bak"
  Invoke-Expression $command
}

function ll {
  Write-Host " "
  eza -lA --git --git-repos --icons --group-directories-first --no-quotes
}

function l {
  Write-Host " "
  eza -lA --git --git-repos --icons --group-directories-first --no-quotes --no-permissions --no-filesize --no-user --no-time
}

function envl {
  Write-Host " "
  Get-ChildItem Env:
}

function touch($file) {
  "" | Out-File $file -Encoding ASCII
}

function which($name) {
  Get-Command $name | Select-Object -ExpandProperty Definition
}

function Export-EnvironmentVariable {
  param(
    [Parameter(Mandatory = $true)]
    [string]$Name,
    [Parameter(Mandatory = $true)]
    [string]$Value
  )
  Set-Item -Force -Path "env:$Name" -Value $Value
}
Set-Alias -Name export -Value Export-EnvironmentVariable

Function Search-Alias {
  param (
    [string]$alias
  )
  if ($alias) {
    Get-Alias | Where-Object DisplayName -Match $alias
  }
  else {
    Get-Alias
  }
}

function q {
  Exit
}

function pathl {
  $env:Path -split ';'
}

function .. {
  Set-Location ".."
}

function lg {
  lazygit
}

function rmf($file) {
  Remove-Item $file -Recurse -Force -Verbose -confirm:$false
}

function colors {
  $colors = [enum]::GetValues([System.ConsoleColor])

  Foreach ($bgcolor in $colors) {
    Foreach ($fgcolor in $colors) { Write-Host "$fgcolor|"  -ForegroundColor $fgcolor -BackgroundColor $bgcolor -NoNewLine }

    Write-Host " on $bgcolor"
  }
}

function ln {
  param(
    [Parameter(Mandatory = $true)]
    [string]$base,

    [Parameter(Mandatory = $true)]
    [string]$target
  )

  try {
    if ((Test-Path -Path $target) -and (Get-Item -Path $target).Target -eq $base) {
      Write-Host ''
      Write-Host -ForegroundColor Yellow "Already a symlink."
      Write-Host ''
    }
    elseif (Test-Path -Path $target) {
      $bakDate = Get-Date -Format "yyyy-MM-dd_HH-mm"
      Rename-Item -Path $target -NewName "$target.$bakDate.bak" -ErrorAction Stop | Out-Null
      Write-Host ''
      Write-Host -ForegroundColor Black "────────────────────────────────────────────────────────────"
      Write-Host ''
      Write-Host -ForegroundColor Yellow "Creating a backup file: " -NoNewline
      Write-Host -ForegroundColor White "$target.$bakDate.bak"
      Write-Host ''
      New-Item -ItemType SymbolicLink -Path $target -Target $base -ErrorAction Stop | Out-Null
      Write-Host -ForegroundColor DarkCyan "$base" -NoNewline
      Write-Host -ForegroundColor DarkGray " 󱦰 " -NoNewline
      Write-Host -ForegroundColor DarkBlue "$target"
      Write-Host ''
      Write-Host -ForegroundColor Black "────────────────────────────────────────────────────────────"
      Write-Host ''
    }
    else {
      New-Item -ItemType SymbolicLink -Path $target -Target $base -ErrorAction Stop | Out-Null
      Write-Host ''
      Write-Host -ForegroundColor Black "────────────────────────────────────────────────────────────"
      Write-Host ''
      Write-Host -ForegroundColor DarkCyan "$base" -NoNewline
      Write-Host -ForegroundColor DarkGray " 󱦰 " -NoNewline
      Write-Host -ForegroundColor DarkBlue "$target"
      Write-Host ''
      Write-Host -ForegroundColor Black "────────────────────────────────────────────────────────────"
      Write-Host ''
    }
  }
  catch {
    Write-Output "Failed to create symbolic link: $_"
  }
}

function bak {
  param(
    [Parameter(Mandatory = $false)]
    [string]$Path = (Get-Location).Path,
    [switch]$s
  )

  $bakFiles = Get-ChildItem -Path $Path -Filter "*.bak" -Recurse -Force -ErrorAction SilentlyContinue
  $backupPath = Join-Path -Path $env:USERPROFILE -ChildPath "backups"

  foreach ($file in $bakFiles) {
    if ($s -and $file.FullName -notlike "$backupPath\*") {
      $destination = Join-Path -Path $backupPath -ChildPath $file.
      Move-Item -Path $file.FullName -Destination $destination -Force | Out-Null
      Write-Host "Moved $file.FullName to $destination"
    }
    else {
      Write-Host $file.FullName
    }
  }
}