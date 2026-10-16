# Native bootstrap/help presentation; no Python or Bash required.
function Write-DotsMessage {
    param([string] $Text, [ValidateSet('heading', 'info', 'error')][string] $Role = 'info', [hashtable] $Presentation = @{})
    $errorStream = $Role -eq 'error'
    $writer = if ($errorStream) { [Console]::Error } else { [Console]::Out }
    $redirected = if ($errorStream) { [Console]::IsErrorRedirected } else { [Console]::IsOutputRedirected }
    $mode = if ($Presentation.ContainsKey('color')) { $Presentation['color'] } elseif ($env:DOTS_COLOR) { $env:DOTS_COLOR } else { 'auto' }
    $icons = if ($Presentation.ContainsKey('icons')) { $Presentation['icons'] } elseif ($env:DOTS_ICONS) { $env:DOTS_ICONS } else { 'auto' }
    $terminal = -not $redirected -and $env:TERM -ne 'dumb' -and $Host.UI.SupportsVirtualTerminal
    $colored = $mode -eq 'always' -or ($mode -eq 'auto' -and $terminal -and -not $env:NO_COLOR)
    $glyphs = $icons -eq 'always' -or ($icons -eq 'auto' -and $terminal)
    $textSafe = [regex]::Replace($Text, '[\x00-\x1f\x7f-\x9f]', { param($m) '\u{0:x4}' -f [int][char]$m.Value })
    $prefix = if ($errorStream) { if ($glyphs) { ([string][char]0xf00d) + ' ' } else { '[x] ' } } else { '' }
    if ($colored) {
        $code = if ($Role -eq 'heading') { '1;96' } elseif ($errorStream) { '91' } else { '94' }
        $writer.WriteLine(([string][char]27 + '[' + $code + 'm') + $prefix + $textSafe + ([string][char]27 + '[0m'))
    } else { $writer.WriteLine($prefix + $textSafe) }
}
