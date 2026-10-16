# Git configuration

Dots links this directory to `${CONFIG}/git`. Git reads its `config` entry point,
which includes common `gitconfig` settings (and their sibling aliases/theme) plus
optional `~/.config/git-termux/config` overrides supplied by Androidots. No
credential helper is executed merely by loading or validating configuration.

The home-anchored overlay include is deliberate: `../git-termux/config` would
follow the directory symlink into the repository before traversing `..`. The
bounded `tools/migrate_git_config.py` migration requires the standard `~/.config`
root; custom XDG layouts require explicitly updating the overlay include/mapping.
The general `dots files edit` command supports custom XDG roots.

The migration preserves Android settings, journals configuration/catalog/link
changes and provides an undo transaction. Its default invocation is preview-only;
`--apply --yes` applies and verifies the standard Git global settings without
printing values. A failed post-apply validation invokes guarded undo.

## Update branch

```
git branch -m master main
git fetch origin
git branch -u origin/main main
git remote set-head origin -a
```
