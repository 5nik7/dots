#!/usr/bin/env pwsh
# PowerShell conversion of git-it bash script

$ErrorActionPreference = 'Stop'

# Color definitions
$script:IsTerminal = -not [Console]::IsOutputRedirected

if ($IsTerminal) {
    $C_RESET = "`e[0m"
    $C_BOLD = "`e[1m"
    $C_DIM = "`e[2m"
    $C_ITALIC = "`e[3m"
    $C_UNDERLINE = "`e[4m"
    $C_REVERSE = "`e[7m"
    $C_BLACK = "`e[30m"
    $C_RED = "`e[31m"
    $C_GREEN = "`e[32m"
    $C_YELLOW = "`e[33m"
    $C_BLUE = "`e[34m"
    $C_MAGENTA = "`e[35m"
    $C_CYAN = "`e[36m"
    $C_WHITE = "`e[37m"
} else {
    $C_RESET = $C_BOLD = $C_DIM = $C_ITALIC = $C_UNDERLINE = $C_REVERSE = ''
    $C_BLACK = $C_RED = $C_GREEN = $C_YELLOW = $C_BLUE = $C_MAGENTA = $C_CYAN = $C_WHITE = ''
}

$color_key = $C_BLUE
$color_value = "$C_BOLD$C_GREEN"
$color_separator = "$color_key$C_DIM"

function Usage {
    $cmdname = Split-Path -Leaf $PSCommandPath
    Write-Host "${C_BOLD}${C_CYAN}$cmdname${C_RESET}"
    Write-Host ""
    Write-Host "${C_BOLD}Usage:${C_RESET}"
    Write-Host "${C_CYAN} $cmdname${C_RESET} ${C_YELLOW}[path] [remote]${C_RESET} ${C_GREEN}[flags]${C_RESET}"
    Write-Host "${C_CYAN} $cmdname${C_RESET} ${C_GREEN}-h | --help${C_RESET}"
    Write-Host ""
    Write-Host "${C_BOLD}Scope flags:${C_RESET}"
    Write-Host "${C_GREEN} --default${C_RESET}"
    Write-Host "${C_GREEN} -a${C_RESET}, ${C_GREEN}--all${C_RESET}"
    Write-Host "${C_GREEN} -I${C_RESET}, ${C_GREEN}--icon${C_RESET}       icon for host"
    Write-Host "${C_GREEN} -s${C_RESET}, ${C_GREEN}--scheme${C_RESET}     scheme"
    Write-Host "${C_GREEN} -H${C_RESET}, ${C_GREEN}--host${C_RESET}       host"
    Write-Host "${C_GREEN} -o${C_RESET}, ${C_GREEN}--owner${C_RESET}      owner"
    Write-Host "${C_GREEN} -r${C_RESET}, ${C_GREEN}--repo${C_RESET}       repo (no .git)"
    Write-Host ""
    Write-Host "${C_BOLD}Formatting flags:${C_RESET}"
    Write-Host "${C_GREEN} -v${C_RESET}, ${C_GREEN}--value${C_RESET}      values only"
    Write-Host "${C_GREEN} -0${C_RESET}, ${C_GREEN}--null${C_RESET}       NUL-delimited output"
    Write-Host "${C_GREEN} --join${C_RESET} ${C_YELLOW}SEP${C_RESET}   join outputs with SEP"
    Write-Host ""
    Write-Host "${C_BOLD}Notes:${C_RESET}"
    Write-Host "  • Clustered short flags supported: ${C_CYAN}-orv${C_RESET}, ${C_CYAN}-aH0${C_RESET}"
    Write-Host ""
    Write-Host "Exit codes:"
    Write-Host "  0 success / usage shown"
    Write-Host "  2 git missing / repo missing / bad args"
    Write-Host "  3 parse error"
}

function Fail {
    param([int]$code, [string]$message)
    [Console]::Error.WriteLine("${C_RED}$message${C_RESET}")
    exit $code
}

# Check if git is available
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Fail 2 "error: git not found"
}

# Initialize variables
$cwd = Get-Location | Select-Object -ExpandProperty Path
$path = $cwd
$remote = "origin"
$separator = '='

