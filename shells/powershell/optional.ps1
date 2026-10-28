# Explicit session opt-ins: dot-source this file so generated functions persist.
param(
  [Parameter(Mandatory, Position=0)]
  [ValidateSet('starship', 'blastoff', 'icons', 'catppuccin', 'pscompletions',
    'fzf', 'completions', 'zoxide', 'mise', 'vfox', 'chocolatey',
    'command-not-found', 'terminal', 'coreutils')]
  [string] $Feature
)

if (-not $global:_DotsOptionalFeatures) { $global:_DotsOptionalFeatures = @{} }
if ($global:_DotsOptionalFeatures[$Feature]) { return }
if ($Feature -eq 'command-not-found' -and ($PSEdition -ne 'Core' -or $PSVersionTable.PSVersion -lt [version]'7.4')) {
  throw 'WinGet CommandNotFound requires PowerShell Core 7.4 or newer.'
}
$dotsOptionalModules = @{
  icons = 'Terminal-Icons'; catppuccin = 'Catppuccin'
  pscompletions = 'PSCompletions'; fzf = 'PSFzf'
  'command-not-found' = 'Microsoft.WinGet.CommandNotFound'
}
try {
  if ($dotsOptionalModules.ContainsKey($Feature)) {
    Import-Module $dotsOptionalModules[$Feature] -Global -ErrorAction Stop
  } else {
    switch ($Feature) {
      blastoff {
        if (-not (Test-Path -LiteralPath (Join-Path $env:DOTS 'bin/blastoff.ps1') -PathType Leaf)) {
          throw 'The bundled Blastoff launcher is missing from this Dots checkout.'
        }
        function global:blastoff {
          & (Join-Path $env:DOTS 'bin/blastoff.ps1') @args
          $global:LASTEXITCODE = $LASTEXITCODE
        }
      }
      completions {
        foreach ($spec in @(
          @('starship', 'completions', 'powershell'),
          @('gh', 'completion', '-s', 'powershell'),
          @('bat', '--completion', 'ps1'),
          @('uv', 'generate-shell-completion', 'powershell'),
          @('uvx', '--generate-shell-completion', 'powershell')
        )) {
          $tool = Get-Command $spec[0] -CommandType Application -TotalCount 1 -ErrorAction Ignore
          if (-not $tool) { continue }
          $toolArgs = $spec[1..($spec.Count - 1)]
          $generated = & $tool @toolArgs | Out-String
          if ($LASTEXITCODE -ne 0) { throw "Completion generation failed: $($spec[0])" }
          if ($generated.Trim()) { Invoke-Expression $generated -ErrorAction Stop }
        }
        Register-ArgumentCompleter -Native -CommandName winget -ScriptBlock {
          param($wordToComplete, $commandAst, $cursorPosition)
          winget complete --word="$wordToComplete" --commandline "$commandAst" --position $cursorPosition |
            ForEach-Object { [Management.Automation.CompletionResult]::new($_, $_, 'ParameterValue', $_) }
        }
      }
      { $_ -in 'starship', 'zoxide', 'mise', 'vfox' } {
        $tool = Get-Command $Feature -CommandType Application -TotalCount 1 -ErrorAction Stop
        $toolArgs = switch ($Feature) {
          starship { 'init', 'powershell', '--print-full-init' }
          zoxide { 'init', 'powershell' }
          default { 'activate', 'pwsh' }
        }
        $generated = & $tool @toolArgs | Out-String
        if ($LASTEXITCODE -ne 0 -or -not $generated.Trim()) { throw "Initialization failed: $Feature" }
        Invoke-Expression $generated -ErrorAction Stop
        if ($Feature -eq 'starship') {
          Install-DotsPrompt -Renderer (Get-Item Function:prompt).ScriptBlock
          if ($global:__ShellInteg_Installed) { __ShellInteg_Rearm }
        }
      }
      chocolatey {
        if (-not $env:ChocolateyInstall) { throw 'ChocolateyInstall is not set.' }
        Import-Module (Join-Path $env:ChocolateyInstall 'helpers/chocolateyProfile.psm1') -Global -ErrorAction Stop
      }
      terminal {
        $integration = Join-Path (Split-Path -Parent $PROFILE.CurrentUserAllHosts) 'shell-integration_v7.ps1'
        if (-not (Test-Path -LiteralPath $integration -PathType Leaf)) { throw 'Terminal integration is not installed.' }
        . $integration
      }
      coreutils { . (Join-Path $env:PWSH 'coreutils.ps1') }
    }
  }
  $global:_DotsOptionalFeatures[$Feature] = $true
} finally {
  Remove-Variable dotsOptionalModules, tool, toolArgs, generated, spec, integration -ErrorAction Ignore
}
