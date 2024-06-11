function g {
  param(
    [string]$arg
  )

  if ($arg -eq $null) {
    git
  }
  elseif ($arg -eq "p") {
    git pull
  }
  elseif ($arg -eq "a") {
    git add .
  }
  elseif ($arg -eq "c") {
    $commitDate = Get-Date -Format "yyyy-MM-dd HH:mm"
    git commit -m "Update @ $commitDate"
  }
  elseif ($arg -eq "s") {
    git push
  }
  elseif ($arg -eq "u") {
    git add .
    $commitDate = Get-Date -Format "yyyy-MM-dd HH:mm"
    git commit -m "Update @ $commitDate"
    git push
  }
  elseif ($arg -match ".git$") {
    git clone $arg
  }
  else {
    git
  }
}

function Get-Weather($arg) {
  if ($arg -eq "help") {
    curl -s "wttr.in/:help"
  }
  elseif ($arg -eq "0") {
    curl -s "wttr.in/Yakima?0uFq"
  }
  elseif ($arg -eq "1") {
    curl -s "wttr.in/Yakima?1uFq"
  }
  elseif ($arg -eq "2") {
    curl -s "wttr.in/Yakima?2uFq"
  }
  elseif ($arg -eq "all") {
    curl -s "wttr.in/Yakima?uFq"
  }
  else {
    curl -s "wttr.in/Yakima?0uFq" | grep --only-matching --color=always ..................°F
  }
}
function Edit-Profile {
  (& $env:EDITOR ([IO.Path]::GetDirectoryName($profile)))
}

function Get-Functions {
  Get-ChildItem function:\
}

function Test-CommandExists {
  param($command)
  $exists = $null -ne (Get-Command $command -ErrorAction SilentlyContinue)
  return $exists
}

# Editor Configuration
$EDITOR = if (Test-CommandExists code) { 'code' }
elseif (Test-CommandExists nvim) { 'nvim' }
elseif (Test-CommandExists vim) { 'vim' }
elseif (Test-CommandExists vi) { 'vi' }
else { 'notepad' }
$env:EDITOR = $EDITOR
function edit-item {
  param (
    [string]$Path = $PWD
  )

  if ($Path) {
    & $env:EDITOR $Path
  }
  else {
    & $env:EDITOR
  }
}

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

function dd {
  param (
    [string]$Path = $PWD
  )

  if ($Path) {
    explorer $Path
  }
  else {
    explorer
  }
}

function Remove-DuplicatePSReadlineHistory {
  $historyPath = (Get-PSReadLineOption).HistorySavePath

  # backup
  $directory = (Get-Item $historyPath).DirectoryName
  $basename = (Get-Item $historyPath).Basename
  $extension = (Get-Item $historyPath).Extension
  $timestamp = (Get-Date).ToString("yyyy-MM-ddTHH-mm-ssZ")

  $backupPath = "$directory\$basename-$timestamp-backup$extension"

  Copy-Item $historyPath $backupPath

  # remove duplicate history
  $uniqueHistory = @()
  $history = Get-Content $historyPath

  [Array]::Reverse($history)

  $history | ForEach-Object {
    if (-Not $uniqueHistory.Contains($_)) {
      $uniqueHistory += $_
    }
  }

  [Array]::Reverse($uniqueHistory)

  Clear-Content $historyPath

  $uniqueHistory | Out-File -Append $historyPath
}

function edit-history {
  & $env:EDITOR (Get-PSReadLineOption).HistorySavePath
}

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

function repos {
  Set-Location "$env:REPOS"
}

function .d {
  Set-Location "$env:PROJECTS\dots"
}

function .f {
  Set-Location "$env:DOTFILES"
}

