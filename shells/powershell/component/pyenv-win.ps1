$PYENV_VERSION = (&pyenv version-name) -replace '\s', ''
$Env:PYENV_VERSION = $PYENV_VERSION
$PYEXEDIR = ($Env:PYENV_HOME + "versions\$PYENV_VERSION")
$PYSCRIPTS = "$PYEXEDIR\Scripts"
$PYENVBIN = ($env:PYENV + "bin")
$PYENVSHIMS = ($env:PYENV + "shims")


function Get-PyenvPath {
    $PYENV_VERSION = (&pyenv version-name) -replace '\s', ''
    $Env:PYENV_VERSION = $PYENV_VERSION
    $PYEXEDIR = ($Env:PYENV_HOME + "versions\$PYENV_VERSION")
    $PYSCRIPTS = "$PYEXEDIR\Scripts"
    $PYENVBIN = ($env:PYENV + "bin")
    $PYENVSHIMS = ($env:PYENV + "shims")
    return $PYEXEDIR, $PYSCRIPTS, $PYENVBIN, $PYENVSHIMS
}

function Get-PyenvVersion {
    $PYENV_VERSION = (&pyenv version-name) -replace '\s', ''
    $Env:PYENV_VERSION = $PYENV_VERSION
    return $PYENV_VERSION
}

function pyenvTop {
Remove-Path -Path "$PYENVBIN"
Remove-Path -Path "$PYENVSHIMS"
Remove-Path -Path "$PYEXEDIR"
Remove-Path -Path "$PYSCRIPTS"

Add-PrependPath -Path "$PYENVBIN"
Add-PrependPath -Path "$PYENVSHIMS"
Add-PrependPath -Path "$PYEXEDIR"
Add-PrependPath -Path "$PYSCRIPTS"

}

function pyenvBottom {
Remove-Path -Path "$PYENVBIN"
Remove-Path -Path "$PYENVSHIMS"
Remove-Path -Path "$PYEXEDIR"
Remove-Path -Path "$PYSCRIPTS"

Add-Path -Path "$PYEXEDIR"
Add-Path -Path "$PYSCRIPTS"
Add-Path -Path "$PYENVSHIMS"
Add-Path -Path "$PYENVBIN"
}

pyenvTop

# $python3exePath = Split-Path -Parent (& { (pyenv which python3 | Out-String) }).Trim()
# Add-PrependPath -Path $python3exePath

# $pipexePath = Split-Path -Parent (& { (pyenv which pip | Out-String) }).Trim()
# Add-PrependPath -Path $pipexePath