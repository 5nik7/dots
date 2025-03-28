(& pyenv-venv completion) | Out-String | Invoke-Expression
(& starship completions powershell) | Out-String | Invoke-Expression
(& bat --completion ps1) | Out-String | Invoke-Expression
(& gh completion -s powershell) | Out-String | Invoke-Expression
(& tree-sitter complete --shell power-shell) | Out-String | Invoke-Expression
(& uv generate-shell-completion powershell) | Out-String | Invoke-Expression
(& uvx --generate-shell-completion powershell) | Out-String | Invoke-Expression
(& glow completion powershell) | Out-String | Invoke-Expression

Register-ArgumentCompleter -Native -CommandName winget -ScriptBlock {
  param($wordToComplete, $commandAst, $cursorPosition)
  [Console]::InputEncoding = [Console]::OutputEncoding = $OutputEncoding = [System.Text.Utf8Encoding]::new()
  $Local:word = $wordToComplete.Replace('"', '""')
  $Local:ast = $commandAst.ToString().Replace('"', '""')
  winget complete --word="$Local:word" --commandline "$Local:ast" --position $cursorPosition | ForEach-Object {
    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterValue', $_)
  }
}

Import-Module "$($(Get-Item $(Get-Command scoop.ps1).Path).Directory.Parent.FullName)\modules\scoop-completion"
