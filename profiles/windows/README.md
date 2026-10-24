# windots

windows dotfiles


## Dots catalog

Configuration source now lives in `config/`, with a temporary `configs -> config`
alias. `.dots/files.json` supplies Windows resource inventory to the parent Dots
checkout: `dots files list --repo windows --platform windows`. The parent checkout installer maps VS Code to the user settings file under APPDATA. Other application targets remain unmapped; wallpaper activation remains unsupported. Installation and restore use the parent shared transaction engine, without WSL or Bash.
