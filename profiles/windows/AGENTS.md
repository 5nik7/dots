# Repository Guidelines

## Project Structure & Module Organization

`windots` stores Windows dotfiles and desktop customization assets. Keep changes grouped by application under `config/`: terminal settings in `alacritty/`, `wezterm/`, and `wt/`; desktop tools in `komorebi/`, `glaze-wm/`, and `yasb/`; and other application settings in their named directories. Themes and images live beside their consumers, such as `config/bat/themes/` and `config/wt/icons/`.

`win.env` and `zshrc.local.symlink` provide environment and shell integration. `notes.md` records configuration locations and setup snippets. `rainmeter/5ui7e` is a Git submodule; manage their revisions deliberately and avoid initializing them for unrelated work.

## Build, Test, and Development Commands

There is no repository-wide build, package manager workflow, or test runner. Run these checks from the repository root:

- `git status --short`: inspect local changes before and after editing.
- `git diff --check`: detect whitespace errors in tracked changes.
- `git diff -- config/wezterm/`: review changes to one application's configuration.
- `zsh -n zshrc.local.symlink`: check shell syntax when Zsh is installed, without executing the startup file.

Validate configuration behavior in the corresponding application on Windows; record application versions and validation steps.

## Coding Style & Naming Conventions

Follow `.editorconfig`: UTF-8, two-space indentation, LF endings, and a final newline by default. Windows `.cmd`, `.bat`, and `.ps1` files use CRLF; INI files use four-space indentation. Markdown permits trailing whitespace. Respect `.gitattributes` and avoid unrelated line-ending conversions.

Preserve application-required filenames, key names, and existing Lua, TOML, YAML, JSON/JSONC, and CSS conventions. Keep assets with their consuming configuration. No repository-wide formatter or linter is configured.

## Testing Guidelines

No automated testing framework, test naming convention, or coverage threshold is established. Use format-aware validation: comment-bearing JSON requires JSONC support. Test changes with disposable configuration copies or isolated profiles, preserving live settings. For visual changes, inspect rendering and capture before/after screenshots. Report native Windows checks separately from syntax checks performed in WSL or Termux.

## Commit & Pull Request Guidelines

History primarily uses `Sync via <host> on <timestamp>` and `Update @ <timestamp>` messages. For manual contributions, use concise, descriptive subjects such as `Adjust WezTerm tab colors`, with one coherent purpose per commit.

PR descriptions should identify affected applications, expected behavior, validation performed, relevant issues, and screenshots for visual changes. Exclude credentials, generated caches, and new machine-local backups; review paths for portability before committing.

## Dots Integration

`config/` is canonical; retain `configs -> config` during migration. `.dots/files.json`
owns Windows inventory metadata for the Dots catalog. The shared native Python adapter resolves app-specific Windows locations through `${APP_CONFIG:app}` and `.dots/file-locations.json`. Maintain Windows PowerShell 5.1/7 alongside Bash-facing parent catalog behavior. Unknown/ambiguous app destinations, Windhawk exports and guest wsl.conf stay explicitly unmapped; never guess a destination or translate WSL paths. See the parent `docs/powershell.md` for mappings and native acceptance status.
Catalog observation must not initialize optional submodules or change desktop state.

## Bundled profile ownership

This directory is now a Dots platform profile, not an independent Androidots or Windots checkout. Follow the root [agent guide](../../AGENTS.md). Catalog source IDs are `termux` and `windows`; legacy IDs are recognized internally for receipt recovery, while CLI selectors require the canonical names. Use the root managed-file transactions for installation and retain the optional Rainmeter submodule boundary on Windows. See [profiles](../../docs/profiles.md).
