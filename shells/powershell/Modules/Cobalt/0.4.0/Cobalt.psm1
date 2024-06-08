# Module created by Microsoft.PowerShell.Crescendo
# Version: 1.1.0
# Schema: https://aka.ms/PowerShell/Crescendo/Schemas/2022-06
# Generated at: 02/05/2023 17:02:36
class PowerShellCustomFunctionAttribute : System.Attribute { 
    [bool]$RequiresElevation
    [string]$Source
    PowerShellCustomFunctionAttribute() { $this.RequiresElevation = $false; $this.Source = "Microsoft.PowerShell.Crescendo" }
    PowerShellCustomFunctionAttribute([bool]$rElevation) {
        $this.RequiresElevation = $rElevation
        $this.Source = "Microsoft.PowerShell.Crescendo"
    }
}

# Queue for holding errors
$__CrescendoNativeErrorQueue = [System.Collections.Queue]::new()
# Returns available errors
# Assumes that we are being called from within a script cmdlet when EmitAsError is used.
function Pop-CrescendoNativeError {
param ([switch]$EmitAsError)
    while ($__CrescendoNativeErrorQueue.Count -gt 0) {
        if ($EmitAsError) {
            $msg = $__CrescendoNativeErrorQueue.Dequeue()
            $er = [System.Management.Automation.ErrorRecord]::new([system.invalidoperationexception]::new($msg), $PSCmdlet.Name, "InvalidOperation", $msg)
            $PSCmdlet.WriteError($er)
        }
        else {
            $__CrescendoNativeErrorQueue.Dequeue()
        }
    }
}
# this is purposefully a filter rather than a function for streaming errors
filter Push-CrescendoNativeError {
    if ($_ -is [System.Management.Automation.ErrorRecord]) {
        $__CrescendoNativeErrorQueue.Enqueue($_)
    }
    else {
        $_
    }
}

function Get-WinGetSource
{
[PowerShellCustomFunctionAttribute(RequiresElevation=$False)]
[CmdletBinding()]

param(
[Parameter()]
[string]$Name
    )

BEGIN {
    $__PARAMETERMAP = @{
         Name = @{
               OriginalName = '--name='
               OriginalPosition = '0'
               Position = '2147483647'
               ParameterType = 'string'
               ApplyToExecutable = $False
               NoGap = $True
               ArgumentTransform = '$args'
               ArgumentTransformType = 'inline'
               }
    }

    $__outputHandlers = @{
        Default = @{ StreamOutput = $False; Handler = { 
                        param ($output)
                        if ($output) {
                            $output | ConvertFrom-Json
                        }
                     } }
    }
}

PROCESS {
    $__boundParameters = $PSBoundParameters
    $__defaultValueParameters = $PSCmdlet.MyInvocation.MyCommand.Parameters.Values.Where({$_.Attributes.Where({$_.TypeId.Name -eq "PSDefaultValueAttribute"})}).Name
    $__defaultValueParameters.Where({ !$__boundParameters["$_"] }).ForEach({$__boundParameters["$_"] = get-variable -value $_})
    $__commandArgs = @()
    $MyInvocation.MyCommand.Parameters.Values.Where({$_.SwitchParameter -and $_.Name -notmatch "Debug|Whatif|Confirm|Verbose" -and ! $__boundParameters[$_.Name]}).ForEach({$__boundParameters[$_.Name] = [switch]::new($false)})
    if ($__boundParameters["Debug"]){wait-debugger}
    $__commandArgs += 'source'
    $__commandArgs += 'export'
    foreach ($paramName in $__boundParameters.Keys|
            Where-Object {!$__PARAMETERMAP[$_].ApplyToExecutable}|
            Sort-Object {$__PARAMETERMAP[$_].OriginalPosition}) {
        $value = $__boundParameters[$paramName]
        $param = $__PARAMETERMAP[$paramName]
        if ($param) {
            if ($value -is [switch]) {
                 if ($value.IsPresent) {
                     if ($param.OriginalName) { $__commandArgs += $param.OriginalName }
                 }
                 elseif ($param.DefaultMissingValue) { $__commandArgs += $param.DefaultMissingValue }
            }
            elseif ( $param.NoGap ) {
                $pFmt = "{0}{1}"
                if($value -match "\s") { $pFmt = "{0}""{1}""" }
                $__commandArgs += $pFmt -f $param.OriginalName, $value
            }
            else {
                if($param.OriginalName) { $__commandArgs += $param.OriginalName }
                if($param.ArgumentTransformType -eq 'inline') {
                   $transform = [scriptblock]::Create($param.ArgumentTransform)
                }
                else {
                   $transform = $param.ArgumentTransform
                }
                $__commandArgs += & $transform $value
            }
        }
    }
    $__commandArgs = $__commandArgs | Where-Object {$_ -ne $null}
    if ($__boundParameters["Debug"]){wait-debugger}
    if ( $__boundParameters["Verbose"]) {
         Write-Verbose -Verbose -Message "WinGet"
         $__commandArgs | Write-Verbose -Verbose
    }
    $__handlerInfo = $__outputHandlers[$PSCmdlet.ParameterSetName]
    if (! $__handlerInfo ) {
        $__handlerInfo = $__outputHandlers["Default"] # Guaranteed to be present
    }
    $__handler = $__handlerInfo.Handler
    if ( $PSCmdlet.ShouldProcess("WinGet $__commandArgs")) {
    # check for the application and throw if it cannot be found
        if ( -not (Get-Command -ErrorAction Ignore "WinGet")) {
          throw "Cannot find executable 'WinGet'"
        }
        if ( $__handlerInfo.StreamOutput ) {
            if ( $null -eq $__handler ) {
                & "WinGet" $__commandArgs
            }
            else {
                & "WinGet" $__commandArgs 2>&1| Push-CrescendoNativeError | & $__handler
            }
        }
        else {
            $result = & "WinGet" $__commandArgs 2>&1| Push-CrescendoNativeError
            & $__handler $result
        }
    }
  } # end PROCESS

<#


.DESCRIPTION
Return WinGet package sources

.PARAMETER Name
Source Name



#>
}


function Register-WinGetSource
{
[PowerShellCustomFunctionAttribute(RequiresElevation=$False)]
[CmdletBinding()]

param(
[Parameter(Mandatory=$true)]
[string]$Name,
[Parameter(Mandatory=$true)]
[string]$Argument
    )

BEGIN {
    $__PARAMETERMAP = @{
         Name = @{
               OriginalName = '--name='
               OriginalPosition = '0'
               Position = '2147483647'
               ParameterType = 'string'
               ApplyToExecutable = $False
               NoGap = $True
               ArgumentTransform = '$args'
               ArgumentTransformType = 'inline'
               }
         Argument = @{
               OriginalName = '--arg='
               OriginalPosition = '0'
               Position = '2147483647'
               ParameterType = 'string'
               ApplyToExecutable = $False
               NoGap = $True
               ArgumentTransform = '$args'
               ArgumentTransformType = 'inline'
               }
    }

    $__outputHandlers = @{
        Default = @{ StreamOutput = $False; Handler = { 
                        param ($output)
                        if ($output) {
                            if ($output[-1] -ne 'Done') {
                                Write-Error ($output -join "`r`n")
                            }
                        }
                     } }
    }
}

PROCESS {
    $__boundParameters = $PSBoundParameters
    $__defaultValueParameters = $PSCmdlet.MyInvocation.MyCommand.Parameters.Values.Where({$_.Attributes.Where({$_.TypeId.Name -eq "PSDefaultValueAttribute"})}).Name
    $__defaultValueParameters.Where({ !$__boundParameters["$_"] }).ForEach({$__boundParameters["$_"] = get-variable -value $_})
    $__commandArgs = @()
    $MyInvocation.MyCommand.Parameters.Values.Where({$_.SwitchParameter -and $_.Name -notmatch "Debug|Whatif|Confirm|Verbose" -and ! $__boundParameters[$_.Name]}).ForEach({$__boundParameters[$_.Name] = [switch]::new($false)})
    if ($__boundParameters["Debug"]){wait-debugger}
    $__commandArgs += 'source'
    $__commandArgs += 'add'
    foreach ($paramName in $__boundParameters.Keys|
            Where-Object {!$__PARAMETERMAP[$_].ApplyToExecutable}|
            Sort-Object {$__PARAMETERMAP[$_].OriginalPosition}) {
        $value = $__boundParameters[$paramName]
        $param = $__PARAMETERMAP[$paramName]
        if ($param) {
            if ($value -is [switch]) {
                 if ($value.IsPresent) {
                     if ($param.OriginalName) { $__commandArgs += $param.OriginalName }
                 }
                 elseif ($param.DefaultMissingValue) { $__commandArgs += $param.DefaultMissingValue }
            }
            elseif ( $param.NoGap ) {
                $pFmt = "{0}{1}"
                if($value -match "\s") { $pFmt = "{0}""{1}""" }
                $__commandArgs += $pFmt -f $param.OriginalName, $value
            }
            else {
                if($param.OriginalName) { $__commandArgs += $param.OriginalName }
                if($param.ArgumentTransformType -eq 'inline') {
                   $transform = [scriptblock]::Create($param.ArgumentTransform)
                }
                else {
                   $transform = $param.ArgumentTransform
                }
                $__commandArgs += & $transform $value
            }
        }
    }
    $__commandArgs = $__commandArgs | Where-Object {$_ -ne $null}
    if ($__boundParameters["Debug"]){wait-debugger}
    if ( $__boundParameters["Verbose"]) {
         Write-Verbose -Verbose -Message "WinGet"
         $__commandArgs | Write-Verbose -Verbose
    }
    $__handlerInfo = $__outputHandlers[$PSCmdlet.ParameterSetName]
    if (! $__handlerInfo ) {
        $__handlerInfo = $__outputHandlers["Default"] # Guaranteed to be present
    }
    $__handler = $__handlerInfo.Handler
    if ( $PSCmdlet.ShouldProcess("WinGet $__commandArgs")) {
    # check for the application and throw if it cannot be found
        if ( -not (Get-Command -ErrorAction Ignore "WinGet")) {
          throw "Cannot find executable 'WinGet'"
        }
        if ( $__handlerInfo.StreamOutput ) {
            if ( $null -eq $__handler ) {
                & "WinGet" $__commandArgs
            }
            else {
                & "WinGet" $__commandArgs 2>&1| Push-CrescendoNativeError | & $__handler
            }
        }
        else {
            $result = & "WinGet" $__commandArgs 2>&1| Push-CrescendoNativeError
            & $__handler $result
        }
    }
  } # end PROCESS

<#


.DESCRIPTION
Register a new WinGet package source

.PARAMETER Name
Source Name


.PARAMETER Argument
Source Argument



#>
}


