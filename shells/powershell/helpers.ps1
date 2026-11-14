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
  # The platform provider owns scope, review and unsupported-operation refusal.
  & (Join-Path $env:DOTS 'bin/dots.ps1') cleanup run @args
  $global:LASTEXITCODE = $LASTEXITCODE
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

function cpy {
  $launcher = Join-Path (Split-Path -Parent (Split-Path -Parent $PSScriptRoot)) 'scripts/cpy.ps1'
  if ($MyInvocation.ExpectingInput) { $input | & $launcher @args }
  else { & $launcher @args }
}

function pst {
  & (Join-Path (Split-Path -Parent (Split-Path -Parent $PSScriptRoot)) 'scripts/pst.ps1') @args
}

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
  param([string]$Directory)
  if (-not $Directory) { throw 'Usage: mkcd <directory>' }
  $provider = $null; $drive = $null
  $target = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath(
    $Directory, [ref]$provider, [ref]$drive)
  if ($provider.Name -ne 'FileSystem') { throw 'mkcd requires a filesystem directory.' }
  if ([IO.File]::Exists($target)) { throw ('mkcd: not a directory: ' + $Directory) }
  [void][IO.Directory]::CreateDirectory($target)
  Set-Location -LiteralPath $target -ErrorAction Stop
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
        Finds a file in the current directory and all subdirectories as a table.
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
  [CmdletBinding()]
  param(
    [Parameter(Position = 0)]
    [AllowEmptyString()]
    [string]$Message,
    [switch]$All,
    [switch]$Yes,
    [switch]$DryRun
  )
  if ($PWD.Provider.Name -ne 'FileSystem') { throw 'gup requires a filesystem directory.' }
  $forward = @('git', 'publish', '-C', $PWD.Path, '--no-wiki')
  if ($All) { $forward += '--all' }
  if ($Yes) { $forward += '--yes' }
  if ($DryRun) { $forward += '--dry-run' }
  if ($PSBoundParameters.ContainsKey('Message')) { $forward += @('--message', $Message) }
  & (Join-Path $env:DOTS 'bin/dots.ps1') @forward
  $global:LASTEXITCODE = $LASTEXITCODE
}

function New-Backup {
  [CmdletBinding(SupportsShouldProcess)]
  param([Parameter(Mandatory, Position=0)][string[]] $Target, [switch] $Store, [switch] $Copy, [switch] $InPlace)
  $forward = @('bak', 'create')
  if ($Copy) { $forward += '--copy' }
  if ($InPlace) { $forward += '--in-place' }
  if ($Store) { $forward += @('--store-dir', (Join-Path $HOME '.bakstore')) }
  if ($PSCmdlet.ShouldProcess(($Target -join ', '), 'Back up with Dots')) {
    & (Join-Path $env:DOTS 'bin/dots.ps1') @forward '--' @Target
  }
}


function Test-CommandExists {
  param([string] $Command)
  $null -ne (Get-Command $Command -ErrorAction Ignore)
}

