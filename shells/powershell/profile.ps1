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