function Unregister-WinGetSource
{
[PowerShellCustomFunctionAttribute(RequiresElevation=$False)]
[CmdletBinding()]

param(
[Parameter(ValueFromPipelineByPropertyName=$true,Mandatory=$true)]
[string]$Name
    )

BEGIN {
    $__PARAMETERMAP = @{
         Name = @{
               OriginalName = '--name='
               OriginalPosition = '0'
               Position = '2147483647'
               ParameterType = 'string'
               ApplyToExecutable = $False
               NoGap = $True
               ArgumentTransform = '$args'
               ArgumentTransformType = 'inline'
               }
    }

    $__outputHandlers = @{
        Default = @{ StreamOutput = $False; Handler = { 
                        param ($output)
                        if ($output) {
                            if ($output[-1] -match 'Did not find a source') {
                                Write-Error ($output -join "`r`n")
                            }
                        }
                     } }
    }
}

PROCESS {
    $__boundParameters = $PSBoundParameters
    $__defaultValueParameters = $PSCmdlet.MyInvocation.MyCommand.Parameters.Values.Where({$_.Attributes.Where({$_.TypeId.Name -eq "PSDefaultValueAttribute"})}).Name
    $__defaultValueParameters.Where({ !$__boundParameters["$_"] }).ForEach({$__boundParameters["$_"] = get-variable -value $_})
    $__commandArgs = @()
    $MyInvocation.MyCommand.Parameters.Values.Where({$_.SwitchParameter -and $_.Name -notmatch "Debug|Whatif|Confirm|Verbose" -and ! $__boundParameters[$_.Name]}).ForEach({$__boundParameters[$_.Name] = [switch]::new($false)})
    if ($__boundParameters["Debug"]){wait-debugger}
    $__commandArgs += 'source'
    $__commandArgs += 'remove'
    foreach ($paramName in $__boundParameters.Keys|
            Where-Object {!$__PARAMETERMAP[$_].ApplyToExecutable}|
            Sort-Object {$__PARAMETERMAP[$_].OriginalPosition}) {
        $value = $__boundParameters[$paramName]
        $param = $__PARAMETERMAP[$paramName]
        if ($param) {
            if ($value -is [switch]) {
                 if ($value.IsPresent) {
                     if ($param.OriginalName) { $__commandArgs += $param.OriginalName }
                 }
                 elseif ($param.DefaultMissingValue) { $__commandArgs += $param.DefaultMissingValue }
            }
            elseif ( $param.NoGap ) {
                $pFmt = "{0}{1}"
                if($value -match "\s") { $pFmt = "{0}""{1}""" }
                $__commandArgs += $pFmt -f $param.OriginalName, $value
            }
            else {
                if($param.OriginalName) { $__commandArgs += $param.OriginalName }
                if($param.ArgumentTransformType -eq 'inline') {
                   $transform = [scriptblock]::Create($param.ArgumentTransform)
                }
                else {
                   $transform = $param.ArgumentTransform
                }
                $__commandArgs += & $transform $value
            }
        }
    }
    $__commandArgs = $__commandArgs | Where-Object {$_ -ne $null}
    if ($__boundParameters["Debug"]){wait-debugger}
    if ( $__boundParameters["Verbose"]) {
         Write-Verbose -Verbose -Message "WinGet"
         $__commandArgs | Write-Verbose -Verbose
    }
    $__handlerInfo = $__outputHandlers[$PSCmdlet.ParameterSetName]
    if (! $__handlerInfo ) {
        $__handlerInfo = $__outputHandlers["Default"] # Guaranteed to be present
    }
    $__handler = $__handlerInfo.Handler
    if ( $PSCmdlet.ShouldProcess("WinGet $__commandArgs")) {
    # check for the application and throw if it cannot be found
        if ( -not (Get-Command -ErrorAction Ignore "WinGet")) {
          throw "Cannot find executable 'WinGet'"
        }
        if ( $__handlerInfo.StreamOutput ) {
            if ( $null -eq $__handler ) {
                & "WinGet" $__commandArgs
            }
            else {
                & "WinGet" $__commandArgs 2>&1| Push-CrescendoNativeError | & $__handler
            }
        }
        else {
            $result = & "WinGet" $__commandArgs 2>&1| Push-CrescendoNativeError
            & $__handler $result
        }
    }
  } # end PROCESS

<#


.DESCRIPTION
Unegister an existing WinGet package source

.PARAMETER Name
Source Name



#>
}


