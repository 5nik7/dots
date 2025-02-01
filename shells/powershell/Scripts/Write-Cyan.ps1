<#
.SYNOPSIS
    Print text in cyan.
.DESCRIPTION
    The color of the text is cyan.
.PARAMETER text
    The text to print.
.PARAMETER inline
    Print the text inline.
.PARAMETER dark
    Print the text in dark cyan.
.EXAMPLE
    PS> Write-Cyan "This is cyan text."
    PS> Write-Cyan "This is dark cyan text." -dark
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
$color = if ($dark) { "DarkCyan" } else { "Cyan" }
if ($inline) {
    Write-Host -foregroundColor $color "$text" -NoNewline
    return
}
Write-Host -foregroundColor $color "$text"
