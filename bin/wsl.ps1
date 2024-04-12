function archinit($distro) {
    Write-Host "Init." -ForegroundColor "Green";
    wsl -d "$distro" exec sudo cat /mnt/c/repos/dotfiles/scripts/archinit > //wsl.localhost/"$distro"/home/snikt/archinit
    wsl -d "$distro" exec sudo chmod +x /home/snikt/archinit
}

function senddots($distro) {
    Write-Host "Init." -ForegroundColor "Green";
    wsl -d "$distro" exec sudo cat /mnt/c/repos/dotfiles/scripts/do75 > //wsl.localhost/"$distro"/home/snikt/.local/bin/do75
    wsl -d "$distro" exec sudo chmod +x /home/snikt/.local/bin/do75
}
