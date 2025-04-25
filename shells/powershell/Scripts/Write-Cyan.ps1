<#
.SYNOPSIS
    Print text in cyan.
.DESCRIPTION
    The color of the text is cyan.
.PARAMETER text
    The text to print.
.PARAMETER inline
    Print the text inline.
.EXAMPLE
    PS> Write-Cyan "This is cyan text."
.NOTES
    Author: njen
#>
[CmdletBinding()]
param (
  [string]$text = '',
  [switch]$inline
)
if ($text -eq '' ) { $text = Read-Host 'text?' }
$color = 'Cyan'
if ($inline) {
  Write-Host -foregroundColor $color "$text" -NoNewline
  return
}
Write-Host -foregroundColor $color "$text"
