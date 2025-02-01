<#
.SYNOPSIS
    Print text in white.
.DESCRIPTION
    The color of the text is white.
.PARAMETER text
    The text to print.
.PARAMETER inline
    Print the text inline.
.PARAMETER dark
    Print the text in gray.
.EXAMPLE
    PS> Write-White "This is white text."
    PS> Write-White "This is gray text." -dark
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
$color = if ($dark) { "Gray" } else { "White" }
if ($inline) {
    Write-Host -foregroundColor $color "$text" -NoNewline
    return
}
Write-Host -foregroundColor $color "$text"
