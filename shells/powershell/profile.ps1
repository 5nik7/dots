using namespace System.Management.Automation
using namespace System.Management.Automation.Language

$env:DOTS = "$env:USERPROFILE\dots"
$Global:DOTS = $env:DOTS

$env:SHELLS = "$env:DOTS\shells"
$Global:SHELLS = $env:SHELLS

$env:PSDOT = "$env:SHELLS\powershell"
$Global:PSDOT = $env:PSDOT

$env:PSCOMPONENT = "$env:PSDOT\component"
$Global:PSCOMPONENT = $env:PSCOMPONENT

foreach ( $includeFile in ("env", "functions", "path", "aliases", "modules", "readline", "completions", "prompt", "lab", "util") ) {
    Unblock-File "$env:PSCOMPONENT\$includeFile.ps1"
    . "$env:PSCOMPONENT\$includeFile.ps1"
}

$fzFile = if (Test-CommandExists fzf) { 'fzf' }
if ($fzFile) {
    Unblock-File "$env:PSCOMPONENT\$FzFile.ps1"
    . "$env:PSCOMPONENT\$FzFile.ps1"
}

$pyenvFile = if (Test-CommandExists pyenv) { 'pyenv-win' }
if ($pyenvFile) {
    Unblock-File "$env:PSCOMPONENT\$pyenvFile.ps1"
    . "$env:PSCOMPONENT\$pyenvFile.ps1"
}

$neovimFile = if (Test-CommandExists nvim) { 'neovim' }
if ($neovimFile) {
    Unblock-File "$env:PSCOMPONENT\$neovimFile.ps1"
    . "$env:PSCOMPONENT\$neovimFile.ps1"
}
