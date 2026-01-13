#!/usr/bin/env pwsh
# git-remote-info.ps1 (sh-compatible CLI + clustered short flags + colorized help)

function Usage {
    $c = @{ Reset="`e[0m"; Bold="`e[1m"; Cyan="`e[36m"; Green="`e[32m"; Yellow="`e[33m" }

    Write-Host ""
    Write-Host "$($c.Bold)$($c.Cyan)git-remote-info$($c.Reset)"
    Write-Host ""
    Write-Host "$($c.Bold)Usage:$($c.Reset)"
    Write-Host "  $($c.Cyan)git-remote-info.ps1$($c.Reset) $($c.Yellow)[path] [remote]$($c.Reset) $($c.Green)[flags]$($c.Reset)"
    Write-Host "  $($c.Cyan)git-remote-info.ps1$($c.Reset) $($c.Green)-h | --help$($c.Reset)"
    Write-Host ""
    Write-Host "$($c.Bold)Scope:$($c.Reset)"
    Write-Host "  $($c.Green)--default$($c.Reset)     scheme, host, owner, repo (also default when no scope flags)"
    Write-Host "  $($c.Green)-a$($c.Reset), --all        everything: scheme, host, owner, repo, basename, fullname, is_ssh, icon"
    Write-Host "  $($c.Green)-s$($c.Reset), --scheme"
    Write-Host "  $($c.Green)-H$($c.Reset), --host"
    Write-Host "  $($c.Green)-o$($c.Reset), --owner"
    Write-Host "  $($c.Green)-r$($c.Reset), --repo"
    Write-Host "  $($c.Green)-b$($c.Reset), --basename"
    Write-Host "  $($c.Green)-f$($c.Reset), --fullname"
    Write-Host "  $($c.Green)-i$($c.Reset), --is-ssh"
    Write-Host "  $($c.Green)-I$($c.Reset), --icon (explicit icon implies --value)"
    Write-Host "  $($c.Green)-E$($c.Reset), --env"
    Write-Host ""
    Write-Host "$($c.Bold)Formatting:$($c.Reset)"
    Write-Host "  $($c.Green)-v$($c.Reset), --value"
    Write-Host "  $($c.Green)-0$($c.Reset), --null"
    Write-Host "      $($c.Green)--join$($c.Reset) $($c.Yellow)SEP$($c.Reset)"
    Write-Host ""
}

function Fail([string]$m, [int]$code = 2) { [Console]::Error.WriteLine($m); exit $code }

$path = (Get-Location)
$remote = "origin"

$wantScheme=$false; $wantHost=$false; $wantOwner=$false; $wantRepo=$false
$wantBasename=$false; $wantFullname=$false; $wantIsSsh=$false; $wantIcon=$false
$wantAny=$false

$wantValue=$false; $wantNull=$false; $wantJoin=$false; $joinSep=""
$wantEnv=$false

$iconExplicit = $false
$pos = New-Object System.Collections.Generic.List[string]

function SetDefault {
  $script:wantScheme=$true; $script:wantHost=$true; $script:wantOwner=$true; $script:wantRepo=$true
  $script:wantAny=$true
}

function SetAll {
  $script:wantScheme=$true; $script:wantHost=$true; $script:wantOwner=$true; $script:wantRepo=$true
  $script:wantBasename=$true; $script:wantFullname=$true; $script:wantIsSsh=$true; $script:wantIcon=$true
  $script:wantAny=$true
}

function ApplyShortChar([char]$c) {
  switch ($c) {
    'h' { Usage; exit 0 }
    'a' { SetAll }
    's' { $script:wantScheme=$true; $script:wantAny=$true }
    'H' { $script:wantHost=$true;   $script:wantAny=$true }
    'o' { $script:wantOwner=$true;  $script:wantAny=$true }
    'r' { $script:wantRepo=$true;   $script:wantAny=$true }
    'b' { $script:wantBasename=$true; $script:wantAny=$true }
    'f' { $script:wantFullname=$true; $script:wantAny=$true }
    'i' { $script:wantIsSsh=$true;    $script:wantAny=$true }
    'I' { $script:wantIcon=$true;     $script:wantAny=$true; $script:iconExplicit=$true }
    'E' { $script:wantEnv=$true }
    'v' { $script:wantValue=$true }
    '0' { $script:wantNull=$true }
    default { Fail ("unknown option: -{0}" -f $c) }
  }
}

for ($i=0; $i -lt $args.Count; $i++) {
  $a = [string]$args[$i]
  switch ($a) {
    "-h" { Usage; exit 0 }
    "--help" { Usage; exit 0 }

    "--default" { SetDefault; continue }
    "-a" { SetAll; continue }
    "--all" { SetAll; continue }

    "--scheme" { $wantScheme=$true; $wantAny=$true; continue }
    "--host"   { $wantHost=$true;   $wantAny=$true; continue }
    "--owner"  { $wantOwner=$true;  $wantAny=$true; continue }
    "--repo"   { $wantRepo=$true;   $wantAny=$true; continue }
    "--basename" { $wantBasename=$true; $wantAny=$true; continue }
    "--fullname" { $wantFullname=$true; $wantAny=$true; continue }
    "--is-ssh"   { $wantIsSsh=$true;    $wantAny=$true; continue }
    "--icon"     { $wantIcon=$true;     $wantAny=$true; $iconExplicit=$true; continue }

    "--env"    { $wantEnv=$true; continue }
    "--value"  { $wantValue=$true; continue }
    "--null"   { $wantNull=$true;  continue }
    "--join"   {
      if ($i+1 -ge $args.Count) { Fail "--join needs a separator" }
      $joinSep = [string]$args[$i+1]
      $wantJoin = $true
      $i++
      continue
    }

    default {
      if ($a -match '^-[A-Za-z0-9]{2,}$') { foreach ($ch in $a.Substring(1).ToCharArray()) { ApplyShortChar $ch }; continue }
      if ($a -match '^-[A-Za-z0-9]$')     { ApplyShortChar $a.Substring(1)[0]; continue }
      if ($a -like "--*") { Fail ("unknown option: {0}" -f $a) }
      $pos.Add($a) | Out-Null
    }
  }
}