function Install-WinGetPackage
{
[PowerShellCustomFunctionAttribute(RequiresElevation=$False)]
[CmdletBinding()]

param(
[Parameter(ValueFromPipelineByPropertyName=$true)]
[string]$ID,
[Parameter()]
[switch]$Exact,
[Parameter(ValueFromPipelineByPropertyName=$true)]
[string]$Source,
[Parameter(ValueFromPipelineByPropertyName=$true)]
[string]$Version
    )

BEGIN {
    $__PARAMETERMAP = @{
         ID = @{
               OriginalName = '--id='
               OriginalPosition = '0'
               Position = '2147483647'
               ParameterType = 'string'
               ApplyToExecutable = $False
               NoGap = $True
               ArgumentTransform = '$args'
               ArgumentTransformType = 'inline'
               }
         Exact = @{
               OriginalName = '--exact'
               OriginalPosition = '0'
               Position = '2147483647'
               ParameterType = 'switch'
               ApplyToExecutable = $False
               NoGap = $False
               ArgumentTransform = '$args'
               ArgumentTransformType = 'inline'
               }
         Source = @{
               OriginalName = '--source='
               OriginalPosition = '0'
               Position = '2147483647'
               ParameterType = 'string'
               ApplyToExecutable = $False
               NoGap = $True
               ArgumentTransform = '$args'
               ArgumentTransformType = 'inline'
               }
         Version = @{
               OriginalName = '--version='
               OriginalPosition = '0'
               Position = '2147483647'
               ParameterType = 'string'
               ApplyToExecutable = $False
               NoGap = $True
               ArgumentTransform = '$args'
               ArgumentTransformType = 'inline'
               }
    }

    $__outputHandlers = @{
        Default = @{ StreamOutput = $False; Handler = { param ($output)
    $language = (Get-UICulture).Name

    $languageData = $(
        $hash = @{}

        $(try {
            # We have to trim the leading BOM for .NET's XML parser to correctly read Microsoft's own files - go figure
            ([xml](((Invoke-WebRequest -Uri "https://raw.githubusercontent.com/microsoft/winget-cli/v1.3.2691/Localization/Resources/$language/winget.resw" -ErrorAction Stop ).Content -replace "\uFEFF", ""))).root.data
        } catch {
            # Fall back to English if a locale file doesn't exist
            (
                ('SearchName','Name'),
                ('SearchID','Id'),
                ('SearchVersion','Version'),
                ('AvailableHeader','Available'),
                ('SearchSource','Source'),
                ('ShowVersion','Version'),
                ('GetManifestResultVersionNotFound','No version found matching:'),
                ('InstallerFailedWithCode','Installer failed with exit code:'),
                ('UninstallFailedWithCode','Uninstall failed with exit code:'),
                ('AvailableUpgrades','upgrades available.')
            ) | ForEach-Object {[pscustomobject]@{name = $_[0]; value = $_[1]}}
        }) | ForEach-Object {
            # Convert the array into a hashtable
            $hash[$_.name] = $_.value
        }

        $hash
    )

    if ($output) {
        if ($output -match $languageData.InstallerFailedWithCode) {
            # Only show output that matches or comes after the 'failed' keyword
            Write-Error ($output[$output.IndexOf($($output -match $languageData.InstallerFailedWithCode | Select-Object -First 1))..($output.Length-1)] -join "`r`n")
        } else {
            $output | ForEach-Object {
                if ($_ -match 'Found .+ \[(?<id>[\S]+)\] Version (?<version>[\S]+)' -and $Matches.id -and $Matches.version) {
                    [pscustomobject]@{
                        ID = $Matches.id
                        Version = $Matches.version
                    }
                }
            }
        }
    }
 } }
    }
}

PROCESS {
    $__boundParameters = $PSBoundParameters
    $__defaultValueParameters = $PSCmdlet.MyInvocation.MyCommand.Parameters.Values.Where({$_.Attributes.Where({$_.TypeId.Name -eq "PSDefaultValueAttribute"})}).Name
    $__defaultValueParameters.Where({ !$__boundParameters["$_"] }).ForEach({$__boundParameters["$_"] = get-variable -value $_})
    $__commandArgs = @()
    $MyInvocation.MyCommand.Parameters.Values.Where({$_.SwitchParameter -and $_.Name -notmatch "Debug|Whatif|Confirm|Verbose" -and ! $__boundParameters[$_.Name]}).ForEach({$__boundParameters[$_.Name] = [switch]::new($false)})
    if ($__boundParameters["Debug"]){wait-debugger}
    $__commandArgs += 'install'
    $__commandArgs += '--accept-package-agreements'
    $__commandArgs += '--accept-source-agreements'
    $__commandArgs += '--silent'
    foreach ($paramName in $__boundParameters.Keys|
            Where-Object {!$__PARAMETERMAP[$_].ApplyToExecutable}|
            Sort-Object {$__PARAMETERMAP[$_].OriginalPosition}) {
        $value = $__boundParameters[$paramName]
        $param = $__PARAMETERMAP[$paramName]
        if ($param) {
            if ($value -is [switch]) {
                 if ($value.IsPresent) {
                     if ($param.OriginalName) { $__commandArgs += $param.OriginalName }
                 }
                 elseif ($param.DefaultMissingValue) { $__commandArgs += $param.DefaultMissingValue }
            }
            elseif ( $param.NoGap ) {
                $pFmt = "{0}{1}"
                if($value -match "\s") { $pFmt = "{0}""{1}""" }
                $__commandArgs += $pFmt -f $param.OriginalName, $value
            }
            else {
                if($param.OriginalName) { $__commandArgs += $param.OriginalName }
                if($param.ArgumentTransformType -eq 'inline') {
                   $transform = [scriptblock]::Create($param.ArgumentTransform)
                }
                else {
                   $transform = $param.ArgumentTransform
                }
                $__commandArgs += & $transform $value
            }
        }
    }
    $__commandArgs = $__commandArgs | Where-Object {$_ -ne $null}
    if ($__boundParameters["Debug"]){wait-debugger}
    if ( $__boundParameters["Verbose"]) {
         Write-Verbose -Verbose -Message "WinGet"
         $__commandArgs | Write-Verbose -Verbose
    }
    $__handlerInfo = $__outputHandlers[$PSCmdlet.ParameterSetName]
    if (! $__handlerInfo ) {
        $__handlerInfo = $__outputHandlers["Default"] # Guaranteed to be present
    }
    $__handler = $__handlerInfo.Handler
    if ( $PSCmdlet.ShouldProcess("WinGet $__commandArgs")) {
    # check for the application and throw if it cannot be found
        if ( -not (Get-Command -ErrorAction Ignore "WinGet")) {
          throw "Cannot find executable 'WinGet'"
        }
        if ( $__handlerInfo.StreamOutput ) {
            if ( $null -eq $__handler ) {
                & "WinGet" $__commandArgs
            }
            else {
                & "WinGet" $__commandArgs 2>&1| Push-CrescendoNativeError | & $__handler
            }
        }
        else {
            $result = & "WinGet" $__commandArgs 2>&1| Push-CrescendoNativeError
            & $__handler $result
        }
    }
  } # end PROCESS

<#


.DESCRIPTION
Install a new package with WinGet

.PARAMETER ID
Package ID


.PARAMETER Exact
Search by exact package name


.PARAMETER Source
Package Source


.PARAMETER Version
Package Version



#>
}


