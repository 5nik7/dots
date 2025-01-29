using namespace System.Management.Automation
using namespace System.Management.Automation.Language

$Env:DOTS = "$Env:USERPROFILE\dots"
$Env:PSDOT = "$Env:DOTS\shells\powershell"
$Env:PSCOMPONENT = "$Env:PSDOT\component"

foreach ( $includeFile in ("env", "functions", "path", "aliases", "modules", "readline", "completions", "prompt", "lab") ) {
    Unblock-File "$Env:PSCOMPONENT\$includeFile.ps1"
    . "$Env:PSCOMPONENT\$includeFile.ps1"
}

$fzFile = if (Test-CommandExists fzf) { 'fzf' }
if ($fzFile) {
    Unblock-File "$Env:PSCOMPONENT\$FzFile.ps1"
    . "$Env:PSCOMPONENT\$FzFile.ps1"
}

$pyenvFile = if (Test-CommandExists pyenv) { 'pyenv-win' }
if ($pyenvFile) {
    Unblock-File "$Env:PSCOMPONENT\$pyenvFile.ps1"
    . "$Env:PSCOMPONENT\$pyenvFile.ps1"
}

$neovimFile = if (Test-CommandExists nvim) { 'neovim' }
if ($neovimFile) {
    Unblock-File "$Env:PSCOMPONENT\$neovimFile.ps1"
    . "$Env:PSCOMPONENT\$neovimFile.ps1"
}