# Load a native application's locally installed provider on its first completion.
[CmdletBinding(DefaultParameterSetName='Line')]
param(
  [Parameter(ParameterSetName='Line', Mandatory)][string]$Line,
  [Parameter(ParameterSetName='Line', Mandatory)][int]$Cursor,
  [Parameter(ParameterSetName='All', Mandatory)][switch]$All
)

$generators = @{
  bat = @('--completion', 'ps1')
  bob = @('complete', 'power-shell')
  'cargo-binstall' = @('--completions', 'powershell')
  codex = @('completion', 'powershell')
  delta = @('--generate-completion', 'powershell')
  docker = @('completion', 'powershell')
  dua = @('completions', 'powershell')
  fd = @('--gen-completions', 'powershell')
  gh = @('completion', '-s', 'powershell')
  just = @('--completions', 'powershell')
  kubectl = @('completion', 'powershell')
  mdcat = @('--completions', 'powershell')
  mise = @('completion', 'powershell')
  ptr = @('completion')
  rg = @('--generate', 'complete-powershell')
  rustup = @('completions', 'powershell')
  starship = @('completions', 'powershell')
  'tree-sitter' = @('complete', '--shell', 'power-shell')
  uv = @('generate-shell-completion', 'powershell')
  uvx = @('--generate-shell-completion', 'powershell')
}
$alias = $null
$packages = @{ ya = 'yazi'; yazi = 'yazi'; zoxide = 'zoxide'; pastel = 'pastel' }
$native = @('cargo', 'choco', 'dotnet', 'git', 'pip', 'scoop', 'winget')
if ($All) {
  $names = @($generators.Keys) + @($packages.Keys) + $native
} else {
  if ($Cursor -lt 1 -or $Cursor -gt $Line.Length) { return }
  # Add a literal suffix so the parser includes a trailing space at the cursor
  # in the active command extent. Never evaluate the command being edited.
  $tokens = $null
  $errors = $null
  $ast = [Management.Automation.Language.Parser]::ParseInput(
    $Line.Substring(0, $Cursor) + 'x', [ref]$tokens, [ref]$errors)
  $command = $ast.FindAll({
    param($node)
    $node -is [Management.Automation.Language.CommandAst] -and $node.Extent.EndOffset -gt $Cursor
  }, $true) | Select-Object -Last 1
  if (-not $command -or $command.CommandElements.Count -lt 2) { return }
  $name = $command.GetCommandName()
  if (-not $name -or $name -notmatch '^[\w.-]+$') { return }
  $alias = Get-Alias -Name $name -ErrorAction Ignore
  if ($alias) { $name = $alias.Definition }
  $names = @($name -replace '\.(exe|cmd|ps1)$', '')
}

