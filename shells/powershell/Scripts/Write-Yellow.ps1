<#
.SYNOPSIS
    Print text in yellow.
.DESCRIPTION
    The color of the text is yellow.
.PARAMETER text
    The text to print.
.PARAMETER inline
    Print the text inline.
.PARAMETER dark
    Print the text in dark yellow.
.EXAMPLE
    PS> Write-Yellow "This is yellow text."
    PS> Write-Yellow "This is dark yellow text." -dark
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
$color = if ($dark) { "DarkYellow" } else { "Yellow" }
if ($inline) {
    Write-Host -foregroundColor $color "$text" -NoNewline
    return
}
Write-Host -foregroundColor $color "$text"
