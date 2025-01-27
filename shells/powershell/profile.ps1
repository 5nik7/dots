using namespace System.Management.Automation
using namespace System.Management.Automation.Language

$Env:DOTS = "$Env:USERPROFILE\dots"
$Env:DOTFILES = "$Env:DOTS\configs"
$Env:DOTCACHE = "$Env:DOTS\cache"

$Env:PSDOT = "$Env:DOTS\shells\powershell"
$Env:PSCOMPS = "$Env:PSDOT\completions"
$Env:PSMODS = "$Env:PSDOT\Modules"

$Env:BASHDOT = "$Env:DOTS\shells\bash"
$Env:ZSHDOT = "$Env:DOTS\shells\zsh"
$Env:PROJECTS = "$Env:USERPROFILE\dev"
$Env:DEV = "$Env:USERPROFILE\dev"
$Env:WINDOTCONF = "$Env:USERPROFILE\.config"

$Env:DRIP = "$Env:DOTS\drip"
$Env:DRIP_COLS = "$Env:DRIP\colorschemes"
$Env:DRIP_TEMPS = "$Env:DRIP\tenplates"
$Env:WALLS = "$Env:DOTS\walls"

$Env:NVM_HOME = "$Env:APPDATA\nvm"
$Env:NVM_SYMLINK = "$Env:HOMEDRIVE\node"
$Env:GOPATH = "$Env:USERPROFILE\go"
$Env:GOBIN = "$Env:USERPROFILE\go\bin"

$Env:DOCUMENTS = [Environment]::GetFolderPath("mydocuments")
$Env:DOWNLOADS = "$Env:USERPROFILE\Downloads"

$Env:STARSHIP_CACHE = "$Env:LOCALAPPDATA\Temp"
$Env:STARSHIP_CONFIG = "$Env:DOTFILES\starship\starship.toml"
$Env:BAT_CONFIG_PATH = "$Env:DOTFILES\bat\config"
$Env:YAZI_CONFIG_HOME = "$Env:DOTFILES\yazi"

$GITBIN = "C:\Git\usr\bin"
$Env:YAZI_FILE_ONE = "$GITBIN\file.exe"
$BAT_THEME = 'wal'
$Env:BAT_THEME = $BAT_THEME
$Env:KOMOREBI_CONFIG_HOME = "$Env:WINDOTCONF\komorebi"

$TIC = (Get-ItemProperty 'HKCU:\Control Panel\Desktop' TranscodedImageCache -ErrorAction Stop).TranscodedImageCache
$wallout = [System.Text.Encoding]::Unicode.GetString($TIC) -replace '(.+)([A-Z]:[0-9a-zA-Z\\])+', '$2'
$Env:WALLPAPER = $wallout

foreach ( $includeFile in ("functions", "aliases", "lab") ) {
    Unblock-File "$Env:PSDOT\$includeFile.ps1"
    . "$Env:PSDOT\$includeFile.ps1"
}

(& gh completion -s powershell) | Out-String | Invoke-Expression
(& starship completions powershell) | Out-String | Invoke-Expression
(& bat --completion ps1) | Out-String | Invoke-Expression
(& tree-sitter complete --shell powershell) | Out-String | Invoke-Expression
(& uv generate-shell-completion powershell) | Out-String | Invoke-Expression
(& uvx --generate-shell-completion powershell) | Out-String | Invoke-Expression

