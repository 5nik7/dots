﻿<#
.SYNOPSIS
	Writes the moon phase
.DESCRIPTION
	This PowerShell script writes the current moon phase to the console.
.EXAMPLE
	PS> ./write-moon.ps1
.LINK
	https://github.com/fleschutz/PowerShell
.NOTES
	Author: Markus Fleschutz | License: CC0
#>

try {
	(Invoke-WebRequest http://wttr.in/Moon -userAgent "curl" -useBasicParsing).Content
	exit 0 # success
} catch {
	" Error in line $($_.InvocationInfo.ScriptLineNumber): $($Error[0])"
	exit 1
}