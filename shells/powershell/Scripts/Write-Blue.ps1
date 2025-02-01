<#
.SYNOPSIS
    Print text in blue.
.DESCRIPTION
    The color of the text is blue.
.PARAMETER text
    The text to print.
.PARAMETER inline
    Print the text inline.
.PARAMETER dark
    Print the text in dark blue.
.EXAMPLE
    PS> Write-Blue "This is blue text."
    PS> Write-Blue "This is dark blue text." -dark
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
$color = if ($dark) { "DarkBlue" } else { "Blue" }
if ($inline) {
    Write-Host -foregroundColor $color "$text" -NoNewline
    return
}
Write-Host -foregroundColor $color "$text"
