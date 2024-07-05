
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

function Set-Env {
  <#
    .SYNOPSIS
    Creates or sets an environment variable.

    .DESCRIPTION
    Uses the .NET [Environment class](http://msdn.microsoft.com/en-us/library/z8te35sa) to create or set an environment variable in the Process, User, or Machine scopes.

    Changes to environment variables in the User and Machine scope are not picked up by running processes. Any running processes that use this environment variable should be restarted.

    Beginning with Carbon 2.3.0, you can set an environment variable for a specific user by specifying the `-ForUser` switch and passing the user's credentials with the `-Credential` parameter. This will run a PowerShell process as that user in order to set the environment variable.

    Normally, you have to restart your PowerShell session/process to see the variable in the `env:` drive. Use the `-Force` switch to also add the variable to the `env:` drive. This functionality was added in Carbon 2.3.0.

    .LINK
    Carbon_EnvironmentVariable

    .LINK
    Remove-EnvironmentVariable

    .LINK
    http://msdn.microsoft.com/en-us/library/z8te35sa

    .EXAMPLE
    Set-EnvironmentVariable -Name 'MyEnvironmentVariable' -Value 'Value1' -ForProcess

    Creates the `MyEnvironmentVariable` with an initial value of `Value1` in the process scope, i.e. the variable is only accessible in the current process.

    .EXAMPLE
    Set-EnvironmentVariable -Name 'MyEnvironmentVariable' -Value 'Value1' -ForComputer

    Creates the `MyEnvironmentVariable` with an initial value of `Value1` in the machine scope, i.e. the variable is accessible in all newly launched processes.

    .EXAMPLE
    Set-EnvironmentVariable -Name 'SomeUsersEnvironmentVariable' -Value 'SomeValue' -ForUser -Credential $userCreds

    Demonstrates that you can set a user-level environment variable for another user by passing its credentials to the `Credential` parameter. Runs a separate PowerShell process as that user to set the environment variable.
    #>
  [CmdletBinding(SupportsShouldProcess = $true)]
  param(
    [Parameter(Mandatory = $true)]
    [string]
    # The name of environment variable to add/set.
    $Name,

    [Parameter(Mandatory = $true)]
    [string]
    # The environment variable's value.
    $Value,

    [Parameter(ParameterSetName = 'ForCurrentUser')]
    # Sets the environment variable for the current computer.
    [Switch]
    $ForComputer,

    [Parameter(ParameterSetName = 'ForCurrentUser')]
    [Parameter(Mandatory = $true, ParameterSetName = 'ForSpecificUser')]
    # Sets the environment variable for the current user.
    [Switch]
    $ForUser,

    [Parameter(ParameterSetName = 'ForCurrentUser')]
    # Sets the environment variable for the current process.
    [Switch]
    $ForProcess,

    [Parameter(ParameterSetName = 'ForCurrentUser')]
    [Switch]
    # Set the variable in the current PowerShell session's `env:` drive, too. Normally, you have to restart your session to see the variable in the `env:` drive.
    #
    # This parameter was added in Carbon 2.3.0.
    $Force,

    [Parameter(Mandatory = $true, ParameterSetName = 'ForSpecificUser')]
    [pscredential]
    # Set an environment variable for a specific user.
    $Credential
  )

  Set-StrictMode -Version 'Latest'

  Use-CallerPreference -Cmdlet $PSCmdlet -Session $ExecutionContext.SessionState

  if ( $PSCmdlet.ParameterSetName -eq 'ForSpecificUser' ) {
    Invoke-PowerShell -FilePath (Join-Path -Path $PSScriptRoot -ChildPath '..\bin\Set-EnvironmentVariable.ps1' -Resolve) `
      -Credential $credential `
      -ArgumentList ('-Name {0} -Value {1}' -f (ConvertTo-Base64 $Name), (ConvertTo-Base64 $Value)) `
      -NonInteractive `
      -OutputFormat 'text'
    return
  }

  if ( -not $ForProcess -and -not $ForUser -and -not $ForComputer ) {
    Write-Error -Message ('Environment variable target not specified. You must supply one of the ForComputer, ForUser, or ForProcess switches.')
    return
  }

  Invoke-Command -ScriptBlock {
    if ( $ForComputer ) {
      [EnvironmentVariableTarget]::Machine
    }

    if ( $ForUser ) {
      [EnvironmentVariableTarget]::User
    }

    if ( $Force -or $ForProcess ) {
      [EnvironmentVariableTarget]::Process
    }
  } |
  Where-Object { $PSCmdlet.ShouldProcess( "$_-level environment variable '$Name'", "set") } |
  ForEach-Object { [Environment]::SetEnvironmentVariable( $Name, $Value, $_ ) }
}

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

function repos {
  Set-Location "$env:REPOS"
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