function Get-WinGetPackage
{
[PowerShellCustomFunctionAttribute(RequiresElevation=$False)]
[CmdletBinding()]

param(
[Parameter(ValueFromPipelineByPropertyName=$true)]
[string]$ID,
[Parameter()]
[switch]$Exact,
[Parameter(ValueFromPipelineByPropertyName=$true)]
[string]$Source
    )

BEGIN {
    $__PARAMETERMAP = @{
         ID = @{
               OriginalName = '--id='
               OriginalPosition = '0'
               Position = '2147483647'
               ParameterType = 'string'
               ApplyToExecutable = $False
               NoGap = $True
               ArgumentTransform = '$args'
               ArgumentTransformType = 'inline'
               }
         Exact = @{
               OriginalName = '--exact'
               OriginalPosition = '0'
               Position = '2147483647'
               ParameterType = 'switch'
               ApplyToExecutable = $False
               NoGap = $False
               ArgumentTransform = '$args'
               ArgumentTransformType = 'inline'
               }
         Source = @{
               OriginalName = '--source='
               OriginalPosition = '0'
               Position = '2147483647'
               ParameterType = 'string'
               ApplyToExecutable = $False
               NoGap = $True
               ArgumentTransform = '$args'
               ArgumentTransformType = 'inline'
               }
    }

    $__outputHandlers = @{
        Default = @{ StreamOutput = $False; Handler = { param ($output)
    $language = (Get-UICulture).Name

    $languageData = $(
        $hash = @{}

        $(try {
            # We have to trim the leading BOM for .NET's XML parser to correctly read Microsoft's own files - go figure
            ([xml](((Invoke-WebRequest -Uri "https://raw.githubusercontent.com/microsoft/winget-cli/v1.3.2691/Localization/Resources/$language/winget.resw" -ErrorAction Stop ).Content -replace "\uFEFF", ""))).root.data
        } catch {
            # Fall back to English if a locale file doesn't exist
            (
                ('SearchName','Name'),
                ('SearchID','Id'),
                ('SearchVersion','Version'),
                ('AvailableHeader','Available'),
                ('SearchSource','Source'),
                ('ShowVersion','Version'),
                ('GetManifestResultVersionNotFound','No version found matching:'),
                ('InstallerFailedWithCode','Installer failed with exit code:'),
                ('UninstallFailedWithCode','Uninstall failed with exit code:'),
                ('AvailableUpgrades','upgrades available.')
            ) | ForEach-Object {[pscustomobject]@{name = $_[0]; value = $_[1]}}
        }) | ForEach-Object {
            # Convert the array into a hashtable
            $hash[$_.name] = $_.value
        }

        $hash
    )

    $nameHeader = $output -Match "^$($languageData.SearchName)"

    if ($nameHeader) {

        $headerLine = $output.IndexOf(($nameHeader | Select-Object -First 1))

        if ($headerLine -ne -1) {
            $idIndex = $output[$headerLine].IndexOf(($languageData.SearchID))
            $versionIndex = $output[$headerLine].IndexOf(($languageData.SearchVersion))
            $availableIndex = $output[$headerLine].IndexOf(($languageData.AvailableHeader))
            $sourceIndex = $output[$headerLine].IndexOf(($languageData.SearchSource))

            # Stop gathering version data at the 'Available' column if it exists, if not continue on to the 'Source' column (if it exists)
            $versionEndIndex = $(
                if ($availableIndex -ne -1) {
                    $availableIndex
                } else {
                    $sourceIndex
                }
            )

            # Only attempt to parse output if it contains a 'version' column
            if ($versionIndex -ne -1) {
                # The -replace cleans up errant characters that come from WinGet's poor treatment of truncated columnar output
                ($output | Select-String -Pattern $languageData.AvailableUpgrades,'--include-unknown' -NotMatch) -replace '[^i\p{IsBasicLatin}]+',' ' | Select-Object -Skip ($headerLine+2) | ForEach-Object {
                    Remove-Variable -Name 'package' -ErrorAction SilentlyContinue

                    $package = [ordered]@{
                        ID = $_.SubString($idIndex,$versionIndex-$idIndex).Trim()
                    }

                    if ($package) {
                        # I'm so sorry, blame WinGet
                        # If neither the 'Available' or 'Source' column exist, gather version data to the end of the string
                        $package.Version = $(
                            if ($versionEndIndex -ne -1) {
                                $_.SubString($versionIndex,$versionEndIndex-$versionIndex)
                            } else {
                                $_.SubString($versionIndex)
                            }
                        ).Trim() -replace '[^\.\d]'

                        # Only attempt to add 'Available Version' data if the column exists
                        if ($availableIndex -ne -1) {
                            $package.Available = $(
                                if ($sourceIndex -ne -1) {
                                    $_.SubString($availableIndex,$sourceIndex-$availableIndex)
                                } else {
                                    $_.SubString($availableIndex)
                                }
                            ).Trim() -replace '[^\.\d]'
                        }

                        # If the 'Source' column was included in the output, include it in our output, too
                        if (($sourceIndex -ne -1) -And ($_.Length -ge $sourceIndex)) {
                            $package.Source = $_.SubString($sourceIndex).Trim() -split ' ' | Select-Object -Last 1
                        }

                        [pscustomobject]$package
                    }
                }
            }
        }
    }
 } }
    }
}

PROCESS {
    $__boundParameters = $PSBoundParameters
    $__defaultValueParameters = $PSCmdlet.MyInvocation.MyCommand.Parameters.Values.Where({$_.Attributes.Where({$_.TypeId.Name -eq "PSDefaultValueAttribute"})}).Name
    $__defaultValueParameters.Where({ !$__boundParameters["$_"] }).ForEach({$__boundParameters["$_"] = get-variable -value $_})
    $__commandArgs = @()
    $MyInvocation.MyCommand.Parameters.Values.Where({$_.SwitchParameter -and $_.Name -notmatch "Debug|Whatif|Confirm|Verbose" -and ! $__boundParameters[$_.Name]}).ForEach({$__boundParameters[$_.Name] = [switch]::new($false)})
    if ($__boundParameters["Debug"]){wait-debugger}
    $__commandArgs += 'list'
    $__commandArgs += '--accept-source-agreements'
    foreach ($paramName in $__boundParameters.Keys|
            Where-Object {!$__PARAMETERMAP[$_].ApplyToExecutable}|
            Sort-Object {$__PARAMETERMAP[$_].OriginalPosition}) {
        $value = $__boundParameters[$paramName]
        $param = $__PARAMETERMAP[$paramName]
        if ($param) {
            if ($value -is [switch]) {
                 if ($value.IsPresent) {
                     if ($param.OriginalName) { $__commandArgs += $param.OriginalName }
                 }
                 elseif ($param.DefaultMissingValue) { $__commandArgs += $param.DefaultMissingValue }
            }
            elseif ( $param.NoGap ) {
                $pFmt = "{0}{1}"
                if($value -match "\s") { $pFmt = "{0}""{1}""" }
                $__commandArgs += $pFmt -f $param.OriginalName, $value
            }
            else {
                if($param.OriginalName) { $__commandArgs += $param.OriginalName }
                if($param.ArgumentTransformType -eq 'inline') {
                   $transform = [scriptblock]::Create($param.ArgumentTransform)
                }
                else {
                   $transform = $param.ArgumentTransform
                }
                $__commandArgs += & $transform $value
            }
        }
    }
    $__commandArgs = $__commandArgs | Where-Object {$_ -ne $null}
    if ($__boundParameters["Debug"]){wait-debugger}
    if ( $__boundParameters["Verbose"]) {
         Write-Verbose -Verbose -Message "WinGet"
         $__commandArgs | Write-Verbose -Verbose
    }
    $__handlerInfo = $__outputHandlers[$PSCmdlet.ParameterSetName]
    if (! $__handlerInfo ) {
        $__handlerInfo = $__outputHandlers["Default"] # Guaranteed to be present
    }
    $__handler = $__handlerInfo.Handler
    if ( $PSCmdlet.ShouldProcess("WinGet $__commandArgs")) {
    # check for the application and throw if it cannot be found
        if ( -not (Get-Command -ErrorAction Ignore "WinGet")) {
          throw "Cannot find executable 'WinGet'"
        }
        if ( $__handlerInfo.StreamOutput ) {
            if ( $null -eq $__handler ) {
                & "WinGet" $__commandArgs
            }
            else {
                & "WinGet" $__commandArgs 2>&1| Push-CrescendoNativeError | & $__handler
            }
        }
        else {
            $result = & "WinGet" $__commandArgs 2>&1| Push-CrescendoNativeError
            & $__handler $result
        }
    }
  } # end PROCESS

<#


.DESCRIPTION
Get a list of installed WinGet packages

.PARAMETER ID
Package ID


.PARAMETER Exact
Search by exact package name


.PARAMETER Source
Package Source



#>
}