function projects {
  Set-Location "$env:PROJECTS"
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

function Set-Link {
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
      $backupFileName = "$target.$bakDate.bak"
      Rename-Item -Path $target -NewName $backupFileName -ErrorAction Stop | Out-Null
      Write-Host ''
      Write-Host -ForegroundColor Yellow "Creating a backup file: " -NoNewline
      Write-Host -ForegroundColor White $backupFileName
      Write-Host ''
      New-Item -ItemType SymbolicLink -Path $target -Target $base -ErrorAction Stop | Out-Null
      Write-Host -ForegroundColor DarkCyan "$base" -NoNewline
      Write-Host -ForegroundColor DarkGray " 󱦰 " -NoNewline
      Write-Host -ForegroundColor DarkBlue "$target"
      Write-Host ''
    }
    else {
      New-Item -ItemType SymbolicLink -Path $target -Target $base -ErrorAction Stop | Out-Null
      Write-Host ''
      Write-Host -ForegroundColor DarkCyan "$base" -NoNewline
      Write-Host -ForegroundColor DarkGray " 󱦰 " -NoNewline
      Write-Host -ForegroundColor DarkBlue "$target"
      Write-Host ''
    }
  }
  catch {
    Write-Output "Failed to create symbolic link: $_"
  }
}

function Add-PathPrefix {
  param (
    [Parameter(Mandatory = $true)]
    [string]$Path
  )
  if (-not ($env:Path -split ';' | Select-String -SimpleMatch $Path)) {
    $env:Path = "$Path;" + $env:Path
  }
}

function Add-Path {
  param (
    [Parameter(Mandatory = $true)]
    [string]$Path
  )
  if (-not ($env:Path -split ';' | Select-String -SimpleMatch $Path)) {
    $env:Path += ";$Path"
  }
}

# $profileDirectory = [System.IO.Path]::GetDirectoryName($PROFILE)
# $envFilePath = Join-Path -Path $profileDirectory -ChildPath ".env"

# if (Test-Path $envFilePath) {
#   Get-Content $envFilePath | ForEach-Object {
#     $name, $value = $_.split('=')

#     if ([string]::IsNullOrWhiteSpace($name) -or $name.Contains('#')) {
#       continue
#     }

#     Set-Item -force -Path "env:$name" -Value $value
#   }
# }

function Find-RegistryUninstallKey {
  param($SearchFor, [switch]$Wow6432Node)
  $results = @()
  $keys = Get-ChildItem HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall |
  ForEach-Object {
    class x64 {
      [string]$GUID
      [string]$Publisher
      [string]$DisplayName
      [string]$DisplayVersion
      [string]$InstallLocation
      [string]$InstallDate
      [string]$UninstallString
      [string]$Wow6432Node
      [string]$RegistryKeyPath
    }
    $x64 = [x64]::new()
    $x64.GUID = $_.pschildname
    $x64.Publisher = $_.GetValue('Publisher')
    $x64.DisplayName = $_.GetValue('DisplayName')
    $x64.DisplayVersion = $_.GetValue('DisplayVersion')
    $x64.InstallLocation = $_.GetValue('InstallLocation')
    $x64.InstallDate = $_.GetValue('InstallDate')
    $x64.UninstallString = $_.GetValue('UninstallString')
    $x64.RegistryKeyPath = "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\$($_.pschildname)"
    if ($Wow6432Node) { $x64.Wow6432Node = 'No' }
    $results += $x64
  }
  if ($Wow6432Node) {
    $keys = Get-ChildItem HKLM:\SOFTWARE\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall |
    ForEach-Object {
      class x86 {
        [string]$GUID
        [string]$Publisher
        [string]$DisplayName
        [string]$DisplayVersion
        [string]$InstallLocation
        [string]$InstallDate
        [string]$UninstallString
        [string]$Wow6432Node
        [string]$RegistryKeyPath
      }
      $x86 = [x86]::new()
      $x86.GUID = $_.pschildname
      $x86.Publisher = $_.GetValue('Publisher')
      $x86.DisplayName = $_.GetValue('DisplayName')
      $x86.DisplayVersion = $_.GetValue('DisplayVersion')
      $x86.InstallLocation = $_.GetValue('InstallLocation')
      $x86.InstallDate = $_.GetValue('InstallDate')
      $x86.UninstallString = $_.GetValue('UninstallString')
      $x86.Wow6432Node = 'Yes'
      $x86.RegistryKeyPath = "HKLM:\SOFTWARE\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall\$($_.pschildname)"
      $results += $x86
    }
  }
  $results | Sort-Object DisplayName | Where-Object { $_.DisplayName -match $SearchFor }
}

