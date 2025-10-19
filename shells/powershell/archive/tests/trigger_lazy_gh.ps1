# Start a fresh session: clear any existing gh completer variable then invoke lazy wrapper
Remove-Variable -Name '__ghCompleterBlock' -Scope Global -ErrorAction SilentlyContinue
. 'C:\Users\njen\dots\shells\powershell\Microsoft.PowerShell_profile.ps1'
Write-Host "Lazy wrapper present: $([bool](Get-Variable -Name '__lazy_gh' -Scope Global -ErrorAction SilentlyContinue))"
# Invoke the lazy wrapper stored in __lazy_gh
if (Get-Variable -Name '__lazy_gh' -Scope Global -ErrorAction SilentlyContinue) {
	& (Get-Variable -Name '__lazy_gh' -Scope Global).Value -WordToComplete '' -CommandAst $null -CursorPosition 0
	Write-Host 'Invoked lazy wrapper'
} else {
	Write-Host 'Lazy wrapper missing'
}