function y {
  $command = Get-Command yazi -CommandType Application -TotalCount 1 -ErrorAction Stop
  $tempFile = [IO.Path]::GetTempFileName()
  $result = 1
  try {
    & $command @args "--cwd-file=$tempFile"
    $result = $LASTEXITCODE
    $cwd = [IO.File]::ReadAllText($tempFile).TrimEnd("`r", "`n")
    if ($result -eq 0 -and $cwd -and (Test-Path -LiteralPath $cwd -PathType Container)) {
      Set-Location -LiteralPath $cwd -ErrorAction Stop
    }
  } catch { $result = 1; throw }
  finally {
    Remove-Item -LiteralPath $tempFile -Force -ErrorAction SilentlyContinue
    $global:LASTEXITCODE = $result
  }
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


# Portable counterparts of shared Bash/Zsh helpers; definitions stay lazy.
function v { Edit-Item @args }
function n { if ($args.Count) { & nvim @args } else { & nvim . } }
function h { Get-History @args }
function path { $env:PATH -split [regex]::Escape([string][IO.Path]::PathSeparator) }
function p: { path }
function gcm { & git commit -m @args }
function gcam { & git commit -a -m @args }
function gcad { & git commit -a --amend @args }
function gst { & git status @args }
function in_git { & git rev-parse --is-inside-work-tree 2>$null }
function gitcheck {
  $paths = @($args); $verbose = $false
  if ($paths.Count -and $paths[0] -in @('-v', '--verbose')) {
    $verbose = $true; $paths = @($paths | Select-Object -Skip 1)
  }
  $output = @(& git status --porcelain=v1 -z --untracked-files=normal --ignore-submodules=none '--' @paths)
  $result = $LASTEXITCODE
  if ($result -ne 0) { $global:LASTEXITCODE = $result; return }
  $records = ($output -join "`n").Split([char]0)
  $changed = @()
  for ($index = 0; $index -lt $records.Count; $index++) {
    $row = $records[$index]
    if ($row.Length -lt 3) { continue }
    $changed += $row.Substring(3)
    if ($row.Substring(0, 2) -match '[RC]') { $index++ }
  }
  if ($verbose) { $changed }
  $global:LASTEXITCODE = if ($changed.Count) { 0 } else { 1 }
}
function gitmodified { & git ls-files --modified @args }
function gitdeleted { & git ls-files --deleted @args }
function gituntracked { & git ls-files --others --exclude-standard @args }
function gitsubmodule {
  $output = @(& git status --porcelain=v2 -z --ignore-submodules=none '--' @args)
  $result = $LASTEXITCODE
  if ($result -ne 0) { $global:LASTEXITCODE = $result; return }
  $records = ($output -join "`n").Split([char]0)
  $changed = @()
  for ($index = 0; $index -lt $records.Count; $index++) {
    $row = $records[$index]
    if (-not $row) { continue }
    $count = switch ($row[0]) { '1' { 9 }; '2' { 10 }; 'u' { 11 }; default { 0 } }
    if (-not $count) { continue }
    $fields = $row -split ' ', $count
    if ($fields.Count -eq $count -and $fields[2].StartsWith('S') -and
        ($fields[1] -ne '..' -or $fields[2] -ne 'S...')) { $changed += $fields[-1] }
    if ($row[0] -eq '2') { $index++ }
  }
  $changed
  $global:LASTEXITCODE = if ($changed.Count) { 0 } else { 1 }
}
function fname { param([string]$Path) [IO.Path]::GetFileNameWithoutExtension($Path) }
function fext { param([string]$Path) [IO.Path]::GetExtension($Path).TrimStart('.') }
function .c { Set-Location -LiteralPath (Join-Path $HOME '.config') }
function .l { Set-Location -LiteralPath (Join-Path $HOME '.local') }
function .lb { Set-Location -LiteralPath (Join-Path $HOME '.local/bin') }
function .lsh { Set-Location -LiteralPath (Join-Path $HOME '.local/share') }
function .lst { Set-Location -LiteralPath (Join-Path $HOME '.local/state') }
function .db { Set-Location -LiteralPath $env:DOTBIN }
function .ds { Set-Location -LiteralPath $env:SHELLS }
function .dsc { Set-Location -LiteralPath $env:DOTSCRIPTS }
function .dsz { Set-Location -LiteralPath (Join-Path $env:SHELLS 'zsh') }
function .dsb { Set-Location -LiteralPath (Join-Path $env:SHELLS 'bash') }
function .dsp { Set-Location -LiteralPath (Join-Path $env:SHELLS 'powershell') }
function .dt { Set-Location -LiteralPath $env:DOTHEMES }
function repos { Set-Location -LiteralPath (Join-Path $HOME 'repos') }
function src { Set-Location -LiteralPath (Join-Path $HOME 'src') }
function notes { Set-Location -LiteralPath $env:NOTES }
function rlp { . (Join-Path $env:PWSH 'profile.ps1') }
function rl { rlp }
function Invoke-DotsListing {
  param([string[]]$Flags, [object[]]$Operands)
  if (Get-Command eza -CommandType Application -ErrorAction Ignore) {
    & eza --group-directories-first --icons=auto @Flags @Operands
  } else { Get-ChildItem -Force @Operands }
}
function l { Invoke-DotsListing @('-l', '--no-user', '--no-filesize', '--no-time', '--no-permissions', '--git', '--git-repos') $args }
function ll { Invoke-DotsListing @('-lh', '--git', '--git-repos') $args }
function la { Invoke-DotsListing @('-a') $args }
function lsa { la @args }
function lla { Invoke-DotsListing @('-lha') $args }
function lt { Invoke-DotsListing @('--tree', '--level=2', '--long', '--git') $args }
function lta { Invoke-DotsListing @('--tree', '--level=2', '--long', '--git', '-a') $args }
function ff {
  $command = Get-Command fzf -CommandType Application -TotalCount 1 -ErrorAction Ignore
  if (-not $command) {
    [Console]::Error.WriteLine('ff: fzf is unavailable; use Find-File SEARCH for a table.')
    $global:LASTEXITCODE = 127
    return
  }
  # Windows PowerShell defaults native pipeline input to ASCII. Scope UTF-8 to
  # this invocation so literal filenames survive without changing the caller.
  $OutputEncoding = [System.Text.UTF8Encoding]::new($false)
  if ($MyInvocation.ExpectingInput) { $input | & $command @args }
  else { & $command @args }
  $global:LASTEXITCODE = $LASTEXITCODE
}
