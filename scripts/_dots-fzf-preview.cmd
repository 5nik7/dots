@echo off
setlocal DisableDelayedExpansion
rem FZF passes only its selection file path to cmd.exe, never candidate text.
if not "%~1"=="--selection" exit /b 2
set "PYTHONUTF8=1"
set "PYTHON_MANAGER_AUTOMATIC_INSTALL=false"
set "PYLAUNCHER_ALLOW_INSTALL="
set "PYLAUNCHER_ALWAYS_INSTALL="
for %%P in (py.exe python3.exe python.exe) do (
  for /f "delims=" %%I in ('where $PATH:%%P 2^>nul ^| findstr /v /i /l /c:"\Microsoft\WindowsApps"') do (
    if /i "%%P"=="py.exe" (
      "%%I" -3 -B "%~dp0..\lib\dots\fzf_preview.py" --selection "%~2"
    ) else (
      "%%I" -B "%~dp0..\lib\dots\fzf_preview.py" --selection "%~2"
    )
    exit /b
  )
)
rem The fallback only reads bounded UTF-8 data and passes the literal name via the environment.
set "DOTS_FZF_SELECTION=%~2"
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -NonInteractive -Command ^
  "$ErrorActionPreference = 'Stop';" ^
  "[Console]::OutputEncoding = [Text.UTF8Encoding]::new($false);" ^
  "function Read-Part($path, $limit) {" ^
  "  $stream = [IO.File]::OpenRead($path);" ^
  "  try {" ^
  "    $buffer = New-Object byte[] $limit;" ^
  "    $count = $stream.Read($buffer, 0, $limit);" ^
  "    [Text.Encoding]::UTF8.GetString($buffer, 0, $count)" ^
  "  } finally { $stream.Dispose() }" ^
  "};" ^
  "$entry = Get-Item -LiteralPath $env:DOTS_FZF_SELECTION;" ^
  "if ($entry -isnot [IO.FileInfo] -or $entry.Length -gt 65536) { exit 1 };" ^
  "$name = (Read-Part $entry.FullName 65536).TrimEnd([char]10, [char]0);" ^
  "$item = Get-Item -LiteralPath $name -Force -ErrorAction SilentlyContinue;" ^
  "$value = if ($item -is [IO.DirectoryInfo]) {" ^
  "  (Get-ChildItem -LiteralPath $item.FullName -Name -Force | Select-Object -First 200) -join [char]10" ^
  "} elseif ($item -is [IO.FileInfo]) {" ^
  "  $data = Read-Part $item.FullName 131072;" ^
  "  if ($data.Contains([char]0)) { $item.Name } else { $data }" ^
  "} else { $name };" ^
  "[Console]::WriteLine([regex]::Replace([string]$value, '(?![\t\n])\p{Cc}', ''))"
exit /b
