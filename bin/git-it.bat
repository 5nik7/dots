@echo off
setlocal

set "PS1=%~dp0git-it.ps1"

:: Prefer pwsh if available, fall back to Windows PowerShell
where pwsh >nul 2>nul
if %errorlevel%==0 (
  pwsh -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%PS1%" %*
  exit /b %errorlevel%
)

powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%PS1%" %*
exit /b %errorlevel%