Register-ArgumentCompleter -Native -CommandName winget -ScriptBlock {
    param($wordToComplete, $commandAst, $cursorPosition)
    [Console]::InputEncoding = [Console]::OutputEncoding = $OutputEncoding = [System.Text.Utf8Encoding]::new()
    $Local:word = $wordToComplete.Replace('"', '""')
    $Local:ast = $commandAst.ToString().Replace('"', '""')
    winget complete --word="$Local:word" --commandline "$Local:ast" --position $cursorPosition | ForEach-Object {
        [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterValue', $_)
    }
}

. "$Env:DOTCACHE\wal\wal.ps1"

# FZF Options
# Editor Configuration
$FZF_DEFAULT_COMMAND = if (Test-CommandExists fd) { 'fd --type f --strip-cwd-prefix --hidden --exclude .git' }
$env:FZF_DEFAULT_COMMAND = $FZF_DEFAULT_COMMAND

$Env:FZF_DEFAULT_OPTS = @"
--height=60%
--color=bg+:$color0,bg:-1,spinner:4,hl:12
--color=fg:8,header:3,info:8,pointer:$color1
--color=marker:14,fg+:13,prompt:$color8,hl+:10
--color=gutter:$bg,selected-bg:0,separator:$color0,preview-border:$color8
--color=border:$color8,preview-bg:$bg,preview-label:0,label:7,query:5,input-border:4
--info=right
--layout=reverse
--border=sharp
--prompt=' '
--pointer='┃'
--separator='──'
--marker='│'
--scrollbar='│'
--preview-window='right:65%'
--preview=`"bat --style=numbers --color=always {}`" --preview-window=border-sharp --tabstop=2 --bind=ctrl-d:preview-half-page-down,ctrl-u:preview-half-page-up
"@

if (-not (Get-Module Terminal-Icons -ListAvailable)) {
    Install-Module Terminal-Icons -Scope CurrentUser -Force
}
Import-Module -Name Terminal-Icons

Import-Module "$Env:PSMODS\winwal\winwal.psm1"
Import-Module "$Env:PSMODS\psdots\psdots.psm1"
Import-Module "$($(Get-Item $(Get-Command scoop.ps1).Path).Directory.Parent.FullName)\modules\scoop-completion"

if ($PSEdition -eq 'Core') {
    Import-Module -Name Microsoft.WinGet.CommandNotFound
}

$Env:PSCRIPTS = "$Env:PSDOT\Scripts"
if (Test-Path($Env:PSCRIPTS)) {
    Add-Path -Path $Env:PSCRIPTS
}

$Env:DOTBIN = "$Env:DOTS\bin"
if (Test-Path($Env:DOTBIN)) {
    Add-Path -Path $Env:DOTBIN
}

$localbin = "$Env:USERPROFILE\.local\bin"
if (Test-Path($localbin)) {
    Add-Path -Path $localbin
}

$PYENV_VERSION = (&pyenv version-name) -replace '\s', ''
$Env:PYENV_VERSION = $PYENV_VERSION
$PYEXEDIR = "$Env:PYENV_HOME" + "versions\$PYENV_VERSION"
$PYSCRIPTS = "$PYEXEDIR\Scripts"

Add-Path -Path "$PYEXEDIR"
Add-Path -Path "$PYSCRIPTS"

if ($host.Name -eq 'ConsoleHost') {
    Import-Module PSReadLine

    $PSReadLineOptions = @{
        HistoryNoDuplicates           = $true
        HistorySearchCursorMovesToEnd = $true
        HistorySearchCaseSensitive    = $false
        MaximumHistoryCount           = "50000"
        ShowToolTips                  = $true
        ContinuationPrompt            = "│"
        BellStyle                     = "None"
        PredictionSource              = "History"
        EditMode                      = "Vi"
        PredictionViewStyle           = "InlineView"
        Colors                        = @{
            Comment                = 'DarkGray'
            Command                = 'DarkMagenta'
            Emphasis               = 'Red'
            Number                 = 'DarkYellow'
            Member                 = 'White'
            Operator               = 'Yellow'
            Type                   = 'Cyan'
            String                 = 'Green'
            Variable               = 'DarkYellow'
            Parameter              = 'Yellow'
            ContinuationPrompt     = 'Black'
            Default                = 'White'
            InlinePrediction       = 'DarkGray'
            ListPrediction         = 'DarkGray'
            ListPredictionSelected = 'DarkGray'
            ListPredictionTooltip  = 'DarkGray'
        }
    }
    Set-PSReadLineOption @PSReadLineOptions
}

Set-PSReadlineKeyHandler -Key Tab -Function MenuComplete
Set-PSReadLineKeyHandler -Key UpArrow -Function HistorySearchBackward
Set-PSReadLineKeyHandler -Key DownArrow -Function HistorySearchForward
Set-PSReadLineKeyHandler -Chord Enter -Function ValidateAndAcceptLine

Set-PSReadLineKeyHandler -Key '"', "'" `
    -BriefDescription SmartInsertQuote `
    -LongDescription "Insert paired quotes if not already on a quote" `
    -ScriptBlock {
    param($key, $arg)

    $quote = $key.KeyChar

    $selectionStart = $null
    $selectionLength = $null
    [Microsoft.PowerShell.PSConsoleReadLine]::GetSelectionState([ref]$selectionStart, [ref]$selectionLength)

    $line = $null
    $cursor = $null
    [Microsoft.PowerShell.PSConsoleReadLine]::GetBufferState([ref]$line, [ref]$cursor)

    # If text is selected, just quote it without any smarts
    if ($selectionStart -ne -1) {
        [Microsoft.PowerShell.PSConsoleReadLine]::Replace($selectionStart, $selectionLength, $quote + $line.SubString($selectionStart, $selectionLength) + $quote)
        [Microsoft.PowerShell.PSConsoleReadLine]::SetCursorPosition($selectionStart + $selectionLength + 2)
        return
    }

    $ast = $null
    $tokens = $null
    $parseErrors = $null
    [Microsoft.PowerShell.PSConsoleReadLine]::GetBufferState([ref]$ast, [ref]$tokens, [ref]$parseErrors, [ref]$null)

    function FindToken {
        param($tokens, $cursor)

        foreach ($token in $tokens) {
            if ($cursor -lt $token.Extent.StartOffset) { continue }
            if ($cursor -lt $token.Extent.EndOffset) {
                $result = $token
                $token = $token -as [StringExpandableToken]
                if ($token) {
                    $nested = FindToken $token.NestedTokens $cursor
                    if ($nested) { $result = $nested }
                }

                return $result
            }
        }
        return $null
    }

    $token = FindToken $tokens $cursor

    # If we're on or inside a **quoted** string token (so not generic), we need to be smarter
    if ($token -is [StringToken] -and $token.Kind -ne [TokenKind]::Generic) {
        # If we're at the start of the string, assume we're inserting a new string
        if ($token.Extent.StartOffset -eq $cursor) {
            [Microsoft.PowerShell.PSConsoleReadLine]::Insert("$quote$quote ")
            [Microsoft.PowerShell.PSConsoleReadLine]::SetCursorPosition($cursor + 1)
            return
        }

        # If we're at the end of the string, move over the closing quote if present.
        if ($token.Extent.EndOffset -eq ($cursor + 1) -and $line[$cursor] -eq $quote) {
            [Microsoft.PowerShell.PSConsoleReadLine]::SetCursorPosition($cursor + 1)
            return
        }
    }

    if ($null -eq $token -or
        $token.Kind -eq [TokenKind]::RParen -or $token.Kind -eq [TokenKind]::RCurly -or $token.Kind -eq [TokenKind]::RBracket) {
        if ($line[0..$cursor].Where{ $_ -eq $quote }.Count % 2 -eq 1) {
            # Odd number of quotes before the cursor, insert a single quote
            [Microsoft.PowerShell.PSConsoleReadLine]::Insert($quote)
        }
        else {
            # Insert matching quotes, move cursor to be in between the quotes
            [Microsoft.PowerShell.PSConsoleReadLine]::Insert("$quote$quote")
            [Microsoft.PowerShell.PSConsoleReadLine]::SetCursorPosition($cursor + 1)
        }
        return
    }

    # If cursor is at the start of a token, enclose it in quotes.
    if ($token.Extent.StartOffset -eq $cursor) {
        if ($token.Kind -eq [TokenKind]::Generic -or $token.Kind -eq [TokenKind]::Identifier -or 
            $token.Kind -eq [TokenKind]::Variable -or $token.TokenFlags.hasFlag([TokenFlags]::Keyword)) {
            $end = $token.Extent.EndOffset
            $len = $end - $cursor
            [Microsoft.PowerShell.PSConsoleReadLine]::Replace($cursor, $len, $quote + $line.SubString($cursor, $len) + $quote)
            [Microsoft.PowerShell.PSConsoleReadLine]::SetCursorPosition($end + 2)
            return
        }
    }

    # We failed to be smart, so just insert a single quote
    [Microsoft.PowerShell.PSConsoleReadLine]::Insert($quote)
}

Set-PSReadLineKeyHandler -Key '(', '{', '[' `
    -BriefDescription InsertPairedBraces `
    -LongDescription "Insert matching braces" `
    -ScriptBlock {
    param($key, $arg)

    $closeChar = switch ($key.KeyChar) {
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
    
    if ($selectionStart -ne -1) {
        # Text is selected, wrap it in brackets
        [Microsoft.PowerShell.PSConsoleReadLine]::Replace($selectionStart, $selectionLength, $key.KeyChar + $line.SubString($selectionStart, $selectionLength) + $closeChar)
        [Microsoft.PowerShell.PSConsoleReadLine]::SetCursorPosition($selectionStart + $selectionLength + 2)
    }
    else {
        # No text is selected, insert a pair
        [Microsoft.PowerShell.PSConsoleReadLine]::Insert("$($key.KeyChar)$closeChar")
        [Microsoft.PowerShell.PSConsoleReadLine]::SetCursorPosition($cursor + 1)
    }
}

Set-PSReadLineKeyHandler -Key ')', ']', '}' `
    -BriefDescription SmartCloseBraces `
    -LongDescription "Insert closing brace or skip" `
    -ScriptBlock {
    param($key, $arg)

    $line = $null
    $cursor = $null
    [Microsoft.PowerShell.PSConsoleReadLine]::GetBufferState([ref]$line, [ref]$cursor)

    if ($line[$cursor] -eq $key.KeyChar) {
        [Microsoft.PowerShell.PSConsoleReadLine]::SetCursorPosition($cursor + 1)
    }
    else {
        [Microsoft.PowerShell.PSConsoleReadLine]::Insert("$($key.KeyChar)")
    }
}

Set-PSReadLineKeyHandler -Key Backspace `
    -BriefDescription SmartBackspace `
    -LongDescription "Delete previous character or matching quotes/parens/braces" `
    -ScriptBlock {
    param($key, $arg)

    $line = $null
    $cursor = $null
    [Microsoft.PowerShell.PSConsoleReadLine]::GetBufferState([ref]$line, [ref]$cursor)

    if ($cursor -gt 0) {
        $toMatch = $null
        if ($cursor -lt $line.Length) {
            switch ($line[$cursor]) {
                <#case#> '"' { $toMatch = '"'; break }
                <#case#> "'" { $toMatch = "'"; break }
                <#case#> ')' { $toMatch = '('; break }
                <#case#> ']' { $toMatch = '['; break }
                <#case#> '}' { $toMatch = '{'; break }
            }
        }

        if ($toMatch -ne $null -and $line[$cursor - 1] -eq $toMatch) {
            [Microsoft.PowerShell.PSConsoleReadLine]::Delete($cursor - 1, 2)
        }
        else {
            [Microsoft.PowerShell.PSConsoleReadLine]::BackwardDeleteChar($key, $arg)
        }
    }
}

Invoke-Expression (&starship init powershell)
Enable-TransientPrompt
function Invoke-Starship-TransientFunction {
    &starship module character
}

Set-PSReadLineOption -ViModeIndicator script -ViModeChangeHandler {
    [Microsoft.PowerShell.PSConsoleReadLine]::InvokePrompt()
    if ($args[0] -eq 'Command') {
        # Set the cursor to a solid block.
        [Microsoft.PowerShell.PSConsoleReadLine]::ForwardChar()
        Write-Host -NoNewLine "`e[2 q"
    }
    else {
        # Set the cursor to a blinking line.
        Write-Host -NoNewLine "`e[5 q"
    }
}


