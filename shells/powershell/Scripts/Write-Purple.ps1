<#
.SYNOPSIS
    Print text in purple.
.DESCRIPTION
    The color of the text is purple (magenta).
.PARAMETER text
    The text to print.
.PARAMETER inline
    Print the text inline.
.EXAMPLE
    PS> Write-Purple "This is magenta text."
.NOTES
    Author: njen
#>
[CmdletBinding()]
param (
  [string]$text = '',
  [switch]$inline
)
if ($text -eq '' ) { $text = Read-Host 'text?' }
$color = 'Magenta'
if ($inline) {
  Write-Host -foregroundColor $color "$text" -NoNewline
  return
}
Write-Host -foregroundColor $color "$text"
