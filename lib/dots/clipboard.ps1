# Native transport only: provider selection and command semantics live in Python.
function Invoke-DotsClipboard {
  param(
    [string] $Root,
    [string] $Command,
    [string[]] $CliArguments,
    [string[]] $PipelineInput,
    [bool] $PipelineUsed
  )
  $process = $null
  try {
    $python = Get-Command py, python3, python -CommandType Application -All -ErrorAction SilentlyContinue |
      Where-Object { $_.Source -notlike '*\Microsoft\WindowsApps\*' -and
        ([IO.Path]::GetExtension($_.Source) -eq '.exe' -or $env:OS -ne 'Windows_NT') } |
      Select-Object -First 1
    if (-not $python) { throw 'Python is unavailable' }
    $text = ''
    if ($Command -eq 'cpy' -and ($CliArguments.Count -eq 0 -or
        ($CliArguments.Count -eq 1 -and $CliArguments[0] -eq '--'))) {
      if ($PipelineUsed) { $text = $PipelineInput -join [Environment]::NewLine }
      else { $text = [Console]::In.ReadToEnd() }
    }
    $request = ConvertTo-Json -Compress -InputObject @{
      command = $Command; arguments = @($CliArguments); input = $text
    }
    $utf8 = New-Object Text.UTF8Encoding($false)
    $controller = Join-Path $Root 'lib/dots/clipboard.py'
    # Only the fixed controller path crosses native argv; text stays on stdin.
    $quoted = '"' + [regex]::Replace(
      [regex]::Replace($controller, '(\\*)"', '$1$1\"'), '(\\+)$', '$1$1') + '"'
    $start = New-Object Diagnostics.ProcessStartInfo
    $start.FileName = $python.Source
    $prefix = if ($python.Name -in @('py', 'py.exe')) { '-3 ' } else { '' }
    $start.Arguments = $prefix + '-B ' + $quoted + ' --powershell'
    $start.UseShellExecute = $false
    $start.CreateNoWindow = $true
    $start.RedirectStandardInput = $true
    $start.RedirectStandardOutput = $true
    $start.RedirectStandardError = $true
    $start.StandardOutputEncoding = $utf8
    $start.StandardErrorEncoding = $utf8
    $start.EnvironmentVariables['PYTHONIOENCODING'] = 'utf-8'
    $start.EnvironmentVariables['PYTHONUTF8'] = '1'
    $start.EnvironmentVariables['PYTHON_MANAGER_AUTOMATIC_INSTALL'] = 'false'
    $start.EnvironmentVariables.Remove('PYLAUNCHER_ALLOW_INSTALL')
    $start.EnvironmentVariables.Remove('PYLAUNCHER_ALWAYS_INSTALL')
    $process = New-Object Diagnostics.Process
    $process.StartInfo = $start
    [void] $process.Start()
    $stdout = $process.StandardOutput.ReadToEndAsync()
    $stderr = $process.StandardError.ReadToEndAsync()
    $bytes = $utf8.GetBytes($request)
    $process.StandardInput.BaseStream.Write($bytes, 0, $bytes.Length)
    $process.StandardInput.Close()
    $process.WaitForExit()
    $output = $stdout.GetAwaiter().GetResult()
    $diagnostic = $stderr.GetAwaiter().GetResult()
    $global:LASTEXITCODE = $process.ExitCode
    if ($diagnostic) { [Console]::Error.Write($diagnostic) }
    if ($output.Length -gt 0 -or ($Command -eq 'pst' -and $process.ExitCode -eq 0)) {
      # One string preserves embedded/trailing newlines in the object pipeline.
      Write-Output -InputObject $output
    }
  } catch {
    [Console]::Error.WriteLine($Command + ': clipboard adapter failed; check Python and the command paths')
    $global:LASTEXITCODE = 1
  } finally {
    if ($null -ne $process) { $process.Dispose() }
  }
}
