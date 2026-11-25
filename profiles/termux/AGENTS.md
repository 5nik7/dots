# Repository Guidelines

## Project Structure & Module Organization

`androidots` contains Android/Termux dotfiles, shell utilities, and application settings.

- `bin/`: clipboard, battery, font, terminal-color, and X11 helper scripts.
- `config/`: application settings; `config/fastfetch/` and `config/termux/`: terminal properties, colors, and font assets.
- `system/`, `profile.json`, and `shells/init.zsh`: system metadata, profile configuration and personal shell hooks.

## Build, Test, and Development Commands

There is no repository-wide build or test runner. Run checks from the repository root:

- `bash -n bin/chnf`: syntax-check a Bash helper without executing it; substitute the changed script.
- `sh -n bin/cpy`: syntax-check a POSIX shell helper.
- `zsh -n zshrc.local.symlink`: check Zsh syntax.
- `bash bin/test_true_color.sh` or `bash bin/test_24_bit_color.sh`: display terminal-color diagnostics for visual inspection.
- `stylua --check config/nvim/`: check Lua formatting when StyLua is installed.
- `git diff --check`: detect whitespace errors before review.

## Coding Style & Naming Conventions

Follow `.editorconfig`: UTF-8, LF endings, final newlines, and two-space indentation by default. Neovim's `stylua.toml` specifies two spaces and a 120-column width. Preserve existing script names and interpreter shebangs; match surrounding naming conventions. Keep application-specific changes within their configuration directory. Quote shell path expansions and preserve Termux-specific paths where required.

## Security & Configuration

Review account and host configuration changes for credentials and machine-specific data. Preserve unrelated staged changes, back up live configuration before applying edits, and exclude generated caches and local state.

## Dots Integration

`profile.json` owns Termux resource metadata consumed by the Dots catalog.
Tracking changes metadata only and must not install files. The parent's theme adapter
connects generated colors to `~/.termux/colors.properties` with a backup journal;
source termux settings remain here. Do not commit machine-specific connectors.

The parent now also implements bounded add/link/remove and recovery through one Python transaction engine. `.dots/file-locations.json` declares Termux discovery/import mappings; it does not initialize private repositories. Preserve per-file defaults, explicit directory ownership and the archived pre-import Git history. Use the parent isolated file-operation tests for integration.

## Bundled profile ownership

This directory is now a Dots platform profile, not an independent Androidots or Windots checkout. Follow the root [agent guide](../../AGENTS.md). Catalog source IDs are `termux` and `windows`; legacy IDs are recognized internally for receipt recovery, while CLI selectors require the canonical names. Use the root managed-file transactions for installation and retain the optional Rainmeter submodule boundary on Windows. See [profiles](../../docs/profiles.md).

Profile mappings contain implementation fields and one target; platform eligibility belongs in the root core registry. Generated paths, aliases and native maps belong in the shared backend, not profile `.env` files. Keep application environment declarations separate.
