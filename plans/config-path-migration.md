# Configuration path migration

**Status: Implemented; isolated verification recorded in docs/testing.md**

- [x] Preserve existing config directory moves and compatibility aliases.
- [x] Update owned references and Neovim submodule worktree registration.
- [x] Test preview/apply/rollback using disposable links.
- [x] Apply reviewed home-link migration with durable recovery evidence.

Go implementation remains paused. No commits, pushes, package installation or live theme/wallpaper activation are included. Existing user changes and independent submodule histories are preserved.

Fourteen links were migrated and verified against their recorded new targets.
Recovery journal: `~/.local/state/dots/migrations/config-paths-20260923.json`.
The helper defaults to preview. To inspect remaining candidates:

```bash
python3 -B tools/migrate_config_paths.py --home "$HOME" --repo "$HOME/dots"
```

Rollback is explicit via the same roots plus `--rollback --journal ABSOLUTE_PATH`;
it refuses link drift. Compatibility aliases and the Neovim pin remain. At the migration checkpoint, the scoped
Neovim gitlink path move was staged and other source edits were uncommitted, including
independent platform/Neovim repositories. This is historical index evidence; inspect
current Git state before staging or delivering any follow-up. No whole-tree staging or history rewrite
was performed. Remove aliases only in a future reviewed cleanup.

Fourteen additional repository-owned Rofi/Starship symlinks were changed to relative
targets within `config/`, preserving their resolved source identity. Original link
text is retained at `~/.local/state/dots/migrations/config-source-links-20260923.json`.
All 897 historical config paths across the three repositories still have mapped
objects in the canonical directories.

## Presentation Acceptance for Follow-up Work

Any future human migration preview or recovery view must meet the [presentation contract](../docs/presentation.md) and its acceptance gate, with consistent source/target, drift and recovery wording. Preserve the helper's machine-readable reports and durable journal format. This requirement does not repeat the completed migration or authorize alias removal.