if ($pos.Count -ge 1) { $path = $pos[0] }
if ($pos.Count -ge 2) { $remote = $pos[1] }
if ($pos.Count -gt 2) { Fail ("too many positional args: {0}" -f $pos[2]) }

if (-not (Get-Command git -ErrorAction SilentlyContinue)) { Fail "git not found" }

# No-arg behavior (usage if not in repo)
if ($args.Count -eq 0) {
  $null = git -C . rev-parse --is-inside-work-tree 2>$null
  if ($LASTEXITCODE -ne 0) { Usage; exit 0 }
}

# default scope == --default
if (-not $wantAny) { SetDefault }

# --icon implies --value ONLY when explicitly requested (not via --all)
if ($iconExplicit -and -not $wantEnv) { $wantValue = $true }

$null = git -C $path rev-parse --is-inside-work-tree 2>$null
if ($LASTEXITCODE -ne 0) { Fail ("not a git repo: {0}" -f $path) }

# starship-style vars + fallback
$GIT_REMOTE = (git -C $path remote get-url $remote 2>$null)
if (-not $GIT_REMOTE) { $GIT_REMOTE = (git -C $path ls-remote --get-url 2>$null) }

# icon logic (your rules)
if (-not $GIT_REMOTE) { $GIT_REMOTE_SYMBOL = "" }
elseif ($GIT_REMOTE -match 'github') { $GIT_REMOTE_SYMBOL = "󰊤" }
elseif ($GIT_REMOTE -match 'gitlab') { $GIT_REMOTE_SYMBOL = "" }
elseif ($GIT_REMOTE -match 'bitbucket') { $GIT_REMOTE_SYMBOL = "" }
elseif ($GIT_REMOTE) { $GIT_REMOTE_SYMBOL = "" }
else { $GIT_REMOTE_SYMBOL = "" }

# remote missing and user asked for more than icon
if (-not $GIT_REMOTE) {
  $onlyIcon = $wantIcon -and -not ($wantScheme -or $wantHost -or $wantOwner -or $wantRepo -or $wantBasename -or $wantFullname -or $wantIsSsh)
  if (-not $onlyIcon) { Fail "parse error: no remote url found" 3 }
}

$isSshVal = ($GIT_REMOTE -match '^(ssh://|[^@]+@[^:/]+[:/])')
$schemeVal = if ($GIT_REMOTE -match '^[a-zA-Z][a-zA-Z0-9+.-]*://') { "https" } elseif ($isSshVal) { "ssh" } else { "unknown" }

$hostVal = $null
if ($GIT_REMOTE -match '://([^/]+)/') { $hostVal = $matches[1] }
elseif ($GIT_REMOTE -match '@([^:/]+)[:/]') { $hostVal = $matches[1] }

if ($GIT_REMOTE -notmatch '[/:]([^/]+)/([^/]+?)(?:\.git)?$') {
  $onlyIcon = $wantIcon -and -not ($wantScheme -or $wantHost -or $wantOwner -or $wantRepo -or $wantBasename -or $wantFullname -or $wantIsSsh)
  if (-not $onlyIcon) { Fail ("parse error: {0}" -f $GIT_REMOTE) 3 }
}
$ownerVal = $matches[1]
$repoVal  = ($matches[2] -replace '\.git$', '')

$basenameVal = $repoVal
$fullnameVal = "$ownerVal/$repoVal"

function FormatToken([string]$k, [string]$v) {
  if ($wantEnv) { return ("export {0}='{1}'" -f $k, $v.Replace("'", "''")) }
  if ($wantValue) { return $v }
  return "$k=$v"
}

$tokens = New-Object System.Collections.Generic.List[string]
if ($wantScheme)   { $tokens.Add((FormatToken "scheme" $schemeVal)) | Out-Null }
if ($wantHost)     { $tokens.Add((FormatToken "host"   $hostVal)) | Out-Null }
if ($wantOwner)    { $tokens.Add((FormatToken "owner"  $ownerVal)) | Out-Null }
if ($wantRepo)     { $tokens.Add((FormatToken "repo"   $repoVal)) | Out-Null }
if ($wantBasename) { $tokens.Add((FormatToken "basename" $basenameVal)) | Out-Null }
if ($wantFullname) { $tokens.Add((FormatToken "fullname" $fullnameVal)) | Out-Null }
if ($wantIsSsh)    { $tokens.Add((FormatToken "is_ssh" ($isSshVal.ToString().ToLower()))) | Out-Null }
if ($wantIcon)     { $tokens.Add((FormatToken "icon" $GIT_REMOTE_SYMBOL)) | Out-Null }

if ($wantJoin) {
  $joined = ($tokens.ToArray() -join $joinSep)
  if ($wantNull) { [Console]::Out.Write($joined + "`0") } else { $joined }
} else {
  if ($wantNull) {
    foreach ($t in $tokens) { [Console]::Out.Write($t); [Console]::Out.Write("`0") }
  } else {
    $tokens
  }
}