function Find-WinGetPackage
{
[PowerShellCustomFunctionAttribute(RequiresElevation=$False)]
[CmdletBinding()]

param(
[Parameter(ValueFromPipelineByPropertyName=$true)]
[string]$ID,
[Parameter()]
[switch]$Exact,
[Parameter(ValueFromPipelineByPropertyName=$true)]
[string]$Source
    )

BEGIN {
    $__PARAMETERMAP = @{
         ID = @{
               OriginalName = '--id='
               OriginalPosition = '0'
               Position = '2147483647'
               ParameterType = 'string'
               ApplyToExecutable = $False
               NoGap = $True
               ArgumentTransform = '$args'
               ArgumentTransformType = 'inline'
               }
         Exact = @{
               OriginalName = '--exact'
               OriginalPosition = '0'
               Position = '2147483647'
               ParameterType = 'switch'
               ApplyToExecutable = $False
               NoGap = $False
               ArgumentTransform = '$args'
               ArgumentTransformType = 'inline'
               }
         Source = @{
               OriginalName = '--source='
               OriginalPosition = '0'
               Position = '2147483647'
               ParameterType = 'string'
               ApplyToExecutable = $False
               NoGap = $True
               ArgumentTransform = '$args'
               ArgumentTransformType = 'inline'
               }
    }

    $__outputHandlers = @{
        Default = @{ StreamOutput = $False; Handler = { param ($output)
    $language = (Get-UICulture).Name

    $languageData = $(
        $hash = @{}

        $(try {
            # We have to trim the leading BOM for .NET's XML parser to correctly read Microsoft's own files - go figure
            ([xml](((Invoke-WebRequest -Uri "https://raw.githubusercontent.com/microsoft/winget-cli/v1.3.2691/Localization/Resources/$language/winget.resw" -ErrorAction Stop ).Content -replace "\uFEFF", ""))).root.data
        } catch {
            # Fall back to English if a locale file doesn't exist
            (
                ('SearchName','Name'),
                ('SearchID','Id'),
                ('SearchVersion','Version'),
                ('AvailableHeader','Available'),
                ('SearchSource','Source'),
                ('ShowVersion','Version'),
                ('GetManifestResultVersionNotFound','No version found matching:'),
                ('InstallerFailedWithCode','Installer failed with exit code:'),
                ('UninstallFailedWithCode','Uninstall failed with exit code:'),
                ('AvailableUpgrades','upgrades available.')
            ) | ForEach-Object {[pscustomobject]@{name = $_[0]; value = $_[1]}}
        }) | ForEach-Object {
            # Convert the array into a hashtable
            $hash[$_.name] = $_.value
        }

        $hash
    )

    $nameHeader = $output -Match "^$($languageData.SearchName)"

    if ($nameHeader) {

        $headerLine = $output.IndexOf(($nameHeader | Select-Object -First 1))

        if ($headerLine -ne -1) {
            $idIndex = $output[$headerLine].IndexOf(($languageData.SearchID))
            $versionIndex = $output[$headerLine].IndexOf(($languageData.SearchVersion))
            $availableIndex = $output[$headerLine].IndexOf(($languageData.AvailableHeader))
            $sourceIndex = $output[$headerLine].IndexOf(($languageData.SearchSource))

            # Stop gathering version data at the 'Available' column if it exists, if not continue on to the 'Source' column (if it exists)
            $versionEndIndex = $(
                if ($availableIndex -ne -1) {
                    $availableIndex
                } else {
                    $sourceIndex
                }
            )

            # Only attempt to parse output if it contains a 'version' column
            if ($versionIndex -ne -1) {
                # The -replace cleans up errant characters that come from WinGet's poor treatment of truncated columnar output
                ($output | Select-String -Pattern $languageData.AvailableUpgrades,'--include-unknown' -NotMatch) -replace '[^i\p{IsBasicLatin}]+',' ' | Select-Object -Skip ($headerLine+2) | ForEach-Object {
                    Remove-Variable -Name 'package' -ErrorAction SilentlyContinue

                    $package = [ordered]@{
                        ID = $_.SubString($idIndex,$versionIndex-$idIndex).Trim()
                    }

                    if ($package) {
                        # I'm so sorry, blame WinGet
                        # If neither the 'Available' or 'Source' column exist, gather version data to the end of the string
                        $package.Version = $(
                            if ($versionEndIndex -ne -1) {
                                $_.SubString($versionIndex,$versionEndIndex-$versionIndex)
                            } else {
                                $_.SubString($versionIndex)
                            }
                        ).Trim() -replace '[^\.\d]'

                        # Only attempt to add 'Available Version' data if the column exists
                        if ($availableIndex -ne -1) {
                            $package.Available = $(
                                if ($sourceIndex -ne -1) {
                                    $_.SubString($availableIndex,$sourceIndex-$availableIndex)
                                } else {
                                    $_.SubString($availableIndex)
                                }
                            ).Trim() -replace '[^\.\d]'
                        }

                        # If the 'Source' column was included in the output, include it in our output, too
                        if (($sourceIndex -ne -1) -And ($_.Length -ge $sourceIndex)) {
                            $package.Source = $_.SubString($sourceIndex).Trim() -split ' ' | Select-Object -Last 1
                        }

                        [pscustomobject]$package
                    }
                }
            }
        }
    }
 } }
    }
}

PROCESS {
    $__boundParameters = $PSBoundParameters
    $__defaultValueParameters = $PSCmdlet.MyInvocation.MyCommand.Parameters.Values.Where({$_.Attributes.Where({$_.TypeId.Name -eq "PSDefaultValueAttribute"})}).Name
    $__defaultValueParameters.Where({ !$__boundParameters["$_"] }).ForEach({$__boundParameters["$_"] = get-variable -value $_})
    $__commandArgs = @()
    $MyInvocation.MyCommand.Parameters.Values.Where({$_.SwitchParameter -and $_.Name -notmatch "Debug|Whatif|Confirm|Verbose" -and ! $__boundParameters[$_.Name]}).ForEach({$__boundParameters[$_.Name] = [switch]::new($false)})
    if ($__boundParameters["Debug"]){wait-debugger}
    $__commandArgs += 'search'
    $__commandArgs += '--accept-source-agreements'
    foreach ($paramName in $__boundParameters.Keys|
            Where-Object {!$__PARAMETERMAP[$_].ApplyToExecutable}|
            Sort-Object {$__PARAMETERMAP[$_].OriginalPosition}) {
        $value = $__boundParameters[$paramName]
        $param = $__PARAMETERMAP[$paramName]
        if ($param) {
            if ($value -is [switch]) {
                 if ($value.IsPresent) {
                     if ($param.OriginalName) { $__commandArgs += $param.OriginalName }
                 }
                 elseif ($param.DefaultMissingValue) { $__commandArgs += $param.DefaultMissingValue }
            }
            elseif ( $param.NoGap ) {
                $pFmt = "{0}{1}"
                if($value -match "\s") { $pFmt = "{0}""{1}""" }
                $__commandArgs += $pFmt -f $param.OriginalName, $value
            }
            else {
                if($param.OriginalName) { $__commandArgs += $param.OriginalName }
                if($param.ArgumentTransformType -eq 'inline') {
                   $transform = [scriptblock]::Create($param.ArgumentTransform)
                }
                else {
                   $transform = $param.ArgumentTransform
                }
                $__commandArgs += & $transform $value
            }
        }
    }
    $__commandArgs = $__commandArgs | Where-Object {$_ -ne $null}
    if ($__boundParameters["Debug"]){wait-debugger}
    if ( $__boundParameters["Verbose"]) {
         Write-Verbose -Verbose -Message "WinGet"
         $__commandArgs | Write-Verbose -Verbose
    }
    $__handlerInfo = $__outputHandlers[$PSCmdlet.ParameterSetName]
    if (! $__handlerInfo ) {
        $__handlerInfo = $__outputHandlers["Default"] # Guaranteed to be present
    }
    $__handler = $__handlerInfo.Handler
    if ( $PSCmdlet.ShouldProcess("WinGet $__commandArgs")) {
    # check for the application and throw if it cannot be found
        if ( -not (Get-Command -ErrorAction Ignore "WinGet")) {
          throw "Cannot find executable 'WinGet'"
        }
        if ( $__handlerInfo.StreamOutput ) {
            if ( $null -eq $__handler ) {
                & "WinGet" $__commandArgs
            }
            else {
                & "WinGet" $__commandArgs 2>&1| Push-CrescendoNativeError | & $__handler
            }
        }
        else {
            $result = & "WinGet" $__commandArgs 2>&1| Push-CrescendoNativeError
            & $__handler $result
        }
    }
  } # end PROCESS

<#


.DESCRIPTION
Find a list of available WinGet packages

.PARAMETER ID
Package ID


.PARAMETER Exact
Search by exact package name


.PARAMETER Source
Package Source



#>
}


function Update-WinGetPackage
{
[PowerShellCustomFunctionAttribute(RequiresElevation=$False)]
[CmdletBinding()]

param(
[Parameter(ValueFromPipelineByPropertyName=$true)]
[string]$ID,
[Parameter()]
[switch]$Exact,
[Parameter(ValueFromPipelineByPropertyName=$true)]
[string]$Source,
[Parameter()]
[switch]$All
    )

BEGIN {
    $__PARAMETERMAP = @{
         ID = @{
               OriginalName = '--id='
               OriginalPosition = '0'
               Position = '2147483647'
               ParameterType = 'string'
               ApplyToExecutable = $False
               NoGap = $True
               ArgumentTransform = '$args'
               ArgumentTransformType = 'inline'
               }
         Exact = @{
               OriginalName = '--exact'
               OriginalPosition = '0'
               Position = '2147483647'
               ParameterType = 'switch'
               ApplyToExecutable = $False
               NoGap = $False
               ArgumentTransform = '$args'
               ArgumentTransformType = 'inline'
               }
         Source = @{
               OriginalName = '--source='
               OriginalPosition = '0'
               Position = '2147483647'
               ParameterType = 'string'
               ApplyToExecutable = $False
               NoGap = $True
               ArgumentTransform = '$args'
               ArgumentTransformType = 'inline'
               }
         All = @{
               OriginalName = '--all'
               OriginalPosition = '0'
               Position = '2147483647'
               ParameterType = 'switch'
               ApplyToExecutable = $False
               NoGap = $False
               ArgumentTransform = '$args'
               ArgumentTransformType = 'inline'
               }
    }

    $__outputHandlers = @{
        Default = @{ StreamOutput = $False; Handler = { param ($output)
    $language = (Get-UICulture).Name

    $languageData = $(
        $hash = @{}

        $(try {
            # We have to trim the leading BOM for .NET's XML parser to correctly read Microsoft's own files - go figure
            ([xml](((Invoke-WebRequest -Uri "https://raw.githubusercontent.com/microsoft/winget-cli/v1.3.2691/Localization/Resources/$language/winget.resw" -ErrorAction Stop ).Content -replace "\uFEFF", ""))).root.data
        } catch {
            # Fall back to English if a locale file doesn't exist
            (
                ('SearchName','Name'),
                ('SearchID','Id'),
                ('SearchVersion','Version'),
                ('AvailableHeader','Available'),
                ('SearchSource','Source'),
                ('ShowVersion','Version'),
                ('GetManifestResultVersionNotFound','No version found matching:'),
                ('InstallerFailedWithCode','Installer failed with exit code:'),
                ('UninstallFailedWithCode','Uninstall failed with exit code:'),
                ('AvailableUpgrades','upgrades available.')
            ) | ForEach-Object {[pscustomobject]@{name = $_[0]; value = $_[1]}}
        }) | ForEach-Object {
            # Convert the array into a hashtable
            $hash[$_.name] = $_.value
        }

        $hash
    )

    if ($output) {
        if ($output -match $languageData.InstallerFailedWithCode) {
            # Only show output that matches or comes after the 'failed' keyword
            Write-Error ($output[$output.IndexOf($($output -match $languageData.InstallerFailedWithCode | Select-Object -First 1))..($output.Length-1)] -join "`r`n")
        } else {
            $output | ForEach-Object {
                if ($_ -match 'Found .+ \[(?<id>[\S]+)\] Version (?<version>[\S]+)' -and $Matches.id -and $Matches.version) {
                    [pscustomobject]@{
                        ID = $Matches.id
                        Version = $Matches.version
                    }
                }
            }
        }
    }
 } }
    }
}

PROCESS {
    $__boundParameters = $PSBoundParameters
    $__defaultValueParameters = $PSCmdlet.MyInvocation.MyCommand.Parameters.Values.Where({$_.Attributes.Where({$_.TypeId.Name -eq "PSDefaultValueAttribute"})}).Name
    $__defaultValueParameters.Where({ !$__boundParameters["$_"] }).ForEach({$__boundParameters["$_"] = get-variable -value $_})
    $__commandArgs = @()
    $MyInvocation.MyCommand.Parameters.Values.Where({$_.SwitchParameter -and $_.Name -notmatch "Debug|Whatif|Confirm|Verbose" -and ! $__boundParameters[$_.Name]}).ForEach({$__boundParameters[$_.Name] = [switch]::new($false)})
    if ($__boundParameters["Debug"]){wait-debugger}
    $__commandArgs += 'upgrade'
    $__commandArgs += '--accept-source-agreements'
    $__commandArgs += '--silent'
    foreach ($paramName in $__boundParameters.Keys|
            Where-Object {!$__PARAMETERMAP[$_].ApplyToExecutable}|
            Sort-Object {$__PARAMETERMAP[$_].OriginalPosition}) {
        $value = $__boundParameters[$paramName]
        $param = $__PARAMETERMAP[$paramName]
        if ($param) {
            if ($value -is [switch]) {
                 if ($value.IsPresent) {
                     if ($param.OriginalName) { $__commandArgs += $param.OriginalName }
                 }
                 elseif ($param.DefaultMissingValue) { $__commandArgs += $param.DefaultMissingValue }
            }
            elseif ( $param.NoGap ) {
                $pFmt = "{0}{1}"
                if($value -match "\s") { $pFmt = "{0}""{1}""" }
                $__commandArgs += $pFmt -f $param.OriginalName, $value
            }
            else {
                if($param.OriginalName) { $__commandArgs += $param.OriginalName }
                if($param.ArgumentTransformType -eq 'inline') {
                   $transform = [scriptblock]::Create($param.ArgumentTransform)
                }
                else {
                   $transform = $param.ArgumentTransform
                }
                $__commandArgs += & $transform $value
            }
        }
    }
    $__commandArgs = $__commandArgs | Where-Object {$_ -ne $null}
    if ($__boundParameters["Debug"]){wait-debugger}
    if ( $__boundParameters["Verbose"]) {
         Write-Verbose -Verbose -Message "WinGet"
         $__commandArgs | Write-Verbose -Verbose
    }
    $__handlerInfo = $__outputHandlers[$PSCmdlet.ParameterSetName]
    if (! $__handlerInfo ) {
        $__handlerInfo = $__outputHandlers["Default"] # Guaranteed to be present
    }
    $__handler = $__handlerInfo.Handler
    if ( $PSCmdlet.ShouldProcess("WinGet $__commandArgs")) {
    # check for the application and throw if it cannot be found
        if ( -not (Get-Command -ErrorAction Ignore "WinGet")) {
          throw "Cannot find executable 'WinGet'"
        }
        if ( $__handlerInfo.StreamOutput ) {
            if ( $null -eq $__handler ) {
                & "WinGet" $__commandArgs
            }
            else {
                & "WinGet" $__commandArgs 2>&1| Push-CrescendoNativeError | & $__handler
            }
        }
        else {
            $result = & "WinGet" $__commandArgs 2>&1| Push-CrescendoNativeError
            & $__handler $result
        }
    }
  } # end PROCESS

<#


.DESCRIPTION
Updates an installed package to the latest version

.PARAMETER ID
Package ID


.PARAMETER Exact
Search by exact package name


.PARAMETER Source
Package Source


.PARAMETER All
Upgrade all packages



#>
}


