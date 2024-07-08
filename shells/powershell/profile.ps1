Set-Alias -Name cat -Value bat
Set-Alias -Name c -Value Clear-Host
Set-Alias -Name path -Value Get-Path
Set-Alias -Name env -Value Get-Env
Set-Alias -Name ls -Value Get-ChildItemPretty
Set-Alias -Name ll -Value Get-ChildItemPretty
Set-Alias -Name la -Value Get-ChildItemPretty
Set-Alias -Name l -Value Get-ChildItemPretty
Set-Alias -Name which -Value Show-Command
Set-Alias -Name touch -Value New-File
Set-Alias -Name d -Value ya
  
function ya {
	$tmp = [System.IO.Path]::GetTempFileName()
	yazi $args --cwd-file="$tmp"
	$cwd = Get-Content -Path $tmp
	if (-not [String]::IsNullOrEmpty($cwd) -and $cwd -ne $PWD.Path) {
		Set-Location -Path $cwd
	}
	Remove-Item -Path $tmp
}

function Get-ChildItemPretty {
	<#
    .SYNOPSIS
        Runs eza with a specific set of arguments. Plus some line breaks before and after the output.
        Alias: ls, ll, la, l
    #>
	[CmdletBinding()]
	param (
		[Parameter(Mandatory = $false, Position = 0)]
		[string]$Path = $PWD
	)

	Write-Host ""
	eza -a -l --group-directories-first --git-repos --git --icons --hyperlink --time-style relative $Path
	Write-Host ""
}

function New-File {
	<#
    .SYNOPSIS
        Creates a new file with the specified name and extension. Alias: touch
    #>
	[CmdletBinding()]
	param (
		[Parameter(Mandatory = $true, Position = 0)]
		[string]$Name
	)

	Write-Verbose "Creating new file '$Name'"
	New-Item -ItemType File -Name $Name -Path $PWD | Out-Null
}

function Show-Command {
	<#
    .SYNOPSIS
        Displays the definition of a command. Alias: which
    #>
	[CmdletBinding()]
	param (
		[Parameter(Mandatory = $true, Position = 0)]
		[string]$Name
	)
	Write-Verbose "Showing definition of '$Name'"
	Get-Command $Name | Select-Object -ExpandProperty Definition
}

