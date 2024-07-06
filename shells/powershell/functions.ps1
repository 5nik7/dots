function gc {
  param(
    [Parameter(Mandatory = $true)]
    [string]$url,
    [Parameter(Mandatory = $false)]
    [string]$dir
  )

  if ($url -match '.git$') {
    if ($dir) {
      git clone $url $dir
    }
    else {
      git clone $url
    }
  }
  else {
    Write-Error "The provided URL does not end with .git"
  }
}
function gup {
  if (Test-Path .git) {
    $commitDate = Get-Date -Format "yyyy-MM-dd HH:mm"
    git add .
    git commit -m "Update @ $commitDate"
    git push
  }
  else {
    Write-Error "This directory does not contain a .git directory"
  }
}

function ga {
  git add .
}

function gp {
  git pull
}

function gcm {
  $commitDate = Get-Date -Format "yyyy-MM-dd HH:mm"
  git commit -m "Update @ $commitDate"
}

function gps {
  git push
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
    curl -s "wttr.in/Yakima?0uFq"
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

function .d {
  Set-Location "$env:PROJECTS\dots"
}

function .f {
  Set-Location "$env:DOTFILES"
}

function .e {
  (& $env:EDITOR "$env:PROJECTS\dots")
}

function pro {
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

function Fresh {
  & $PROFILE
  Write-Host -ForegroundColor DarkGray '┌───────────────────┐'
  Write-Host -ForegroundColor DarkGray '│' -NoNewline
  Write-Host -ForegroundColor Cyan ' Profile reloaded. ' -NoNewline
  Write-Host -ForegroundColor DarkGray '│'
  Write-Host -ForegroundColor DarkGray '└───────────────────┘'
}