# Scoop Packages
# scoop bucket add anderlli0053_DEV-tools https://github.com/anderlli0053/DEV-tools
# scoop install winget powershell 7zip bat delta exa `
# fd fzf gh git gzip lazygit less ntop openssh ripgrep wget nodejs16 python

# scoop update *

# Install-Module -Name Terminal-Icons -Repository PSGallery -Scope AllUsers -Force -AllowClobber
# Install-Module -Name z -Scope AllUsers -Force -AllowClobber
# Install-Module -Name PSReadLine -Scope AllUsers -Force -SkipPublisherCheck -AllowClobber
# Install-Module -Name PSFzf -Scope AllUsers -Force -AllowClobber

# Update-Module
# $REPOS = "C:\repos"
# $DOTS = "C:\repos\dots"
# $DOTSFILES = "$DOTFILES\configs"
# $WINCONFIG = "$HOME\.config"
# $APPDATA = "$HOME\AppData"
function ln {
        param(
                [Parameter(Mandatory = $true)]
                [string]$base,

                [Parameter(Mandatory = $true)]
                [string]$target
        )

        try {
                if ((Test-Path -Path $target) -and (Get-Item -Path $target).Target -eq $base) {
                        Write-Host ''
                        Write-Host -ForegroundColor Yellow "Already a symlink."
                        Write-Host ''
                }
                elseif (Test-Path -Path $target) {
                        $bakDate = Get-Date -Format "yyyy-MM-dd_HH-mm"
                        Rename-Item -Path $target -NewName "$target.$bakDate.bak" -ErrorAction Stop | Out-Null
                        Write-Host ''
                        Write-Host -ForegroundColor White "Creating a backup file: " -NoNewline
                        Write-Host -ForegroundColor Green "$target.$bakDate.bak"
                        New-Item -ItemType SymbolicLink -Path $target -Target $base -ErrorAction Stop | Out-Null
                        Write-Host ''
                        Write-Host -ForegroundColor Blue "$base " -NoNewline
                        Write-Host -ForegroundColor Yellow "->" -NoNewline
                        Write-Host -ForegroundColor Cyan " $target"
                        Write-Host ''
                }
                else {
                        New-Item -ItemType SymbolicLink -Path $target -Target $base -ErrorAction Stop | Out-Null
                        Write-Host ''
                        Write-Host -ForegroundColor Blue "$base " -NoNewline
                        Write-Host -ForegroundColor Yellow "->" -NoNewline
                        Write-Host -ForegroundColor Cyan " $target"
                        Write-Host ''
                }
        }
        catch {
                Write-Output "Failed to create symbolic link: $_"
        }
}

# ln "$DOTCONF\yazi" "$CONFDIR\yazi"

# ln "$DOTCONF\code\settings.json" "$CONFDIR\settings.json"

# ln "$DOTCONF\starship\starship.toml" "$CONFDIR\starship.toml"

# ln "$DOTCONF\wal" "$CONFDIR\wal"

# ln "$DOTCONF\vifm" "$APPDATA\vifm"

# ln "$DOTCONF\lsd" "$APPDATA\lsd"

# ln "$DOTCONF\alacritty" "$APPDATA\alacritty"

# C:\repos\dots\configs\powershell\profile.ps1

# ln "$DOTFILES\powershell\Profile.ps1" "C:\Program Files (x86)\PowerShell\7\profile.ps1"

# ln "$DOTCONF\powershell\.env" "$HOME\Documents\PowerShell\.env"

# ln "$env:DOTFILES\wt\settings.json" "C:\ProgramData\scoop\apps\windows-terminal-preview\1.20.10303.0\settings\settings.json"

# ln "$env:DOTFILES\code\settings.json" "C:\Users\nickf\AppData\Roaming\Code\User\settings.json"

# ln "$env:CONFIG\wt\settings.json" "C:\repos\windots\wt\settings.json"

# ln "$env:REPOS\power5hell\Scripts" "$env:CONFIG\PowerShell\Scripts"

# ln "$env:REPOS\starship\starship.toml" "$env:CONFIG\starship.toml"

# ln "$DOTCONF\bat" "$CONFDIR\bat"

# ln "$env:DOTFILES\bat" "C:\Users\nickf\AppData\Roaming\bat"

# ln "$env:LOCALAPPDATA\nvim" "$env:REPOS\neoviim"

# ln "$env:DOTFILES\glaze-wm" "C:\Users\nickf\.glaze-wm"

# ln "$env:DOTFILES\bat" "C:\ProgramData\bat"

# Fetch submodules
# git submodule update --init --recursive