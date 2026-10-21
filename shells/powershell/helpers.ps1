# Personal helpers; definitions only, no external startup work.
function Edit-Item {
  param([string] $Path = $PWD.Path)
  if (-not $env:EDITOR) {
    foreach ($candidate in 'nvim', 'code', 'vim', 'vi', 'notepad') {
      if (Get-Command $candidate -CommandType Application -ErrorAction Ignore) {
        $env:EDITOR = $candidate
        break
      }
    }
  }
  if (-not $env:EDITOR) { throw 'No editor found; set $env:EDITOR to an executable.' }
  & $env:EDITOR $Path
}

function c {
  Clear-Host
}

function Invoke-eza {
  if (Get-Command eza -CommandType Application -ErrorAction Ignore) {
    eza --icons=auto --group-directories-first @args
  } else { Get-ChildItem @args }
}

function env {
  Get-ChildItem env:
}

function RepeatString {
  param(
    [string]$Text,
    [int]$Count
  )

  if ($Count -le 0 -or $null -eq $Text) {
    return ''
  }

  $Text * $Count
}

function Import-ScoopModule {
  param (
    [Parameter()]
    $Name
  )
  Import-Module "$($(Get-Item $(Get-Command scoop.ps1).Path).Directory.Parent.FullName)\modules\$Name" -Global
}

function Clear-Cache {
  # add clear cache logic here
  Write-Host 'Clearing cache...' -ForegroundColor Cyan

  # Clear Windows Prefetch
  Write-Host 'Clearing Windows Prefetch...' -ForegroundColor Yellow
  Remove-Item -Path "$env:SystemRoot\Prefetch\*" -Force -ErrorAction SilentlyContinue

  # Clear Windows Temp
  Write-Host 'Clearing Windows Temp...' -ForegroundColor Yellow
  Remove-Item -Path "$env:SystemRoot\Temp\*" -Recurse -Force -ErrorAction SilentlyContinue

  # Clear User Temp
  Write-Host 'Clearing User Temp...' -ForegroundColor Yellow
  Remove-Item -Path "$env:TEMP\*" -Recurse -Force -ErrorAction SilentlyContinue

  # Clear Internet Explorer Cache
  Write-Host 'Clearing Internet Explorer Cache...' -ForegroundColor Yellow
  Remove-Item -Path "$env:LOCALAPPDATA\Microsoft\Windows\INetCache\*" -Recurse -Force -ErrorAction SilentlyContinue

  Write-Host 'Cache clearing completed.' -ForegroundColor Green
}

function Edit-Profile { Edit-Item (Join-Path $env:PWSH 'profile.ps1') }

