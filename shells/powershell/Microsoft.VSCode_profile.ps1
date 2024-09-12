$ENV:DOTS = "$HOME\dots"
$DOTS = $ENV:DOTS

$ENV:PSDOT = "$ENV:DOTS\shells\powershell"
$PSDOT = $ENV:PSDOT

foreach ( $includeFile in ("core") ) {
  Unblock-File $PSDOT\$includeFile.ps1
  . "$PSDOT\$includeFile.ps1"
}