# Native diagnostics. Definitions are compared in memory; only sanitized changes
# and explicitly selected non-sensitive scalar values reach the event file.
function Write-DotsTraceRecord {
    param($Event, $Name, $Kind, $Status)
    if (-not $env:DOTS_DEBUG_EVENTS) { return }
    if ($global:_DotsTraceCount -ge 10000 -or $global:_DotsTraceBytes -ge 8000000) {
        if (-not $global:_DotsTraceTruncated) {
            $global:_DotsTraceTruncated=$true
            $limit=@{event='coverage'; time=([DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()/1000.0); name='Trace limit reached'; kind='phase'; status=''; pid=$PID}
            [IO.File]::AppendAllText($env:DOTS_DEBUG_EVENTS,(($limit | ConvertTo-Json -Compress)+"`n"),[Text.UTF8Encoding]::new($false))
        }
        return
    }
    $global:_DotsTraceCount++
    $row = @{event=$Event; time=([DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()/1000.0); name=$Name; kind=$Kind; status=$Status; pid=$PID}
    $text = ($row | ConvertTo-Json -Compress -Depth 5) + "`n"
    if ($global:_DotsTraceBytes + [Text.Encoding]::UTF8.GetByteCount($text) -gt 8000000) { $global:_DotsTraceBytes=8000000; return }
    $global:_DotsTraceBytes += [Text.Encoding]::UTF8.GetByteCount($text)
    [IO.File]::AppendAllText($env:DOTS_DEBUG_EVENTS, $text, [Text.UTF8Encoding]::new($false))
}
function Get-DotsTraceState {
    $result = @{}
    $categories = $env:DOTS_DEBUG_CHANGES -split ','
    if ('variables' -in $categories) {
        foreach ($variable in Get-Variable -Scope Global) {
            if ($variable.Name -match '^(?:_DotsTrace|_DotsPath|_DotsDebug|PS|MyInvocation|ExecutionContext|Error|LASTEXITCODE|\?)') { continue }
            $value = $variable.Value
            if ($null -eq $value -or $value -is [string] -or $value -is [ValueType]) {
                $result['variables:'+$variable.Name] = @{data=[string]$value; type=[string]$variable.Options}
            }
        }
        foreach ($variable in Get-ChildItem Env:) {
            if ($variable.Name -notmatch '^DOTS_DEBUG') { $result['variables:env:'+$variable.Name] = @{data=$variable.Value; type='exported'} }
        }
    }
    if ('functions' -in $categories) {
        foreach ($function in Get-ChildItem Function:) {
            if ($function.Name -notmatch 'DotsTrace|DotsPath') { $result['functions:'+$function.Name] = @{data=$function.Definition; type='function'} }
        }
    }
    if ('aliases' -in $categories) {
        foreach ($alias in Get-Alias) { $result['aliases:'+$alias.Name] = @{data=$alias.Definition; type='alias'} }
    }
    if ('options' -in $categories) {
        foreach ($name in @('ErrorActionPreference','WarningPreference','VerbosePreference','DebugPreference','InformationPreference','ProgressPreference','ConfirmPreference','WhatIfPreference')) {
            $result['options:'+$name] = @{data=[string](Get-Variable -Name $name -ValueOnly); type='preference'}
        }
    }
    return $result
}
function Invoke-DotsTraceSnapshot {
    param([string]$File='unknown', [int]$Line=0)
    if ($global:_DotsTraceBusy) { return }
    $global:_DotsTraceBusy = $true
    try {
        $current = Get-DotsTraceState
        Write-DotsTraceRecord state-begin $File ([string]$Line) 'visible-global-scope'
        if ('path' -in ($env:DOTS_DEBUG_CHANGES -split ',')) { Write-DotsTraceRecord state-path PATH path $env:PATH }
        Write-DotsTraceRecord state-end '' '' ''
        if ($null -ne $global:_DotsTracePrevious) {
            $keys = @($current.Keys) + @($global:_DotsTracePrevious.Keys) | Select-Object -Unique
            foreach ($key in $keys) {
                $old = $global:_DotsTracePrevious[$key]; $new = $current[$key]
                if ($null -ne $old -and $null -ne $new -and $old.data -ceq $new.data -and $old.type -eq $new.type) { continue }
                $category,$name = $key -split ':',2
                $action = if ($null -eq $old) {'set'} elseif ($null -eq $new) {'unset'} else {'changed'}
                if ($category -in @('functions','aliases')) { $action = if ($null -eq $old) {'created'} elseif ($null -eq $new) {'removed'} else {'redefined'} }
                $change = @{category=$category; name=$name; action=$action; file=$global:_DotsTraceFile; line=$global:_DotsTraceLine; scope='visible-global-scope'; precision='observation-interval'}
                $change.observed_at_file=$File; $change.observed_at_line=$Line
                if ($name.StartsWith('env:')) { $change.name=$name.Substring(4); $change.scope='environment' }
                if ($null -ne $old -and $null -ne $new -and $old.type -ne $new.type) {
                    $change.attributes_changed=$true; $change.before_attributes=$old.type; $change.after_attributes=$new.type
                }
                if ($category -eq 'options') {
                    $safeOptions=@('Stop','Continue','SilentlyContinue','Inquire','Ignore','Suspend','Break','True','False','None','Low','Medium','High')
                    $change.before=if ($old.data -in $safeOptions) {$old.data} else {'unavailable'}
                    $change.after=if ($new.data -in $safeOptions) {$new.data} else {'unavailable'}
                }
                if ($category -eq 'variables' -and ($name -replace '^env:','') -in ($env:DOTS_DEBUG_VALUES -split ',')) {
                    $privateName=[regex]::Escape(($name -replace '^env:',''))
                    if ($name -match 'TOKEN|PASSWORD|PASSWD|SECRET|CREDENTIAL|PRIVATE_KEY|API_KEY' -or $env:DOTS_ENV_HOOKS -match "(?:^|;)$privateName`:[^;:]+:1:" -or $global:_DotsTraceFile -match '[/\\](?:secrets|private|\.private)[/\\.]') { $change.redacted=$true }
                    else {
                        if ($null -ne $old) { $change.before=$old.data.Substring(0,[Math]::Min(4096,$old.data.Length)) }
                        if ($null -ne $new) { $change.after=$new.data.Substring(0,[Math]::Min(4096,$new.data.Length)) }
                    }
                }
                Write-DotsTraceRecord change $name $category ($change | ConvertTo-Json -Compress)
            }
        }
        $global:_DotsTracePrevious=$current; $global:_DotsTraceFile=$File; $global:_DotsTraceLine=$Line
    } finally { $global:_DotsTraceBusy=$false }
}
function Register-DotsTraceFile {
    param([string]$File)
    if ($env:DOTS_DEBUG_DETAIL -ne 'deep' -or $global:_DotsTraceConflict -or -not $File.EndsWith('.ps1') -or -not (Test-Path -LiteralPath $File -PathType Leaf)) { return }
    if ($global:_DotsTraceFiles.ContainsKey($File)) { return }
    $global:_DotsTraceFiles[$File]=$true
    $tokens=$null; $errors=$null
    $ast=[Management.Automation.Language.Parser]::ParseFile($File,[ref]$tokens,[ref]$errors)
    $lines=@($ast.FindAll({param($node) $node -is [Management.Automation.Language.StatementAst]},$true) | ForEach-Object {$_.Extent.StartLineNumber} | Select-Object -Unique)
    if ($lines.Count) {
        $global:_DotsTraceBreakpoints += @(Set-PSBreakpoint -Script $File -Line $lines -Action {
            if ($null -ne $PSDebugContext) { Invoke-DotsTraceSnapshot $PSDebugContext.InvocationInfo.ScriptName $PSDebugContext.InvocationInfo.ScriptLineNumber }
        })
    }
}
function Initialize-DotsTrace {
    if ($global:_DotsTraceInitialized -or -not $env:DOTS_DEBUG_EVENTS -or $env:DOTS_DEBUG_DETAIL -eq 'files') { return }
    $global:_DotsTraceInitialized=$true; $global:_DotsTraceFiles=@{}; $global:_DotsTraceBreakpoints=@()
    $global:_DotsTraceCount=0; $global:_DotsTraceBytes=0
    if ($env:DOTS_DEBUG_DETAIL -eq 'deep' -and @(Get-PSBreakpoint).Count) {
        $global:_DotsTraceConflict=$true
        Write-DotsTraceRecord coverage 'Deep trace unavailable: existing PowerShell breakpoints' phase ''
    }
    Invoke-DotsTraceSnapshot 'inherited' 0
}

function Write-DotsPathRecord {
    param($Event, $File='', $Line=0, $PathValue='')
    $row=@{event=$Event; time=([DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()/1000.0); file=$File; line=$Line; path=$PathValue; pid=$PID}
    [IO.File]::AppendAllText($env:DOTS_DEBUG_SESSION, (($row | ConvertTo-Json -Compress)+"`n"), [Text.UTF8Encoding]::new($false))
}
function Update-DotsPathRecording {
    if ($global:_DotsPathBusy -or -not $global:_DotsPathActive) { return }
    $global:_DotsPathBusy=$true
    try {
        if ($env:PATH -cne $global:_DotsPathPrevious) {
            if ($global:_DotsPathCount -ge 10000 -or (Get-Item -LiteralPath $env:DOTS_DEBUG_SESSION).Length -gt 8000000) {
                Write-DotsPathRecord limit; $global:_DotsPathActive=$false; return
            }
            $global:_DotsPathCount++
            Write-DotsPathRecord path $global:_DotsPathFile $global:_DotsPathLine $env:PATH
            $global:_DotsPathPrevious=$env:PATH
        }
        $frame=Get-PSCallStack | Where-Object {$_.FunctionName -notmatch 'DotsPath|ScriptBlock'} | Select-Object -First 1
        $global:_DotsPathFile=if ($frame.ScriptName) {$frame.ScriptName} else {'interactive'}
        $global:_DotsPathLine=$frame.ScriptLineNumber
    } finally { $global:_DotsPathBusy=$false }
}
function Start-DotsPathRecording {
    if ($global:_DotsPathActive) { return }
    if (@(Get-PSBreakpoint).Count) { throw 'Existing PowerShell breakpoints prevent PATH recording' }
    if (-not $global:_DotsPathDirectory) {
        $global:_DotsPathDirectory=Join-Path ([IO.Path]::GetTempPath()) ('dots-path.'+[Guid]::NewGuid().ToString('N'))
        [void][IO.Directory]::CreateDirectory($global:_DotsPathDirectory)
        $env:DOTS_DEBUG_SESSION=Join-Path $global:_DotsPathDirectory 'events.jsonl'
        [IO.File]::WriteAllText($env:DOTS_DEBUG_SESSION,'')
        Register-EngineEvent -SourceIdentifier PowerShell.Exiting -MessageData $global:_DotsPathDirectory -Action {
            $directory=$event.MessageData
            [IO.File]::Delete((Join-Path $directory 'events.jsonl'))
            [IO.Directory]::Delete($directory)
        } | Out-Null
    }
    $global:_DotsPathBusy=$true; $global:_DotsPathPrevious=$env:PATH; $global:_DotsPathFile='inherited'; $global:_DotsPathLine=0; $global:_DotsPathCount=0
    Write-DotsPathRecord baseline inherited 0 $env:PATH
    $global:_DotsPathBreakpoint=Set-PSBreakpoint -Command '*' -Action { Update-DotsPathRecording }
    $global:_DotsPathOpen=$true; $global:_DotsPathActive=$true; $global:_DotsPathBusy=$false
}
function Stop-DotsPathRecording {
    if (-not $global:_DotsPathOpen) { return }
    Update-DotsPathRecording
    $global:_DotsPathActive=$false
    if ($global:_DotsPathBreakpoint) { Remove-PSBreakpoint -Breakpoint $global:_DotsPathBreakpoint; $global:_DotsPathBreakpoint=$null }
    Write-DotsPathRecord stop
    $global:_DotsPathOpen=$false
}