function Uninstall-WinGetPackage
{
[PowerShellCustomFunctionAttribute(RequiresElevation=$False)]
[CmdletBinding()]

param(
[Parameter(ValueFromPipelineByPropertyName=$true)]
[string]$ID,
[Parameter()]
[switch]$Exact,
[Parameter(ValueFromPipelineByPropertyName=$true)]
[string]$Source
    )

BEGIN {
    $__PARAMETERMAP = @{
         ID = @{
               OriginalName = '--id='
               OriginalPosition = '0'
               Position = '2147483647'
               ParameterType = 'string'
               ApplyToExecutable = $False
               NoGap = $True
               ArgumentTransform = '$args'
               ArgumentTransformType = 'inline'
               }
         Exact = @{
               OriginalName = '--exact'
               OriginalPosition = '0'
               Position = '2147483647'
               ParameterType = 'switch'
               ApplyToExecutable = $False
               NoGap = $False
               ArgumentTransform = '$args'
               ArgumentTransformType = 'inline'
               }
         Source = @{
               OriginalName = '--source='
               OriginalPosition = '0'
               Position = '2147483647'
               ParameterType = 'string'
               ApplyToExecutable = $False
               NoGap = $True
               ArgumentTransform = '$args'
               ArgumentTransformType = 'inline'
               }
    }

    $__outputHandlers = @{
        Default = @{ StreamOutput = $False; Handler = { param ($output)
    $language = (Get-UICulture).Name

    $languageData = $(
        $hash = @{}

        $(try {
            # We have to trim the leading BOM for .NET's XML parser to correctly read Microsoft's own files - go figure
            ([xml](((Invoke-WebRequest -Uri "https://raw.githubusercontent.com/microsoft/winget-cli/v1.3.2691/Localization/Resources/$language/winget.resw" -ErrorAction Stop ).Content -replace "\uFEFF", ""))).root.data
        } catch {
            # Fall back to English if a locale file doesn't exist
            (
                ('SearchName','Name'),
                ('SearchID','Id'),
                ('SearchVersion','Version'),
                ('AvailableHeader','Available'),
                ('SearchSource','Source'),
                ('ShowVersion','Version'),
                ('GetManifestResultVersionNotFound','No version found matching:'),
                ('InstallerFailedWithCode','Installer failed with exit code:'),
                ('UninstallFailedWithCode','Uninstall failed with exit code:'),
                ('AvailableUpgrades','upgrades available.')
            ) | ForEach-Object {[pscustomobject]@{name = $_[0]; value = $_[1]}}
        }) | ForEach-Object {
            # Convert the array into a hashtable
            $hash[$_.name] = $_.value
        }

        $hash
    )

    if ($output) {
        if ($output -match $languageData.UninstallFailedWithCode) {
            # Only show output that matches or comes after the 'failed' keyword
            Write-Error ($output[$output.IndexOf($($output -match $languageData.UninstallFailedWithCode | Select-Object -First 1))..($output.Length-1)] -join "`r`n")
        }
    }
 } }
    }
}

PROCESS {
    $__boundParameters = $PSBoundParameters
    $__defaultValueParameters = $PSCmdlet.MyInvocation.MyCommand.Parameters.Values.Where({$_.Attributes.Where({$_.TypeId.Name -eq "PSDefaultValueAttribute"})}).Name
    $__defaultValueParameters.Where({ !$__boundParameters["$_"] }).ForEach({$__boundParameters["$_"] = get-variable -value $_})
    $__commandArgs = @()
    $MyInvocation.MyCommand.Parameters.Values.Where({$_.SwitchParameter -and $_.Name -notmatch "Debug|Whatif|Confirm|Verbose" -and ! $__boundParameters[$_.Name]}).ForEach({$__boundParameters[$_.Name] = [switch]::new($false)})
    if ($__boundParameters["Debug"]){wait-debugger}
    $__commandArgs += 'uninstall'
    $__commandArgs += '--accept-source-agreements'
    $__commandArgs += '--silent'
    foreach ($paramName in $__boundParameters.Keys|
            Where-Object {!$__PARAMETERMAP[$_].ApplyToExecutable}|
            Sort-Object {$__PARAMETERMAP[$_].OriginalPosition}) {
        $value = $__boundParameters[$paramName]
        $param = $__PARAMETERMAP[$paramName]
        if ($param) {
            if ($value -is [switch]) {
                 if ($value.IsPresent) {
                     if ($param.OriginalName) { $__commandArgs += $param.OriginalName }
                 }
                 elseif ($param.DefaultMissingValue) { $__commandArgs += $param.DefaultMissingValue }
            }
            elseif ( $param.NoGap ) {
                $pFmt = "{0}{1}"
                if($value -match "\s") { $pFmt = "{0}""{1}""" }
                $__commandArgs += $pFmt -f $param.OriginalName, $value
            }
            else {
                if($param.OriginalName) { $__commandArgs += $param.OriginalName }
                if($param.ArgumentTransformType -eq 'inline') {
                   $transform = [scriptblock]::Create($param.ArgumentTransform)
                }
                else {
                   $transform = $param.ArgumentTransform
                }
                $__commandArgs += & $transform $value
            }
        }
    }
    $__commandArgs = $__commandArgs | Where-Object {$_ -ne $null}
    if ($__boundParameters["Debug"]){wait-debugger}
    if ( $__boundParameters["Verbose"]) {
         Write-Verbose -Verbose -Message "WinGet"
         $__commandArgs | Write-Verbose -Verbose
    }
    $__handlerInfo = $__outputHandlers[$PSCmdlet.ParameterSetName]
    if (! $__handlerInfo ) {
        $__handlerInfo = $__outputHandlers["Default"] # Guaranteed to be present
    }
    $__handler = $__handlerInfo.Handler
    if ( $PSCmdlet.ShouldProcess("WinGet $__commandArgs")) {
    # check for the application and throw if it cannot be found
        if ( -not (Get-Command -ErrorAction Ignore "WinGet")) {
          throw "Cannot find executable 'WinGet'"
        }
        if ( $__handlerInfo.StreamOutput ) {
            if ( $null -eq $__handler ) {
                & "WinGet" $__commandArgs
            }
            else {
                & "WinGet" $__commandArgs 2>&1| Push-CrescendoNativeError | & $__handler
            }
        }
        else {
            $result = & "WinGet" $__commandArgs 2>&1| Push-CrescendoNativeError
            & $__handler $result
        }
    }
  } # end PROCESS

<#


.DESCRIPTION
Uninstall an existing package with WinGet

.PARAMETER ID
Package ID


.PARAMETER Exact
Search by exact package name


.PARAMETER Source
Package Source



#>
}


