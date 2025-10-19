Import-Module -Name 'catppuccin' -Global

$Flavor = $Catppuccin['Mocha']
$Global:Flavor = $Flavor

if ($PSEdition -eq 'Core')
{
  $PSStyle.Formatting.Debug = $Flavor.Sky.Foreground()
  $PSStyle.Formatting.Error = $Flavor.Red.Foreground()
  $PSStyle.Formatting.ErrorAccent = $Flavor.Blue.Foreground()
  $PSStyle.Formatting.FormatAccent = $Flavor.Teal.Foreground()
  $PSStyle.Formatting.TableHeader = $Flavor.Rosewater.Foreground()
  $PSStyle.Formatting.Verbose = $Flavor.Yellow.Foreground()
  $PSStyle.Formatting.Warning = $Flavor.Peach.Foreground()
  Import-Module -Name 'CompletionPredictor'
}

if ($host.Name -eq 'ConsoleHost')
{
  Import-Module PSReadLine

  if ($PSEdition -ne 'Core')
  {
    $VersionPredictionSource = 'History'
  }
  else
  {
    $VersionPredictionSource = 'HistoryAndPlugin'
  }
  $PSReadLineOptions = @{
    HistoryNoDuplicates           = $true
    HistorySearchCursorMovesToEnd = $true
    HistorySearchCaseSensitive    = $false
    MaximumHistoryCount           = '50000'
    ShowToolTips                  = $true
    ContinuationPrompt            = '│'
    BellStyle                     = 'None'
    PredictionSource              = $VersionPredictionSource
    EditMode                      = 'Windows' # "Vi" or "Emacs" or "Windows"
    PredictionViewStyle           = 'InlineView' # "InlineView" or "ListView"
    Colors                        = @{
      # Largely based on the Code Editor style guide
      # Emphasis, ListPrediction and ListPredictionSelected are inspired by the Catppuccin fzf theme

      # Powershell colours
      ContinuationPrompt     = $Flavor.Base.Foreground()
      Emphasis               = $Flavor.Red.Foreground()
      Selection              = $Flavor.Surface0.Background()

      # PSReadLine prediction colours
      InlinePrediction       = $Flavor.Overlay0.Foreground()
      ListPrediction         = $Flavor.Mauve.Foreground()
      ListPredictionSelected = $Flavor.Surface0.Background()

      # Syntax highlighting
      Command                = $Flavor.Teal.Foreground()
      Comment                = $Flavor.Overlay0.Foreground()
      Default                = $Flavor.Text.Foreground()
      Error                  = $Flavor.Red.Foreground()
      Keyword                = $Flavor.Mauve.Foreground()
      Member                 = $Flavor.Rosewater.Foreground()
      Number                 = $Flavor.Peach.Foreground()
      Operator               = $Flavor.Sky.Foreground()
      Parameter              = $Flavor.Pink.Foreground()
      String                 = $Flavor.Green.Foreground()
      Type                   = $Flavor.Yellow.Foreground()
      Variable               = $Flavor.Lavender.Foreground()
    }
  }
  Set-PSReadLineOption @PSReadLineOptions
}

# Set-PSReadlineKeyHandler -Key Tab -Function MenuComplete
Set-PSReadLineKeyHandler -Key Tab -ScriptBlock { Invoke-FzfTabCompletion }
Set-PSReadLineKeyHandler -Key UpArrow -Function HistorySearchBackward
Set-PSReadLineKeyHandler -Key DownArrow -Function HistorySearchForward
Set-PSReadLineKeyHandler -Chord 'Ctrl+d' -Function DeleteChar
Set-PSReadLineKeyHandler -Chord 'Ctrl+w' -Function BackwardDeleteWord
Set-PSReadLineKeyHandler -Chord 'Alt+d' -Function DeleteWord
Set-PSReadLineKeyHandler -Chord 'Ctrl+LeftArrow' -Function BackwardWord
Set-PSReadLineKeyHandler -Chord 'Ctrl+RightArrow' -Function ForwardWord
Set-PSReadLineKeyHandler -Chord 'Ctrl+z' -Function Undo
Set-PSReadLineKeyHandler -Chord 'Ctrl+y' -Function Redo

Set-PSReadLineKeyHandler -Chord Enter -Function ValidateAndAcceptLine

Set-PSReadLineKeyHandler -Key '(', '{', '[' `
  -BriefDescription InsertPairedBraces `
  -LongDescription 'Insert matching braces' `
  -ScriptBlock {
  param($key, $arg)

  $closeChar = switch ($key.KeyChar)
  {
    <#case#> '(' { [char]')'; break }
    <#case#> '{' { [char]'}'; break }
    <#case#> '[' { [char]']'; break }
  }

  $selectionStart = $null
  $selectionLength = $null
  [Microsoft.PowerShell.PSConsoleReadLine]::GetSelectionState([ref]$selectionStart, [ref]$selectionLength)

  $line = $null
  $cursor = $null
  [Microsoft.PowerShell.PSConsoleReadLine]::GetBufferState([ref]$line, [ref]$cursor)

  if ($selectionStart -ne -1)
  {
    # Text is selected, wrap it in brackets
    [Microsoft.PowerShell.PSConsoleReadLine]::Replace($selectionStart, $selectionLength, $key.KeyChar + $line.SubString($selectionStart, $selectionLength) + $closeChar)
    [Microsoft.PowerShell.PSConsoleReadLine]::SetCursorPosition($selectionStart + $selectionLength + 2)
  }
  else
  {
    # No text is selected, insert a pair
    [Microsoft.PowerShell.PSConsoleReadLine]::Insert("$($key.KeyChar)$closeChar")
    [Microsoft.PowerShell.PSConsoleReadLine]::SetCursorPosition($cursor + 1)
  }
}

Set-PSReadLineKeyHandler -Key ')', ']', '}' `
  -BriefDescription SmartCloseBraces `
  -LongDescription 'Insert closing brace or skip' `
  -ScriptBlock {
  param($key, $arg)

  $line = $null
  $cursor = $null
  [Microsoft.PowerShell.PSConsoleReadLine]::GetBufferState([ref]$line, [ref]$cursor)

  if ($line[$cursor] -eq $key.KeyChar)
  {
    [Microsoft.PowerShell.PSConsoleReadLine]::SetCursorPosition($cursor + 1)
  }
  else
  {
    [Microsoft.PowerShell.PSConsoleReadLine]::Insert("$($key.KeyChar)")
  }
}

Set-PSReadLineKeyHandler -Key Backspace `
  -BriefDescription SmartBackspace `
  -LongDescription 'Delete previous character or matching quotes/parens/braces' `
  -ScriptBlock {
  param($key, $arg)

  $line = $null
  $cursor = $null
  [Microsoft.PowerShell.PSConsoleReadLine]::GetBufferState([ref]$line, [ref]$cursor)

  if ($cursor -gt 0)
  {
    $toMatch = $null
    if ($cursor -lt $line.Length)
    {
      switch ($line[$cursor])
      {
        <#case#> '"' { $toMatch = '"'; break }
        <#case#> "'" { $toMatch = "'"; break }
        <#case#> ')' { $toMatch = '('; break }
        <#case#> ']' { $toMatch = '['; break }
        <#case#> '}' { $toMatch = '{'; break }
      }
    }

    if ($toMatch -ne $null -and $line[$cursor - 1] -eq $toMatch)
    {
      [Microsoft.PowerShell.PSConsoleReadLine]::Delete($cursor - 1, 2)
    }
    else
    {
      [Microsoft.PowerShell.PSConsoleReadLine]::BackwardDeleteChar($key, $arg)
    }
  }
}

