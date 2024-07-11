$ENV:LAB = "$ENV:PROJECTS\lab"
$LAB = $ENV:LAB

$ENV:PSLAB = "$LAB\powershell"
$PSLAB = $ENV:PSLAB

foreach ( $SUBLAB in ("rnd") ) {
  if (Test-Path("$PSLAB\$SUBLAB")) {
    Add-Path -Path "$PSLAB\$SUBLAB"
  }
}