function Get-WinGetPackageInfo
{
[PowerShellCustomFunctionAttribute(RequiresElevation=$False)]
[CmdletBinding(DefaultParameterSetName='Default')]

param(
[Parameter(Position=0,ValueFromPipelineByPropertyName=$true,Mandatory=$true,ParameterSetName='Default')]
[Parameter(Position=0,ValueFromPipelineByPropertyName=$true,Mandatory=$true,ParameterSetName='Versions')]
[string]$ID,
[Parameter(ParameterSetName='Default')]
[Parameter(ParameterSetName='Versions')]
[switch]$Exact,
[Parameter(ValueFromPipelineByPropertyName=$true,ParameterSetName='Default')]
[Parameter(ValueFromPipelineByPropertyName=$true,ParameterSetName='Versions')]
[string]$Version,
[Parameter(ValueFromPipelineByPropertyName=$true,ParameterSetName='Default')]
[Parameter(ValueFromPipelineByPropertyName=$true,ParameterSetName='Versions')]
[string]$Source,
[Parameter(ParameterSetName='Versions')]
[switch]$Versions
    )

BEGIN {
    $__PARAMETERMAP = @{
         ID = @{
               OriginalName = '--id='
               OriginalPosition = '0'
               Position = '0'
               ParameterType = 'string'
               ApplyToExecutable = $False
               NoGap = $True
               ArgumentTransform = '$args'
               ArgumentTransformType = 'inline'
               }
         Exact = @{
               OriginalName = '--exact'
               OriginalPosition = '0'
               Position = '2147483647'
               ParameterType = 'switch'
               ApplyToExecutable = $False
               NoGap = $False
               ArgumentTransform = '$args'
               ArgumentTransformType = 'inline'
               }
         Version = @{
               OriginalName = '--version='
               OriginalPosition = '0'
               Position = '2147483647'
               ParameterType = 'string'
               ApplyToExecutable = $False
               NoGap = $True
               ArgumentTransform = '$args'
               ArgumentTransformType = 'inline'
               }
         Source = @{
               OriginalName = '--source='
               OriginalPosition = '0'
               Position = '2147483647'
               ParameterType = 'string'
               ApplyToExecutable = $False
               NoGap = $True
               ArgumentTransform = '$args'
               ArgumentTransformType = 'inline'
               }
         Versions = @{
               OriginalName = '--versions'
               OriginalPosition = '0'
               Position = '2147483647'
               ParameterType = 'switch'
               ApplyToExecutable = $False
               NoGap = $False
               ArgumentTransform = '$args'
               ArgumentTransformType = 'inline'
               }
    }

    $__outputHandlers = @{
        Default = @{ StreamOutput = $False; Handler = { 
                            param ( $output )

                            $packageInfo = @{}

                            $output | Select-String -AllMatches -Pattern '^\s*([\w\s]+):\s(.+)$' | ForEach-Object -MemberName Matches | ForEach-Object{
                                $match = ($_.Groups | Select-Object -Skip 1).Value
                                $packageInfo.add($match[0],$match[1])
                            }

                            $packageInfo
                         } }
        Versions = @{ StreamOutput = $False; Handler = { param ($output)
    $language = (Get-UICulture).Name

    $languageData = $(
        $hash = @{}

        $(try {
            # We have to trim the leading BOM for .NET's XML parser to correctly read Microsoft's own files - go figure
            ([xml](((Invoke-WebRequest -Uri "https://raw.githubusercontent.com/microsoft/winget-cli/v1.3.2691/Localization/Resources/$language/winget.resw" -ErrorAction Stop ).Content -replace "\uFEFF", ""))).root.data
        } catch {
            # Fall back to English if a locale file doesn't exist
            (
                ('SearchName','Name'),
                ('SearchID','Id'),
                ('SearchVersion','Version'),
                ('AvailableHeader','Available'),
                ('SearchSource','Source'),
                ('ShowVersion','Version'),
                ('GetManifestResultVersionNotFound','No version found matching:'),
                ('InstallerFailedWithCode','Installer failed with exit code:'),
                ('UninstallFailedWithCode','Uninstall failed with exit code:'),
                ('AvailableUpgrades','upgrades available.')
            ) | ForEach-Object {[pscustomobject]@{name = $_[0]; value = $_[1]}}
        }) | ForEach-Object {
            # Convert the array into a hashtable
            $hash[$_.name] = $_.value
        }

        $hash
    )

    if ($output) {
        if ($output | Select-String -Pattern $languageData.GetManifestResultVersionNotFound) {
            # Only show output that matches or comes after the 'failed' keyword
            Write-Error ($output[$output.IndexOf($($output | Select-String -Pattern $languageData.GetManifestResultVersionNotFound | Select-Object -First 1))..($output.Length-1)] -join "`r`n")
        } else {
            $versionHeader = $output -Match "^$($languageData.ShowVersion)"

            if ($versionHeader) {

                $headerLine = $output.IndexOf(($versionHeader | Select-Object -First 1))

                if ($headerLine -ne -1) {
                    $output | Select-Object -Skip ($headerLine+2)
                }
            }
        }
    }
 } }
    }
}

PROCESS {
    $__boundParameters = $PSBoundParameters
    $__defaultValueParameters = $PSCmdlet.MyInvocation.MyCommand.Parameters.Values.Where({$_.Attributes.Where({$_.TypeId.Name -eq "PSDefaultValueAttribute"})}).Name
    $__defaultValueParameters.Where({ !$__boundParameters["$_"] }).ForEach({$__boundParameters["$_"] = get-variable -value $_})
    $__commandArgs = @()
    $MyInvocation.MyCommand.Parameters.Values.Where({$_.SwitchParameter -and $_.Name -notmatch "Debug|Whatif|Confirm|Verbose" -and ! $__boundParameters[$_.Name]}).ForEach({$__boundParameters[$_.Name] = [switch]::new($false)})
    if ($__boundParameters["Debug"]){wait-debugger}
    $__commandArgs += 'show'
    $__commandArgs += '--accept-source-agreements'
    foreach ($paramName in $__boundParameters.Keys|
            Where-Object {!$__PARAMETERMAP[$_].ApplyToExecutable}|
            Sort-Object {$__PARAMETERMAP[$_].OriginalPosition}) {
        $value = $__boundParameters[$paramName]
        $param = $__PARAMETERMAP[$paramName]
        if ($param) {
            if ($value -is [switch]) {
                 if ($value.IsPresent) {
                     if ($param.OriginalName) { $__commandArgs += $param.OriginalName }
                 }
                 elseif ($param.DefaultMissingValue) { $__commandArgs += $param.DefaultMissingValue }
            }
            elseif ( $param.NoGap ) {
                $pFmt = "{0}{1}"
                if($value -match "\s") { $pFmt = "{0}""{1}""" }
                $__commandArgs += $pFmt -f $param.OriginalName, $value
            }
            else {
                if($param.OriginalName) { $__commandArgs += $param.OriginalName }
                if($param.ArgumentTransformType -eq 'inline') {
                   $transform = [scriptblock]::Create($param.ArgumentTransform)
                }
                else {
                   $transform = $param.ArgumentTransform
                }
                $__commandArgs += & $transform $value
            }
        }
    }
    $__commandArgs = $__commandArgs | Where-Object {$_ -ne $null}
    if ($__boundParameters["Debug"]){wait-debugger}
    if ( $__boundParameters["Verbose"]) {
         Write-Verbose -Verbose -Message "WinGet"
         $__commandArgs | Write-Verbose -Verbose
    }
    $__handlerInfo = $__outputHandlers[$PSCmdlet.ParameterSetName]
    if (! $__handlerInfo ) {
        $__handlerInfo = $__outputHandlers["Default"] # Guaranteed to be present
    }
    $__handler = $__handlerInfo.Handler
    if ( $PSCmdlet.ShouldProcess("WinGet $__commandArgs")) {
    # check for the application and throw if it cannot be found
        if ( -not (Get-Command -ErrorAction Ignore "WinGet")) {
          throw "Cannot find executable 'WinGet'"
        }
        if ( $__handlerInfo.StreamOutput ) {
            if ( $null -eq $__handler ) {
                & "WinGet" $__commandArgs
            }
            else {
                & "WinGet" $__commandArgs 2>&1| Push-CrescendoNativeError | & $__handler
            }
        }
        else {
            $result = & "WinGet" $__commandArgs 2>&1| Push-CrescendoNativeError
            & $__handler $result
        }
    }
  } # end PROCESS

<#


.DESCRIPTION
Shows information on a specific WinGet package

.PARAMETER ID
Package ID


.PARAMETER Exact
Search by exact package name


.PARAMETER Version
Package Version


.PARAMETER Source
Package Source


.PARAMETER Versions
Show available versions of the package



#>
}


