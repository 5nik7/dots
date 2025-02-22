<#
.SYNOPSIS
Print environment variables with optional highlighting.

.PARAMETER name
A string used to match and highlight entries based on their name.

.PARAMETER only
Only display matched entries.

.PARAMETER value
A string used to match and highlight entries based on their value.
#>

param (
    [string] $name,
    [string] $value,
    [switch] $only)

$format = '{0,-30} {1}'

Write-Host ($format -f 'Name', 'Value') -ForegroundColor Black
Write-Host ($format -f '----', '-----') -ForegroundColor Black

Get-ChildItem env: | Sort-Object name | ForEach-Object `
{
    $ename = $_.Name.ToString()
    if ($ename.Length -gt 30) { $ename = $ename.Substring(0, 27) + '...' }

    $evalue = $_.Value.ToString()
    $max = $host.UI.RawUI.WindowSize.Width - 32
    if ($evalue.Length -gt $max) { $evalue = $evalue.Substring(0, $max - 3) + '...' }

    if ($name -and ($_.Name -match $name)) {
        Write-Host ($format -f $ename, $evalue) -ForegroundColor Green
    }
    elseif ($value -and ($_.Value -match $value) -and !$only) {
        Write-Host ($format -f $ename, $evalue) -ForegroundColor Green
    }
    elseif ([String]::IsNullOrEmpty($name) -and [String]::IsNullOrEmpty($value) -and !$only) {
        if ($_.Name -eq 'COMPUTERNAME' -or $_.Name -eq 'USERDOMAIN') {
            Write-Host ($format -f $ename, $evalue) -ForegroundColor Cyan
        }
        elseif ($_.Name -match '^(Program|System|windir|ComSpec|DriverData|CommonProgram|COMPUTERNAME)|ALLUSERSPROFILE') {
            Write-Host ($format -f $ename, $evalue) -ForegroundColor Magenta
        }
        elseif ($_.Name -match '^(Path|PSModulePath|CARGO_HOME|JAVA_HOME|NVM|RUSTUP|NvimCopilotNode|PSCRIPTS|PSLAB)|BIN$') {
            Write-Host ($format -f $ename, $evalue) -ForegroundColor Green
        }
        elseif ($_.Name -match '^(PS)|LAB|DEV|PROJECTS|EDITOR') {
            Write-Host ($format -f $ename, $evalue) -ForegroundColor Yellow
        }
        elseif ($_.Name -match 'DOTS') {
            Write-Host ($format -f $ename, $evalue) -ForegroundColor Yellow
        }
        elseif ($_.Name -match '^(DOT|SHELLS|WALLS)|DOT$') {
            Write-Host ($format -f $ename, $evalue) -ForegroundColor DarkYellow
        }
        elseif ($_.Name -match '^(CONF|BACKUPS|APPDATA|LOCALAPPDATA|TEMP|TMP|DOCUMENTS|DOWNLOADS|HOMEDRIVE)|(CACHE|CONFIG)$') {
            Write-Host ($format -f $ename, $evalue) -ForegroundColor Blue
        }
        elseif ($evalue -match "$env:USERNAME(?:\\\w+){0,1}$") {
            Write-Host ($format -f $ename, $evalue) -ForegroundColor Blue
        }
        elseif ($_.Name -match 'AWS_') {
            Write-Host ($format -f $ename, $evalue) -ForegroundColor DarkYellow
        }
        elseif ($_.Name -match 'ConEmu' -or $_.Value.IndexOf('\') -lt 0) {
            Write-Host ($format -f $ename, $evalue) -ForegroundColor DarkGray
        }
        else {
            Write-Host ($format -f $ename, $evalue)
        }
    }
    elseif (!$only) {
        Write-Host ($format -f $ename, $evalue)
    }
}