function Get-Path {
	<#
	.SYNOPSIS
	Display the PATH environment variable as a list of strings rathan than a single string
	and displays the source of each value defined in the Registry: Machine, User, or Process

	.PARAMETER search
	An optional search string to find in each path.

	.PARAMETER sort
	Sorts the strings alphabetically, otherwise displays them in the order in which
	they appear in the PATH environment variable

	.DESCRIPTION
	Reports whether each path references an existing directory, if it is duplicated in 
	the PATH environment variable, if it is and empty entry. See the Repair-Path command
	for a description of how it cleans up the PATH. Also reports the PATH length and
	warns when it exceeds 80% capacity.
	#>

	# CmdletBinding adds -Verbose functionality, SupportsShouldProcess adds -WhatIf
	[CmdletBinding(SupportsShouldProcess = $true)]

	param (
		[string] $search,
		[switch] $sort
	)

	Begin {
		function ExpandPath ($path) {
			# check env variables in path like '%USREPROFILE%'
			$match = [Regex]::Match($path, '\%(.+)\%')
			if ($match.Success) {
				$evar = [Environment]::GetEnvironmentVariable( `
						$match.Value.Substring(1, $match.Value.Length - 2))

				if ($evar -and ($evar.Length -gt 0)) {
					return $path -replace $match.value, $evar
				}
			}

			return $path
		}
	}
	Process {
		# In order to avoid substitution of environment variables in path strings
		# we must pull the Path property raw values directly from the Registry.
		# Other mechanisms such as [Env]::GetEnvVar... will expand variables.

		$0 = 'SYSTEM\CurrentControlSet\Control\Session Manager\Environment'
		$sysKey = [Microsoft.Win32.Registry]::LocalMachine.OpenSubKey($0, $false <# readonly #>)
		$sysPaths = $sysKey.GetValue('Path', $null, 'DoNotExpandEnvironmentNames') -split ';'
		$sysExpos = $sysPaths | Where-Object { $_ -match '\%.+\%' } | ForEach-Object { ExpandPath $_ }
		$sysKey.Dispose()

		$usrKey = [Microsoft.Win32.Registry]::CurrentUser.OpenSubKey('Environment', $false <# readonly #>)
		$usrPaths = $usrKey.GetValue('Path', $null, 'DoNotExpandEnvironmentNames') -split ';'
		$usrExpos = $usrPaths | Where-Object { $_ -match '\%.+\%' } | ForEach-Object { ExpandPath $_ }
		$usrKey.Dispose()

		if ($VerbosePreference -eq 'Continue') {
			Write-Host 'Original System Paths' -ForegroundColor DarkYellow
			Write-Host ($sysPaths -join [Environment]::NewLine) -ForegroundColor DarkGray
			Write-Host 'Original User Paths' -ForegroundColor DarkYellow
			Write-Host ($usrPaths -join [Environment]::NewLine) -ForegroundColor DarkGray
			Write-Host
		}

		if ($sort) { $paths = $env:Path -split ';' | Sort-Object }
		else { $paths = $env:Path -split ';' }

		$duplicates = @()

		Write-Host
		$format = "{0,4}  {1}"

		foreach ($path in $paths) {
			$source = ''
			if (($sysExpos -contains $path) -or ($sysPaths -contains $path)) { $source += 'M' }
			if (($usrExpos -contains $path) -or ($usrPaths -contains $path)) { $source += 'U' }
			if ($source -eq '') { $source += 'P' }

			if ($path.Length -eq 0) {
				Write-Host '     -- EMPTY --' -ForegroundColor Yellow
			}
			elseif ($duplicates.Contains($path)) {
				Write-Host("$format ** DUPLICATE" -f $source, $path) -ForegroundColor Yellow
			}
			else {
				if (!(Test-Path $path)) {
					Write-Host("$format ** NOT FOUND" -f $source, $path) -ForegroundColor Red
				}
				elseif ($search -and $path.ToLower().Contains($search.ToLower())) {
					Write-Host($format -f $source, $path) -ForegroundColor Green
				}
				else {
					if ($source.Contains('P')) {
						Write-Host($format -f $source, $path) -ForegroundColor White
					}
					elseif ($source.Contains('U')) {
						if ($usrExpos -contains $path) { $source = "*$source" }
						Write-Host($format -f $source, $path) -ForegroundColor Gray
					}
					else {
						if ($sysExpos -contains $path) { $source = "*$source" }
						Write-Host($format -f $source, $path) -ForegroundColor DarkGray
					}
				}
			}

			$duplicates += $path
		}

		Write-Host
		Write-Host "PATH contains $($env:Path.Length) bytes" -NoNewline

		if (($env:Path).Length -gt ([Int16]::MaxValue * 0.80)) {
			Write-Host ' .. exceeds 80% capacity; consider removing unused entries' -ForegroundColor Red
		}
		Write-Host
	}
}

function Get-Env {
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

	Write-Host ($format -f 'Name', 'Value')
	Write-Host ($format -f '----', '-----')

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
			Write-Host ($format -f $ename, $evalue) -ForegroundColor DarkGreen
		}
		elseif ([String]::IsNullOrEmpty($name) -and [String]::IsNullOrEmpty($value) -and !$only) {
			if ($_.Name -eq 'COMPUTERNAME' -or $_.Name -eq 'USERDOMAIN') {
				Write-Host ($format -f $ename, $evalue) -ForegroundColor Blue
			}
			elseif ($_.Name -match 'APPDATA' -or $_.Name -eq 'ProgramData') {
				Write-Host ($format -f $ename, $evalue) -ForegroundColor Magenta
			}
			elseif ($evalue -match "$env:USERNAME(?:\\\w+){0,1}$") {
				Write-Host ($format -f $ename, $evalue) -ForegroundColor DarkGreen
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
}

if ($host.Name -eq 'ConsoleHost') {
	Import-Module PSReadLine
  
	$PSReadLineOptions = @{
		HistoryNoDuplicates           = $true
		HistorySearchCursorMovesToEnd = $true
		HistorySearchCaseSensitive    = $false
		MaximumHistoryCount           = "10000"
		ShowToolTips                  = $true
		ContinuationPrompt            = " "
		BellStyle                     = "None"
		PredictionSource              = "History"
		EditMode                      = "Vi"
		TerminateOrphanedConsoleApps  = $true
		PredictionViewStyle           = "InlineView"
		Colors                        = @{
			Comment                = 'DarkGray'
			Command                = 'Magenta'
			Emphasis               = 'Cyan'
			Number                 = 'Yellow'
			Member                 = 'Blue'
			Operator               = 'Blue'
			Type                   = 'Yellow'
			String                 = 'Green'
			Variable               = 'Cyan'
			Parameter              = 'Blue'
			ContinuationPrompt     = 'Black'
			Default                = 'White'
			InlinePrediction       = 'DarkGray'
			ListPrediction         = 'DarkGray'
			ListPredictionSelected = 'DarkGray'
			ListPredictionTooltip  = 'DarkGray'
		}
	}
	Set-PSReadLineOption @PSReadLineOptions
}

Set-PSReadlineKeyHandler -Key Tab -Function MenuComplete
Set-PSReadLineKeyHandler -Key UpArrow -Function HistorySearchBackward
Set-PSReadLineKeyHandler -Key DownArrow -Function HistorySearchForward
Set-PSReadLineKeyHandler -Chord Enter -Function ValidateAndAcceptLine


Invoke-Expression (&starship init powershell)
Enable-TransientPrompt
function Invoke-Starship-TransientFunction {
	&starship module character
}
Invoke-Expression (&starship init powershell)

Set-PSReadLineOption -ViModeIndicator script -ViModeChangeHandler {
	[Microsoft.PowerShell.PSConsoleReadLine]::InvokePrompt()
	if ($args[0] -eq 'Command') {
		# Set the cursor to a solid block.
		Write-Host -NoNewLine "`e[2 q"
	}
	else {
		# Set the cursor to a blinking line.
		Write-Host -NoNewLine "`e[5 q"
	}
}