function Get-PubIP { (Invoke-WebRequest http://ifconfig.me/ip).Content }

function winutil { Invoke-RestMethod https://christitus.com/win | Invoke-Expression }

function trash($path) {
  $trashicon = ''
  if (-not $path) {
    Write-Host -foregroundColor Blue -NoNewline "$trashicon Usage: "
    Write-Host -foregroundColor Cyan -NoNewline "trash "
    Write-Host -foregroundColor White "<path-to-file-or-directory>"
    return
  }

  $fullPath = (Resolve-Path -LiteralPath $path -ErrorAction Stop).Path

  if (Test-Path -LiteralPath $fullPath) {
    $item = Get-Item -LiteralPath $fullPath

    if ($item.PSIsContainer) {
      # Handle directory
      $parentPath = $item.Parent.FullName
    }
    else {
      # Handle file
      $parentPath = $item.DirectoryName
    }

    $shell = New-Object -ComObject 'Shell.Application'
    $shellItem = $shell.NameSpace($parentPath).ParseName($item.Name)

    if ($shellItem) {
      $shellItem.InvokeVerb('delete')
      Write-Host -foregroundColor Green "$trashicon Item '$fullPath' has been moved to the Recycle Bin."
    }
    else {
      Write-Host "Error: Could not find the item '$fullPath' to trash."
    }
  }
  else {
    Write-Host "Error: Item '$fullPath' does not exist."
  }
}

function cpy { clip.exe }

function pst { Get-Clipboard }

function touch {
  param([Parameter(Mandatory, Position=0)][string] $File)
  $path = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($File)
  $stream = [IO.File]::Open($path, [IO.FileMode]::OpenOrCreate, [IO.FileAccess]::Write, [IO.FileShare]::Read)
  $stream.Dispose()
  [IO.File]::SetLastWriteTimeUtc($path, [DateTime]::UtcNow)
}

function export($name, $value) {
  set-item -force -path "env:$name" -value $value;
}

function pkill($name) {
  Get-Process $name -ErrorAction SilentlyContinue | Stop-Process
}

function greps($regex, $dir) {
  if ( $dir ) {
    Get-ChildItem $dir | select-string $regex
    return
  }
  $input | select-string $regex
}

function pgrep($name) { Get-Process $name }

function head {
  param($Path, $n = 10)
  Get-Content -LiteralPath $Path -Head $n
}

function tail {
  param($Path, $n = 10, [switch]$f = $false)
  Get-Content -LiteralPath $Path -Tail $n -Wait:$f
}

function df { get-volume }

function mkcd {
  param($dir) mkdir $dir -Force; Set-Location $dir
}

function sysinfo { Get-ComputerInfo }

function unzip ($file) {
  Write-Output('Extracting', $file, 'to', $pwd)
  $fullFile = Get-ChildItem -Path $pwd -Filter $file | ForEach-Object { $_.FullName }
  Expand-Archive -Path $fullFile -DestinationPath $pwd
}

function docs {
  $docs = if (([Environment]::GetFolderPath('MyDocuments'))) { ([Environment]::GetFolderPath('MyDocuments')) } else { $HOME + '\Documents' }
  Set-Location -Path $docs
}

function dd {
  $currentDirectory = Resolve-Path "$PWD"
  start-process explorer.exe "$currentDirectory"
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

function Find-File {
  <#
    .SYNOPSIS
        Finds a file in the current directory and all subdirectories. Alias: ff
    #>
  [CmdletBinding()]
  param (
    [Parameter(ValueFromPipeline, Mandatory = $true, Position = 0)]
    [string]$SearchTerm
  )

  Write-Verbose "Searching for '$SearchTerm' in current directory and subdirectories"
  $result = Get-ChildItem -Recurse -Filter "*$SearchTerm*" -ErrorAction SilentlyContinue

  Write-Verbose 'Outputting results to table'
  $result | Format-Table -AutoSize
}

function Find-String {
  <#
    .SYNOPSIS
        Searches for a string in a file or directory. Alias: grep
    #>
  [CmdletBinding()]
  param (
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$SearchTerm,
    [Parameter(ValueFromPipeline, Mandatory = $false, Position = 1)]
    [string]$Directory,
    [Parameter(Mandatory = $false)]
    [switch]$Recurse
  )

  Write-Verbose "Searching for '$SearchTerm' in '$Directory'"
  if ($Directory) {
    if ($Recurse) {
      Write-Verbose "Searching for '$SearchTerm' in '$Directory' and subdirectories"
      Get-ChildItem -Recurse $Directory | Select-String $SearchTerm
      return
    }

    Write-Verbose "Searching for '$SearchTerm' in '$Directory'"
    Get-ChildItem $Directory | Select-String $SearchTerm
    return
  }

  if ($Recurse) {
    Write-Verbose "Searching for '$SearchTerm' in current directory and subdirectories"
    Get-ChildItem -Recurse | Select-String $SearchTerm
    return
  }

  Write-Verbose "Searching for '$SearchTerm' in current directory"
  Get-ChildItem | Select-String $SearchTerm
}

function Show-Command {
  [CmdletBinding()]
  param (
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$Name
  )
  if (-not (Test-CommandExists $Name)) {
    Write-Error "Command not found: $Name"
    return
  }
  Write-Verbose "Showing definition of '$Name'"
  Get-Command $Name | Select-Object -ExpandProperty Definition
}

function datb($1) {
  if ($catppuccin.Macchiato.Base) { $border = $catppuccin.Macchiato.Base.ToString() } else { $border = 'black' };
  rich -y -a square -S $border -d 1 --theme catppuccin-mocha -m $1
}

function dat($1) { rich --pager --text-full -y -e -d 1 -m $1 }

function open {
  param (
    [Parameter(Mandatory = $true, ValueFromRemainingArguments = $true)]
    [string[]]$Paths
  )
  foreach ($path in $Paths) {
    Start-Process $path
  }
}

function google {
  param (
    [Parameter(Mandatory = $true, ValueFromRemainingArguments = $true)]
    [string[]]$QueryParts
  )
  $query = [string]::Join(' ', $QueryParts)
  $encodedQuery = [Uri]::EscapeDataString($query)
  $url = "https://www.google.com/search?q=$encodedQuery"
  Start-Process $url
}

function q { Exit }

function .d { Set-Location "$env:DOTS" }

function .df { Set-Location "$env:DOTFILES" }

function cdev { Set-Location "$env:DEV" }

function .. { Set-Location '..' }

function ... { Set-Location '..\..' }

function .... { Set-Location '..\..\..' }

function ..... { Set-Location '..\..\..\..' }

function Get-Functions { Get-ChildItem function:\ }

function find-ln { Get-ChildItem | Where-Object { $_.Attributes -match 'ReparsePoint' } }

function nerdfonts {
  param (
    [Parameter(ValueFromRemainingArguments = $true)]
    $OptionalParameters
  )
  & ([scriptblock]::Create((Invoke-WebRequest 'https://to.loredo.me/Install-NerdFont.ps1').Content)) @OptionalParameters
}

function Remove-DuplicatePSReadlineHistory {
  $historyPath = (Get-PSReadLineOption).HistorySavePath

  # backup
  $directory = (Get-Item $historyPath).DirectoryName
  $basename = (Get-Item $historyPath).Basename
  $extension = (Get-Item $historyPath).Extension
  $timestamp = (Get-Date).ToString('yyyy-MM-ddTHH-mm-ssZ')

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

function git_all {
  param(
    [Parameter(ValueFromRemainingArguments = $true)]
    $Args
  )
  $gitusername = git config get --global user.name
  if (Test-Path .git) {
    # Check remote access before running commands
    $hasAccess = $true
    $remoteUrl = git remote get-url origin 2>$null
    if (-not $remoteUrl -or ($remoteUrl -notmatch $gitusername)) {
      # Write-Host "Remote does not contain username '$gitusername'. Cannot run git commands." -ForegroundColor Yellow
      return
    }
    try {
      git ls-remote > $null 2>&1
    }
    catch {
      $hasAccess = $false
    }
    if (-not $hasAccess) {
      # Write-Host "Skipping main repo (no remote access or permission denied)" -ForegroundColor Yellow
      return
    }
    git @Args
    # Get submodule paths from .gitmodules
    $submodules = @()
    if (Test-Path .gitmodules) {
      $submodules = git config --file .gitmodules --get-regexp path | ForEach-Object {
        $_ -replace '^[^ ]+ ', ''
      }
    }
    foreach ($sub in $submodules) {
      if (Test-Path $sub) {
        Push-Location $sub
        # Try a harmless git command to check access
        $subHasAccess = $true
        $subRemoteUrl = git remote get-url origin 2>$null
        if (-not $subRemoteUrl -or ($subRemoteUrl -notmatch $gitusername)) {
          # Write-Host "Submodule '$sub' remote does not contain username '$gitusername'. Skipping." -ForegroundColor Yellow
          Pop-Location
          continue
        }
        try {
          git ls-remote > $null 2>&1
        }
        catch {
          $subHasAccess = $false
        }
        if ($subHasAccess) {
          git @Args
        }
        else {
          # Write-Host "Skipping submodule '$sub' (no permission or inaccessible)" -ForegroundColor Yellow
        }
        Pop-Location
      }
    }
  }
  else {
    Write-Error 'This directory does not contain a .git directory'
  }
}

function gup {
  param(
    [Parameter(Position = 0)]
    [string]$Message,
    [switch]$All
  )
  $gitusername = git config get --global user.name
  if (Test-Path .git) {
    $remoteUrl = git remote get-url origin 2>$null
    if (-not $remoteUrl -or ($remoteUrl -notmatch $gitusername)) {
      # Write-Host "Remote does not contain username '$gitusername'. Cannot push or fetch from remote." -ForegroundColor Yellow
      return
    }
    $commitMessage = if ($Message) { $Message } else { "Update @ $(Get-Date -Format 'MM-dd-yyyy HH:mm')" }
    if ($All) {
      git_all add .
      # Check for staged changes
      $status = git_all diff --cached --name-only
      if ($status) {
        git_all commit -m "$commitMessage"
        git_all push
      }
      else {
        Write-Host "No changes to commit." -ForegroundColor Yellow
      }
    }
    else {
      git add .
      $status = git diff --cached --name-only
      if ($status) {
        git commit -m "$commitMessage"
        git push
      }
      else {
        Write-Host "No changes to commit." -ForegroundColor Yellow
      }
    }
  }
  else {
    Write-Error 'This directory does not contain a .git directory'
  }
}

function New-Backup {
  [CmdletBinding(SupportsShouldProcess)]
  param([Parameter(Mandatory, Position=0)][string] $Target, [switch] $Store, [switch] $Copy)
  $item = Get-Item -LiteralPath $Target -Force -ErrorAction Stop
  $parent = if ($item.PSIsContainer) { $item.Parent.FullName } else { $item.DirectoryName }
  if (-not $parent) { throw 'Cannot back up a filesystem root.' }
  $directory = if ($Store) { Join-Path $HOME '.bakstore' } else { $parent }
  $name = $item.Name + '.' + [DateTime]::UtcNow.ToString('yyyyMMdd-HHmmssfffffff') + '.' + [guid]::NewGuid().ToString('N') + '.bak'
  $destination = Join-Path $directory $name
  if ($PSCmdlet.ShouldProcess($item.FullName, "Back up to $destination")) {
    if (-not [IO.Directory]::Exists($directory)) { [void][IO.Directory]::CreateDirectory($directory) }
    if ($Copy) { Copy-Item -LiteralPath $item.FullName -Destination $destination -Recurse -ErrorAction Stop }
    else { Move-Item -LiteralPath $item.FullName -Destination $destination -ErrorAction Stop }
    $destination
  }
}


function Test-CommandExists {
  param([string] $Command)
  $null -ne (Get-Command $Command -ErrorAction Ignore)
}

function y {
  $command = Get-Command yazi -CommandType Application -ErrorAction Stop
  $tempFile = [IO.Path]::GetTempFileName()
  try {
    & $command @args "--cwd-file=$tempFile"
    $cwd = [IO.File]::ReadAllText($tempFile).TrimEnd("`r", "`n")
    if ($cwd -and (Test-Path -LiteralPath $cwd -PathType Container)) { Set-Location -LiteralPath $cwd }
  } finally { Remove-Item -LiteralPath $tempFile -Force -ErrorAction SilentlyContinue }
}

function Invoke-DotsFuzzyCompletion {
  if (-not (Get-Command fzf -CommandType Application -ErrorAction Ignore)) {
    [Microsoft.PowerShell.PSConsoleReadLine]::TabCompleteNext()
    return
  }
  try {
    if (-not (Get-Module PSFzf)) { Import-Module PSFzf -Global -ErrorAction Stop }
  } catch {
    [Microsoft.PowerShell.PSConsoleReadLine]::TabCompleteNext()
    return
  }
  Invoke-FzfTabCompletion
}

