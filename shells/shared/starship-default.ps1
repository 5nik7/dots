# Retire only values previously exported by Dots; explicit overrides stay valid.
if ($env:STARSHIP_CONFIG) {
    $dotsStarshipRoots = @($env:DOTFILES, $env:DOTCONFIG,
        "$env:DOTS/config", "$env:DOTS/configs", "$HOME/dots/config",
        "$HOME/dots/configs", "$HOME/.dots/config", "$HOME/.dots/configs")
    foreach ($dotsStarshipRoot in $dotsStarshipRoots) {
        if ($dotsStarshipRoot -and
            $env:STARSHIP_CONFIG.Replace('\', '/').TrimEnd('/') -eq
            ($dotsStarshipRoot.Replace('\', '/').TrimEnd('/') + '/starship/starship.toml')) {
            Remove-Item Env:STARSHIP_CONFIG
            break
        }
    }
    Remove-Variable dotsStarshipRoots, dotsStarshipRoot
}