function Get-WinGetPackageUpdate
{
[PowerShellCustomFunctionAttribute(RequiresElevation=$False)]
[CmdletBinding()]

param(    )

BEGIN {
    $__PARAMETERMAP = @{}
    $__outputHandlers = @{
        Default = @{ StreamOutput = $False; Handler = { param ($output)
    $language = (Get-UICulture).Name

    $languageData = $(
        $hash = @{}

        $(try {
            # We have to trim the leading BOM for .NET's XML parser to correctly read Microsoft's own files - go figure
            ([xml](((Invoke-WebRequest -Uri "https://raw.githubusercontent.com/microsoft/winget-cli/v1.3.2691/Localization/Resources/$language/winget.resw" -ErrorAction Stop ).Content -replace "\uFEFF", ""))).root.data
        } catch {
            # Fall back to English if a locale file doesn't exist
            (
                ('SearchName','Name'),
                ('SearchID','Id'),
                ('SearchVersion','Version'),
                ('AvailableHeader','Available'),
                ('SearchSource','Source'),
                ('ShowVersion','Version'),
                ('GetManifestResultVersionNotFound','No version found matching:'),
                ('InstallerFailedWithCode','Installer failed with exit code:'),
                ('UninstallFailedWithCode','Uninstall failed with exit code:'),
                ('AvailableUpgrades','upgrades available.')
            ) | ForEach-Object {[pscustomobject]@{name = $_[0]; value = $_[1]}}
        }) | ForEach-Object {
            # Convert the array into a hashtable
            $hash[$_.name] = $_.value
        }

        $hash
    )

    $nameHeader = $output -Match "^$($languageData.SearchName)"

    if ($nameHeader) {

        $headerLine = $output.IndexOf(($nameHeader | Select-Object -First 1))

        if ($headerLine -ne -1) {
            $idIndex = $output[$headerLine].IndexOf(($languageData.SearchID))
            $versionIndex = $output[$headerLine].IndexOf(($languageData.SearchVersion))
            $availableIndex = $output[$headerLine].IndexOf(($languageData.AvailableHeader))
            $sourceIndex = $output[$headerLine].IndexOf(($languageData.SearchSource))

            # Stop gathering version data at the 'Available' column if it exists, if not continue on to the 'Source' column (if it exists)
            $versionEndIndex = $(
                if ($availableIndex -ne -1) {
                    $availableIndex
                } else {
                    $sourceIndex
                }
            )

            # Only attempt to parse output if it contains a 'version' column
            if ($versionIndex -ne -1) {
                # The -replace cleans up errant characters that come from WinGet's poor treatment of truncated columnar output
                ($output | Select-String -Pattern $languageData.AvailableUpgrades,'--include-unknown' -NotMatch) -replace '[^i\p{IsBasicLatin}]+',' ' | Select-Object -Skip ($headerLine+2) | ForEach-Object {
                    Remove-Variable -Name 'package' -ErrorAction SilentlyContinue

                    $package = [ordered]@{
                        ID = $_.SubString($idIndex,$versionIndex-$idIndex).Trim()
                    }

                    if ($package) {
                        # I'm so sorry, blame WinGet
                        # If neither the 'Available' or 'Source' column exist, gather version data to the end of the string
                        $package.Version = $(
                            if ($versionEndIndex -ne -1) {
                                $_.SubString($versionIndex,$versionEndIndex-$versionIndex)
                            } else {
                                $_.SubString($versionIndex)
                            }
                        ).Trim() -replace '[^\.\d]'

                        # Only attempt to add 'Available Version' data if the column exists
                        if ($availableIndex -ne -1) {
                            $package.Available = $(
                                if ($sourceIndex -ne -1) {
                                    $_.SubString($availableIndex,$sourceIndex-$availableIndex)
                                } else {
                                    $_.SubString($availableIndex)
                                }
                            ).Trim() -replace '[^\.\d]'
                        }

                        # If the 'Source' column was included in the output, include it in our output, too
                        if (($sourceIndex -ne -1) -And ($_.Length -ge $sourceIndex)) {
                            $package.Source = $_.SubString($sourceIndex).Trim() -split ' ' | Select-Object -Last 1
                        }

                        [pscustomobject]$package
                    }
                }
            }
        }
    }
 } }
    }
}

PROCESS {
    $__boundParameters = $PSBoundParameters
    $__defaultValueParameters = $PSCmdlet.MyInvocation.MyCommand.Parameters.Values.Where({$_.Attributes.Where({$_.TypeId.Name -eq "PSDefaultValueAttribute"})}).Name
    $__defaultValueParameters.Where({ !$__boundParameters["$_"] }).ForEach({$__boundParameters["$_"] = get-variable -value $_})
    $__commandArgs = @()
    $MyInvocation.MyCommand.Parameters.Values.Where({$_.SwitchParameter -and $_.Name -notmatch "Debug|Whatif|Confirm|Verbose" -and ! $__boundParameters[$_.Name]}).ForEach({$__boundParameters[$_.Name] = [switch]::new($false)})
    if ($__boundParameters["Debug"]){wait-debugger}
    $__commandArgs += 'upgrade'
    foreach ($paramName in $__boundParameters.Keys|
            Where-Object {!$__PARAMETERMAP[$_].ApplyToExecutable}|
            Sort-Object {$__PARAMETERMAP[$_].OriginalPosition}) {
        $value = $__boundParameters[$paramName]
        $param = $__PARAMETERMAP[$paramName]
        if ($param) {
            if ($value -is [switch]) {
                 if ($value.IsPresent) {
                     if ($param.OriginalName) { $__commandArgs += $param.OriginalName }
                 }
                 elseif ($param.DefaultMissingValue) { $__commandArgs += $param.DefaultMissingValue }
            }
            elseif ( $param.NoGap ) {
                $pFmt = "{0}{1}"
                if($value -match "\s") { $pFmt = "{0}""{1}""" }
                $__commandArgs += $pFmt -f $param.OriginalName, $value
            }
            else {
                if($param.OriginalName) { $__commandArgs += $param.OriginalName }
                if($param.ArgumentTransformType -eq 'inline') {
                   $transform = [scriptblock]::Create($param.ArgumentTransform)
                }
                else {
                   $transform = $param.ArgumentTransform
                }
                $__commandArgs += & $transform $value
            }
        }
    }
    $__commandArgs = $__commandArgs | Where-Object {$_ -ne $null}
    if ($__boundParameters["Debug"]){wait-debugger}
    if ( $__boundParameters["Verbose"]) {
         Write-Verbose -Verbose -Message "WinGet"
         $__commandArgs | Write-Verbose -Verbose
    }
    $__handlerInfo = $__outputHandlers[$PSCmdlet.ParameterSetName]
    if (! $__handlerInfo ) {
        $__handlerInfo = $__outputHandlers["Default"] # Guaranteed to be present
    }
    $__handler = $__handlerInfo.Handler
    if ( $PSCmdlet.ShouldProcess("WinGet $__commandArgs")) {
    # check for the application and throw if it cannot be found
        if ( -not (Get-Command -ErrorAction Ignore "WinGet")) {
          throw "Cannot find executable 'WinGet'"
        }
        if ( $__handlerInfo.StreamOutput ) {
            if ( $null -eq $__handler ) {
                & "WinGet" $__commandArgs
            }
            else {
                & "WinGet" $__commandArgs 2>&1| Push-CrescendoNativeError | & $__handler
            }
        }
        else {
            $result = & "WinGet" $__commandArgs 2>&1| Push-CrescendoNativeError
            & $__handler $result
        }
    }
  } # end PROCESS

<#


.DESCRIPTION
Get a list of installed WinGet packages

#>
}