# Neither engine has a public API for inspecting existing native completers.
function Get-DotsNativeCompleters {
  $flags = [Reflection.BindingFlags]'Instance,NonPublic,Public'
  $field = $ExecutionContext.GetType().GetField('_context', $flags)
  if (-not $field) { return }
  $context = $field.GetValue($ExecutionContext)
  $property = $context.GetType().GetProperty('NativeArgumentCompleters', $flags)
  if ($property) { return $property.GetValue($context, $null) }
}
if (-not $global:_DotsHostCompletionProviders) { $global:_DotsHostCompletionProviders = @{} }
foreach ($name in $names) {
  if ($global:_DotsHostCompletionProviders.ContainsKey($name)) { continue }
  if (-not $generators.ContainsKey($name) -and -not $packages.ContainsKey($name) -and $name -notin $native) { continue }
  $previousExit = $global:LASTEXITCODE
  try {
    $registered = Get-DotsNativeCompleters
    if ($registered -and ($registered.ContainsKey($name) -or $registered.ContainsKey("$name.exe"))) {
      $global:_DotsHostCompletionProviders[$name] = 'existing'
      continue
    }
    $app = Get-Command $name -CommandType Application -TotalCount 1 -ErrorAction Ignore
    if (-not $app) { continue }
    $source = $null
    if ($generators.ContainsKey($name)) {
      $arguments = $generators[$name]
      $source = & $app @arguments 2>$null | Out-String
      if ($LASTEXITCODE -ne 0 -or -not $source.Trim()) { throw 'generator unavailable' }
    } elseif ($packages.ContainsKey($name)) {
      $roots = @($env:SCOOP, $env:SCOOP_GLOBAL)
      if ($env:USERPROFILE) { $roots += Join-Path $env:USERPROFILE 'scoop' }
      if ($env:ProgramData) { $roots += Join-Path $env:ProgramData 'scoop' }
      $provider = foreach ($root in $roots) {
        if (-not $root) { continue }
        $path = Join-Path $root "apps/$($packages[$name])/current/completions/_$name.ps1"
        if ([IO.File]::Exists($path)) { $path; break }
      }
      if (-not $provider -and $name -eq 'pastel' -and $env:LOCALAPPDATA) {
        $link = Join-Path $env:LOCALAPPDATA 'Microsoft/WinGet/Links/pastel.exe'
        $target = (Get-Item -LiteralPath $link -ErrorAction Ignore).Target
        if ($target) {
          $path = Join-Path (Split-Path $target) 'autocomplete/_pastel.ps1'
          if ([IO.File]::Exists($path)) { $provider = $path }
        }
      }
      if (-not $provider) { continue }
      $source = [IO.File]::ReadAllText($provider)
    } elseif ($name -eq 'choco') {
      if (-not $env:ChocolateyInstall) { continue }
      $provider = Join-Path $env:ChocolateyInstall 'helpers/ChocolateyTabExpansion.ps1'
      if (-not [IO.File]::Exists($provider)) { continue }
      # This provider uses script scope and its own file path.
      $null = New-Module -ErrorAction Stop -ScriptBlock { param($path); . $path; Export-ModuleMember -Function @() -Alias @() } -ArgumentList $provider
    } else {
      $completer = {
        param($wordToComplete, $commandAst, $cursorPosition)
        $before = $global:LASTEXITCODE
        $line = $commandAst.Extent.Text
        $position = $cursorPosition - $commandAst.Extent.StartOffset
        if ($position -gt $line.Length) { $line += ' ' * ($position - $line.Length) }
        try {
          $values = switch ($name) {
            winget { & $app complete "--word=$wordToComplete" "--commandline=$line" --position $position 2>$null }
            dotnet { & $app complete --position $position $line 2>$null }
            pip {
              $saved = @($env:COMP_WORDS, $env:COMP_CWORD, $env:PIP_AUTO_COMPLETE)
              try {
                $env:COMP_WORDS = $line.Substring(0, $position)
                $env:COMP_CWORD = $env:COMP_WORDS.Split().Length - 1
                $env:PIP_AUTO_COMPLETE = '1'
                (& $app 2>$null) -split '\s+'
              } finally {
                $env:COMP_WORDS, $env:COMP_CWORD, $env:PIP_AUTO_COMPLETE = $saved
              }
            }
            default {
              if ($commandAst.CommandElements.Count -gt 2 -or
                  ($commandAst.CommandElements.Count -eq 2 -and -not $wordToComplete)) { return }
              switch ($name) {
                git { & $app --list-cmds=main,others,alias 2>$null }
                cargo { & $app --list 2>$null | ForEach-Object { if ($_ -match '^\s+(\S+)') { $Matches[1] } } }
                scoop {
                  $directory = Join-Path (Split-Path (Split-Path $app.Source)) 'apps/scoop/current/libexec'
                  Get-ChildItem -LiteralPath $directory -Filter 'scoop-*.ps1' -ErrorAction Ignore |
                    ForEach-Object { $_.BaseName.Substring(6) }
                }
              }
            }
          }
          foreach ($value in $values) {
            if ($value -and $value.StartsWith([string]$wordToComplete, [StringComparison]::OrdinalIgnoreCase)) {
              [Management.Automation.CompletionResult]::new($value, $value, 'ParameterValue', $value)
            }
          }
        } finally { $global:LASTEXITCODE = $before }
      }.GetNewClosure()
      Register-ArgumentCompleter -Native -CommandName $name -ScriptBlock $completer
    }
    if ($source) {
      # Keep generated helper functions alive in a private module without
      # exporting them over the user's prompt, commands or completion bindings.
      $providerScript = if ($name -eq 'mise') {
        & (Join-Path $PSScriptRoot 'mise-completion-source.ps1') -Source $source
      } else { [ScriptBlock]::Create($source) }
      $null = New-Module -ErrorAction Stop -ScriptBlock { param($script); . $script; Export-ModuleMember -Function @() -Alias @() } -ArgumentList $providerScript
    }
    $global:_DotsHostCompletionProviders[$name] = 'loaded'
  } catch {
    $global:_DotsHostCompletionProviders[$name] = 'unavailable'
    Write-Verbose "Completion for $name unavailable: $_"
  } finally { $global:LASTEXITCODE = $previousExit }
}

# Native PowerShell resolves .exe forms automatically, but an alias needs its
# own registration. Give the upstream provider its canonical command and offsets.
if ($alias -and $global:_DotsHostCompletionProviders.ContainsKey($name)) {
  $registered = Get-DotsNativeCompleters
  if ($registered -and -not $registered.ContainsKey($alias.Name)) {
    $target = $registered[$name]
    if (-not $target) { $target = $registered["$name.exe"] }
    if ($target) {
      $forward = {
        param($wordToComplete, $commandAst, $cursorPosition)
        $first = $commandAst.CommandElements[0].Extent
        $text = $name + $commandAst.Extent.Text.Substring($first.Text.Length)
        $position = $cursorPosition - $first.EndOffset + $name.Length
        $tokens = $null
        $errors = $null
        $parsed = [Management.Automation.Language.Parser]::ParseInput($text, [ref]$tokens, [ref]$errors)
        & $target $wordToComplete $parsed.EndBlock.Statements[0].PipelineElements[0] $position
      }.GetNewClosure()
      Register-ArgumentCompleter -Native -CommandName $alias.Name -ScriptBlock $forward
    }
  }
}
