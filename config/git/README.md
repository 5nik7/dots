# Git configuration

Dots owns this directory and links it to `${CONFIG}/git`. Git reads `config`,
which includes common `gitconfig` settings followed by the ignored `gitplatform`
selector. The common file includes aliases, the original `gitppuccin` fallback,
and finally the generated `dots-theme.gitconfig` color include.

## Platform selection

Installing or linking `dots:git`, applying its mapping, or restoring it from a
stash selects `gitplatform -> termux`, `windows`, `wsl`, or `linux`. Linux starts
with a comment-only overlay. These are relative links inside this fixed source
directory, planned and journaled as a bounded Git companion rather than ordinary
nested catalog targets. No credential helper is executed by configuration checks.

A correct pre-existing selector is observed without claiming installation
ownership. Recognized platform links can be replaced with a retained baseline;
unrelated links/files and owned-link drift are refused. Stash keeps source files
and the selector. Uninstall restores only installation-owned changes, preserving
drift. Native Windows installation requires symlink capability; there is no copy
fallback or expansion of the separate Windows managed-operation command surface.

The preview-first `tools/migrate_git_config.py` repairs the previous Termux XDG
layout after platform settings have been moved into `termux`. `--apply --yes`
removes the stale Androidots Git catalog and import entries and only verified old global/overlay
links, retaining receipt recovery data. It accepts the old overlay entry point or
the consolidated one, requires the standard `~/.config` root, verifies effective
settings privately, and automatically undoes a failed verification. It does not
move/delete Androidots source files. Other/custom layouts use reviewed mappings.

## Shared colors and Delta

`default/themed/gitconfig.tpl` generates native Git colors and a Delta `dots`
feature. Refresh publishes the include through the existing theme connector;
identity, credentials, aliases, commands and behavior options remain source edits.
The original colors and `gitppuccin` feature remain the fallback when the include
is missing. Git roles supply foreground colors; bold/reverse attributes are
explicit template choices. Delta uses `normal` where Git's foreground is `reset`; native diff old/new slots also use that compatible spelling because Delta reads them. The common setting uses Delta's supported `true-color` key.

Native Git status groups deletions and renames under its staged/changed colors;
it does not provide separate color slots for those states.

Diff backgrounds blend resolved added/deleted foregrounds into the background at
10% (ordinary) and 25% (emphasized). Reset foregrounds produce the background.
Mode, blame colors, decorations and moved-line tints follow the shared palette.

Delta 0.20.1 reads its bat assets from the standard cache location rather than
`BAT_CACHE_PATH`. Each Dots generation therefore exposes `delta-cache/bat` as a
relative link to its own bat cache. The common Git pager/filter commands redirect
only their Delta processes with `XDG_CACHE_HOME` and select `--syntax-theme=Dots`;
interactive filtering retains `--color-only`. Missing generated cache falls back
to ordinary Delta. The user's normal bat cache and shell environment are unchanged.
Direct standalone Delta invocations do not receive this Git-specific cache setup.
Native Windows theme publication remains unsupported; the common fallback works
without generated data. Native verification here covers Termux, not Windows/WSL.

## Update branch

```
git branch -m master main
git fetch origin
git branch -u origin/main main
git remote set-head origin -a
```
