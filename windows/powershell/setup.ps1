# Scoop Packages
# scoop bucket add anderlli0053_DEV-tools https://github.com/anderlli0053/DEV-tools
# scoop install winget powershell 7zip bat delta exa `
# fd fzf gh git gzip lazygit less ntop openssh ripgrep wget nodejs16 python

# scoop update *

# Install-Module -Name Terminal-Icons -Repository PSGallery -Scope CurrentUser -Force -AllowClobber
# Install-Module -Name z -Scope CurrentUser -Force -AllowClobber
# Install-Module -Name PSReadLine -Scope CurrentUser -Force -SkipPublisherCheck -AllowClobber
# Install-Module -Name PSFzf -Scope CurrentUser -Force -AllowClobber

# Update-Module


function ln($file1, $file2) {
    if (Test-Path $file1) {
        Remove-Item -Recurse -Force $file1
        New-Item -ItemType SymbolicLink -Path $file1 -Target $file2
    }
    else {
        New-Item -ItemType SymbolicLink -Path $file1 -Target $file2
    }
}

# ln "$env:LOCALAPPDATA\nvim" "X:\hub\repos\do75\nvim"

# ln "C:\Users\nickf\.config\starship.toml" "X:\hub\repos\do75\starship\starship.toml"

ln "C:\Users\nickf\Documents\PowerShell\Profile.ps1" "X:\hub\repos\do75\windows\powershell\Profile.ps1"
ln "C:\Users\nickf\Documents\PowerShell\Microsoft.PowerShell_profile.ps1" "X:\hub\repos\do75\windows\powershell\Microsoft.PowerShell_profile.ps1"
ln "C:\Users\nickf\Documents\PowerShell\Microsoft.VSCode_profile.ps1" "X:\hub\repos\do75\windows\powershell\Microsoft.VSCode_profile.ps1"

ln "C:\Users\nickf\Documents\WindowsPowerShell\Profile.ps1" "X:\hub\repos\do75\windows\powershell\Profile.ps1"
ln "C:\Users\nickf\Documents\WindowsPowerShell\Microsoft.PowerShell_profile.ps1" "X:\hub\repos\do75\windows\powershell\Microsoft.PowerShell_profile.ps1"
ln "C:\Users\nickf\Documents\WindowsPowerShell\Microsoft.VSCode_profile.ps1" "X:\hub\repos\do75\windows\powershell\Microsoft.VSCode_profile.ps1"

# Fetch submodules
# git submodule update --init --recursive