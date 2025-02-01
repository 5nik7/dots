<#
.SYNOPSIS
    Print text in black.
.DESCRIPTION
    The color of the text is black.
.PARAMETER text
    The text to print.
.PARAMETER inline
    Print the text inline.
.PARAMETER dark
    Print the text in black.
.EXAMPLE
    PS> Write-Black "This is dark gray text."
    PS> Write-Black "This is black text." -dark
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
$color = if ($dark) { "Black" } else { "DarkGray" }
if ($inline) {
    Write-Host -foregroundColor $color "$text" -NoNewline
    return
}
Write-Host -foregroundColor $color "$text"