$want_any = $false
$want_icon = $false
$want_scheme = $false
$want_host = $false
$want_owner = $false
$want_repo = $false
$want_url = $false
$want_color = $false
$want_key = $false
$want_value = $true
$want_null = $false
$want_join = $false
$join_sep = ""

function SetScopeDefault {
    $script:want_color = $true
    $script:want_key = $true
    $script:want_url = $true
    $script:want_icon = $true
    $script:want_scheme = $true
    $script:want_host = $true
    $script:want_owner = $true
    $script:want_repo = $true
    $script:want_any = $true
}

function SetScopeAll {
    $script:want_color = $true
    $script:want_key = $true
    $script:want_url = $true
    $script:want_icon = $true
    $script:want_scheme = $true
    $script:want_host = $true
    $script:want_owner = $true
    $script:want_repo = $true
    $script:want_any = $true
}

function ApplyShortChar([char]$c) {
    switch ($c) {
        'h' { Usage; exit 0 }
        'a' { SetScopeAll }
        's' { $script:want_scheme = $true; $script:want_any = $true }
        'H' { $script:want_host = $true; $script:want_any = $true }
        'o' { $script:want_owner = $true; $script:want_any = $true }
        'r' { $script:want_repo = $true; $script:want_any = $true }
        'I' { $script:want_icon = $true; $script:want_any = $true }
        'u' { $script:want_url = $true; $script:want_any = $true }
        'c' { $script:want_color = $true }
        'k' { $script:want_key = $true }
        'v' { $script:want_value = $true }
        '0' { $script:want_null = $true }
        default { Fail 2 "unknown option: -$c" }
    }
}

# Parse command line arguments
$pos = New-Object System.Collections.Generic.List[string]

for ($i = 0; $i -lt $args.Count; $i++) {
    $a = [string]$args[$i]
    switch ($a) {
        "-h" { Usage; exit 0 }
        "--help" { Usage; exit 0 }
        "--default" { SetScopeDefault; continue }
        "-a" { SetScopeAll; continue }
        "--all" { SetScopeAll; continue }
        "--scheme" { $want_scheme = $true; $want_any = $true; continue }
        "--host" { $want_host = $true; $want_any = $true; continue }
        "--owner" { $want_owner = $true; $want_any = $true; continue }
        "--repo" { $want_repo = $true; $want_any = $true; continue }
        "--icon" { $want_icon = $true; $want_any = $true; continue }
        "--url" { $want_url = $true; $want_any = $true; continue }
        "--color" { $want_color = $true; continue }
        "--sep" {
            if ($i + 1 -ge $args.Count) { Fail 2 "--sep needs a separator" }
            $separator = [string]$args[$i + 1]
            $want_key = $true
            $i++
            continue
        }
        "-k" { $want_key = $true; continue }
        "--key" { $want_key = $true; continue }
        "-0" { $want_null = $true; continue }
        "--null" { $want_null = $true; continue }
        "-j" {
            if ($i + 1 -ge $args.Count) { Fail 2 "-j needs a separator" }
            $join_sep = [string]$args[$i + 1]
            $want_join = $true
            $want_key = $false
            $i++
            continue
        }
        "--join" {
            if ($i + 1 -ge $args.Count) { Fail 2 "--join needs a separator" }
            $join_sep = [string]$args[$i + 1]
            $want_join = $true
            $want_key = $false
            $i++
            continue
        }
        default {
            # Handle clustered short flags
            if ($a -match '^-[A-Za-z0-9]{2,}$') {
                foreach ($ch in $a.Substring(1).ToCharArray()) {
                    ApplyShortChar $ch
                }
                continue
            }
            if ($a -match '^-[A-Za-z0-9]$') {
                ApplyShortChar $a.Substring(1)[0]
                continue
            }
            if ($a -like "--*") {
                Fail 2 "unknown option: $a"
            }
            $pos.Add($a) | Out-Null
        }
    }
}

