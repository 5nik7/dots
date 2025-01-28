$PYENV_VERSION = (&pyenv version-name) -replace '\s', ''
$Env:PYENV_VERSION = $PYENV_VERSION
$PYEXEDIR = "$Env:PYENV_HOME" + "versions\$PYENV_VERSION"
$PYSCRIPTS = "$PYEXEDIR\Scripts"

Add-Path -Path "$PYEXEDIR"
Add-Path -Path "$PYSCRIPTS"