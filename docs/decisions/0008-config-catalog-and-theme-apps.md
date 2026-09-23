# 0008: Configuration catalogs and application themes

**Status: Accepted and implemented, 2026-09-23.**

The owner requested an Omarchy-like command and theme layout, completion of the
existing `configs` to `config` moves, and a first practical files-management slice,
including Androidots. Further Go development remains paused.

Keep the Bash dispatcher from decision 0006. Implement file inspection and metadata
tracking with a Python standard-library backend, explicit source composition and
per-repository JSON catalogs. Defer general installation, add/remove/edit and undo.
`config/` is canonical; temporary `configs -> config` aliases preserve compatibility.
The Neovim Git worktree moves without changing its pinned commit or internal Git
directory name. A separate preview/apply/rollback helper journals existing live-link
retargeting, preserving resolved source identity.

Extend decision 0007 with flat theme variants, literal shared templates and a stable
XDG state `dots/current/theme` link to an immutable generation. Retain native palette
APIs, plural commands and old state reading. Omarchy semantic colors define shared
application appearance; native palette names remain queryable. Imported themes are
data only. Trusted bundled application files may override templates; downloaded
Lua, scripts and application configuration never execute or override generated data.

Bounded theme publication may back up and connect fixed application theme files and
reload available adapters. These operations have durable journals and reverse-order
rollback, independently of the proposed general Go transaction engine. Repository
source edits and metadata tracking remain ordinary Git-managed edits. Explicit Git
theme install/update/remove use staging, clean-tree checks and retained archives.
Wallpaper operations are separate, explicit, journaled adapter calls and cannot
promise restoration of an unknown prior Android/desktop wallpaper.

This is an authorized expansion of the earlier Zsh/Neovim-only slice. It does not
introduce arbitrary install manifests, hooks, remote bootstrap, package installation
or native Windows management. See [themes](../themes.md), [files](../files.md),
[safety](../safety.md), and the three focused plans under `plans/` for the contracts.
