$timeout = 1000
$pingResult = Get-CimInstance -ClassName Win32_PingStatus -Filter "Address = 'github.com' AND Timeout = $timeout" -Property StatusCode 2>$null
if ($pingResult.StatusCode -eq 0) {
  $canConnectToGitHub = $true
}
else {
  $canConnectToGitHub = $false
}

function Update-PowerShell {
  if (-not $global:canConnectToGitHub) {
    Write-Host "󱎘 Skipping PowerShell update or installation check due to GitHub.com not responding within 1 second." -ForegroundColor Yellow
    return
  }
  try {
    $isInstalled = $null -ne (Get-Command pwsh -ErrorAction SilentlyContinue)
    $updateNeeded = $false
    if ($isInstalled) {
      $currentVersion = $PSVersionTable.PSVersion.ToString()
    }
    else {
      $currentVersion = "0.0"
    }
    $gitHubApiUrl = "https://api.github.com/repos/PowerShell/PowerShell/releases/latest"
    $latestReleaseInfo = Invoke-RestMethod -Uri $gitHubApiUrl
    $latestVersion = $latestReleaseInfo.tag_name.Trim('v')
    if ($currentVersion -lt $latestVersion) {
      $updateNeeded = $true
    }
    if ($updateNeeded -and $isInstalled) {
      Write-Host "Updating PowerShell..." -ForegroundColor Yellow
      winget upgrade "Microsoft.PowerShell" --accept-source-agreements --accept-package-agreements
    }
    elseif ($updateNeeded -and -not $isInstalled) {
      Write-Host "Installing PowerShell..." -ForegroundColor Yellow
      winget install "Microsoft.PowerShell" --accept-source-agreements --accept-package-agreements
    }
    else {
      Write-Host "󰸞 PowerShell is up to date." -ForegroundColor Green
    }
  }
  catch {
    Write-Error "󱎘 Failed to update or install PowerShell. Error: $_"
  }
}
