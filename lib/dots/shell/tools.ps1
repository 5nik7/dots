# Dot-sourced so generated native functions and hooks survive initialization.
param([string] $Feature)
if ($Feature -eq 'direnv' -and $PSVersionTable.PSVersion -lt [version]'7.2') {
  throw 'direnv requires PowerShell 7.2 or newer.'
}
$tool = Get-Command $Feature -CommandType Application -TotalCount 1 -ErrorAction Stop
$toolArgs = switch ($Feature) {
  starship { 'init', 'powershell', '--print-full-init' }
  zoxide { 'init', 'powershell' }
  atuin { 'init', 'powershell', '--disable-ctrl-r', '--disable-up-arrow' }
  direnv { 'hook', 'pwsh' }
  tv { 'init', 'power-shell' }
  default { 'activate', 'pwsh' }
}
$generated = & $tool @toolArgs | Out-String
if ($LASTEXITCODE -ne 0 -or -not $generated.Trim()) { throw "Initialization failed: $Feature" }
# Television supplies Ctrl-T and Ctrl-R. Keep any chords already owned by
# PSFzf, including when the module was initialized by a profile hook.
if ($Feature -eq 'tv' -and (Get-Module PSReadLine)) {
  $generated = & {
    $reserved = @(Get-PSReadLineKeyHandler -Bound | Where-Object Function -Match 'fzf' | ForEach-Object Key)
    $text = $generated
    if ($reserved.Count) {
      $statements = ([scriptblock]::Create($text)).Ast.EndBlock.Statements
      for ($i = $statements.Count - 1; $i -ge 0; $i--) {
        $extent = $statements[$i].Extent
        if ($extent.Text -match '^Set-PSReadLineKeyHandler\s+-(?:Chord|Key)\s+[''"]?(Ctrl\+[rt])\b' -and
            $reserved -contains $Matches[1]) {
          $text = $text.Remove($extent.StartOffset, $extent.EndOffset - $extent.StartOffset)
        }
      }
    }
    $text
  }
}
Invoke-Expression $generated -ErrorAction Stop
if ($Feature -eq 'starship') {
  Install-DotsPrompt -Renderer (Get-Item Function:prompt).ScriptBlock
  if ($global:__ShellInteg_Installed) { __ShellInteg_Rearm }
}
