<#
.SYNOPSIS
    Print text in purple.
.DESCRIPTION
    The color of the text is purple (magenta).
.PARAMETER text
    The text to print.
.PARAMETER inline
    Print the text inline.
.PARAMETER dark
    Print the text in dark magenta.
.EXAMPLE
    PS> Write-Purple "This is magenta text."
    PS> Write-Purple "This is dark magenta text." -dark
.NOTES
    Author: njen
#>
[CmdletBinding()]
param (
    [string]$text = "",
    [switch]$inline,
    [switch]$dark
)
if ($text -eq "" ) { $text = Read-Host "$($util.symbols.readhost.icon)" }
$color = if ($dark) { "DarkMagenta" } else { "Magenta" }
if ($inline) {
    Write-Host -foregroundColor $color "$text" -NoNewline
    return
}
Write-Host -foregroundColor $color "$text"
