$env:NEOVIMCONFIG = $env:LOCALAPPDATA + "\nvim"
$env:NEOVIMDATA = $env:LOCALAPPDATA + "\nvim-data"
$env:MASONBIN = $env:NEOVIMDATA + "\mason\bin"

# Add-Path -Path $env:MASONBIN