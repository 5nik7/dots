# The installed rc keeps discovery cheap for both conventional and relocated checkouts.
$dotsRcRoot = if ($env:DOTS_BOOTSTRAP_DIR) { $env:DOTS_BOOTSTRAP_DIR } else { Join-Path $HOME 'dots' }
if (-not $env:DOTS_BOOTSTRAP_DIR) {
    $dotsRcCli = Get-Command dots.ps1 -CommandType ExternalScript -TotalCount 1 -ErrorAction SilentlyContinue
    if ($dotsRcCli) {
        $dotsRcRoot = [IO.Directory]::GetParent($dotsRcCli.Path).Parent.FullName
    } else {
        $dotsRcPin = Join-Path $HOME '.local/share/dots/bootstrap/checkout'
        if ([IO.File]::Exists($dotsRcPin)) {
            try {
                $dotsRcCandidate = [IO.File]::ReadAllText($dotsRcPin).TrimEnd([char]13, [char]10)
                if ($dotsRcCandidate -and $dotsRcCandidate -notmatch '\p{Cc}') { $dotsRcRoot = $dotsRcCandidate }
            } catch [IO.IOException] { } catch [UnauthorizedAccessException] { }
        }
    }
}
if (-not [IO.Path]::IsPathRooted($dotsRcRoot) -or
    ([IO.Path]::DirectorySeparatorChar -eq '\' -and $dotsRcRoot -notmatch '^(?:[a-z]:[\\/]|\\\\(?![?.]\\))') -or
    -not ([IO.File]::Exists([IO.Path]::Combine($dotsRcRoot, 'shells/powershell/profile.ps1')) -and
          [IO.File]::Exists([IO.Path]::Combine($dotsRcRoot, 'bin/dots.ps1')) -and
          [IO.File]::Exists([IO.Path]::Combine($dotsRcRoot, 'lib/dots/shell/startup.bash')))) {
    $dotsRcArgs = [Environment]::GetCommandLineArgs()
    $dotsRcMode = 'offline'
    if ([Environment]::UserInteractive -and -not [Console]::IsInputRedirected -and
        -not ($dotsRcArgs -match '^-(?:noni.*|command.*|c|file|f|enc.*)$')) {
        $dotsRcMode = 'interactive'
    }
    $dotsRcRoot = & (Join-Path $HOME '.local/share/dots/bootstrap/locate.ps1') $dotsRcMode
}
if ($dotsRcRoot) { . ([IO.Path]::Combine($dotsRcRoot, 'shells/powershell/profile.ps1')) }
Remove-Variable dotsRcRoot,dotsRcArgs,dotsRcMode,dotsRcCli,dotsRcCandidate,dotsRcPin -ErrorAction Ignore
