<#
.SYNOPSIS
List all external scripts and their parameter names. These are all of the
scripts implemented in your WindowsPowerShell profile Modules/Scripts folder.

.DESCRIPTION
Any aliases are listed along with each command.
#>

$sysparams = @(
    'Verbose', 'Debug', 'ErrorAction', 'WarningAction', 'InformationAction', 'ErrorVariable',
    'WarningVariable', 'InformationVariable', 'OutVariable', 'OutBuffer', 'PipelineVariable'
)

$aliases = @{}

Get-Alias | ForEach-Object { if ($aliases[$_.Definition] -eq $null) { $aliases.Add($_.Definition, $_.Name) } }

$scriptsPath = $Env:PSCRIPTS

Get-Command -CommandType ExternalScript | ForEach-Object `
{
    $name = [IO.Path]::GetFileNameWithoutExtension($_.Name)
    if ($_.Source -like "$scriptsPath\*") {
        Write-Host "$name " -NoNewline

        $parameters = $_.Parameters
        if ($parameters -ne $null) {
            $parameters.Keys | Where-Object { $sysparams -notcontains $_ } | ForEach-Object `
            {
                $p = $parameters[$_]
                $c = if ($p.ParameterType -like 'Switch') { 'DarkGray' } else { 'DarkCyan' }
                Write-Host "-$_ " -NoNewline -ForegroundColor $c
            }
        }

        $alias = $aliases[$name]
        if ($alias) {
            Write-Host " ($alias)" -ForegroundColor DarkGreen -NoNewline
        }

        Write-Host
    }
}