if ($pos.Count -ge 1) { $path = $pos[0] }
if ($pos.Count -ge 2) { $remote = $pos[1] }
if ($pos.Count -gt 2) { Fail 2 "too many positional args: $($pos[2])" }

# No-arg behavior (show usage if not in repo)
if ($args.Count -eq 0) {
    $null = git -C $path rev-parse --is-inside-work-tree 2>$null
    if ($LASTEXITCODE -ne 0) {
        Usage
        exit 0
    }
}

# Default scope == --default
if (-not $want_any) {
    SetScopeDefault
}

# Check if path is a git repo
$pathout = $path -replace [regex]::Escape($HOME), '~'
$null = git -C $path rev-parse --is-inside-work-tree 2>$null
if ($LASTEXITCODE -ne 0) {
    Fail 2 "$pathout not a git repo"
}

# Get git remote URL
$GIT_REMOTE = (git -C $path remote get-url $remote 2>$null)
if (-not $GIT_REMOTE) {
    $GIT_REMOTE = (git -C $path ls-remote --get-url 2>$null)
}
if (-not $GIT_REMOTE) {
    $GIT_REMOTE = ""
}

# Icon logic
$GIT_REMOTE_SYMBOL = if (-not $GIT_REMOTE) {
    ""
} elseif ($GIT_REMOTE -match 'github') {
    "󰊤"
} elseif ($GIT_REMOTE -match 'gitlab') {
    ""
} elseif ($GIT_REMOTE -match 'bitbucket') {
    ""
} elseif ($GIT_REMOTE) {
    ""
} else {
    ""
}

# Determine scheme
$is_ssh = ($GIT_REMOTE -match '^(ssh://|[^@]+@[^:/]+[:/])')
$scheme = if ($GIT_REMOTE -match '^[a-zA-Z][a-zA-Z0-9+.-]*://') {
    "https"
} elseif ($is_ssh) {
    "ssh"
} else {
    "unknown"
}

# Parse host
$host_val = ''
if ($GIT_REMOTE -match '^[^:]*://([^/]+)/') {
    $host_val = $matches[1]
} elseif ($GIT_REMOTE -match '^[^@]*@([^:/]+)[:/]') {
    $host_val = $matches[1]
}

# Parse owner and repo
$owner_val = ''
$repo_val = ''
if ($GIT_REMOTE -match '[/:]([^/]+)/([^/]+?)(?:\.git)?$') {
    $owner_val = $matches[1]
    $repo_val = $matches[2] -replace '\.git$', ''
}

# Format token function
function FormatToken([string]$k, [string]$v) {
    $k_out = $k
    $v_out = $v
    $sep = $separator

    if ($want_color) {
        $k_out = "$color_key$k$C_RESET"
        $v_out = "$color_value$v$C_RESET"
        $sep = "$color_separator$separator$C_RESET"
    }

    if ($want_key) {
        return "$k_out$sep$v_out"
    } else {
        return $v_out
    }
}

# Collect outputs
$outputs = New-Object System.Collections.Generic.List[string]

if ($want_url) {
    $outputs.Add((FormatToken 'url' $GIT_REMOTE)) | Out-Null
}
if ($want_icon) {
    $outputs.Add((FormatToken 'icon' $GIT_REMOTE_SYMBOL)) | Out-Null
}
if ($want_scheme) {
    $outputs.Add((FormatToken 'scheme' $scheme)) | Out-Null
}
if ($want_host) {
    $outputs.Add((FormatToken 'host' $host_val)) | Out-Null
}
if ($want_owner) {
    $outputs.Add((FormatToken 'owner' $owner_val)) | Out-Null
}
if ($want_repo) {
    $outputs.Add((FormatToken 'repo' $repo_val)) | Out-Null
}

# Output results
if ($want_join) {
    $joined = $outputs -join $join_sep
    if ($want_null) {
        [Console]::Write($joined)
        [Console]::Write([char]0)
    } else {
        Write-Output $joined
    }
} else {
    foreach ($output in $outputs) {
        if ($want_null) {
            [Console]::Write($output)
            [Console]::Write([char]0)
        } else {
            Write-Output $output
        }
    }
}

exit 0
