$env:box = $true
if ($env:box -eq $true) { $Global:box = $true }
else { $Global:box = $false }

if ($env:padding) { $Global:padout = $env:padding }
else { $Global:padout = 3 }



# Editor Configuration
$EDITOR = if (Test-CommandExists code) { 'nvim' }
elseif (Test-CommandExists code) { 'nvim' }
elseif (Test-CommandExists vim) { 'vim' }
elseif (Test-CommandExists vi) { 'vi' }
else { 'notepad' }
$env:EDITOR = $EDITOR
function Edit-Item {
    param (
        [string]$Path = $PWD
    )

    if ($Path) {
        & $env:EDITOR $Path
    }
    else {
        & $env:EDITOR
    }
}
