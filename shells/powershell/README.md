# Powershell

## Dots initialization

The startup file resolves file and parent-directory symlinks and loads the adjacent native Dots loader directly. Checkout-derived paths replace inherited Dots path values; set custom overrides after initialization. Keep the full checkout layout when relocating it; the former configuration body lives in `interactive.ps1`. See [shell initialization](../../docs/shell-init.md) for bootstrap, common environment defaults, reload behavior and verification limits.
