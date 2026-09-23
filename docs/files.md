# File catalog

**Status: Implemented metadata and read-only inventory; general file installation remains proposed.**

`dots files` starts the managed-files workflow by locating sources, recording their
intent, classifying targets, and listing them. It requires Python 3.9+ on a POSIX
host; discovery additionally requires Git. Neither ordinary dispatch nor basic
help requires Python or Git. Go development remains paused.

## Commands

```bash
dots files sources
dots files list --sort app
dots files list --repo androidots --platform termux
dots files list --all-platforms --json
dots files discover
dots files locate kitty
dots files show dots:kitty
dots files source dots:kitty
dots files target dots:kitty
```

`list` shows tracked records; `discover` shows untracked candidates in declared
roots, respecting Git exclusions and directory ownership. `locate QUERY` searches
both by case-insensitive ID, application, source and target substrings. `show`,
`source` and `target` require a qualified `repository:resource` ID. `sources` reports
available, unavailable and explicitly excluded repositories without initializing
submodules. Read-only commands do not create caches, lock files or state.

List/discover/locate accept `--repo`, `--app`, `--category`, `--status`, `--platform`,
`--all-platforms`, `--sort id|app|repository|source|status`, and `--json`. The default
platform is detected; other platforms can be inspected explicitly. `--json` emits
one schema-1 object with `platform`, `resources` and `sources`; diagnostics go to
stderr. Human lists are tab-separated ID, status, source and target. Sources list
ID, availability, repository root and platforms. Success is 0; validation/I/O
errors are 1 and invalid command syntax is 2.

Tracking writes only repository metadata, with an exclusive lock, flushed temporary
file and atomic replacement. Quote destination tokens to leave them literal:

```bash
dots files track config/example/settings --repo dots --id example-settings \
  --app example --category config --target '${CONFIG}/example/settings' \
  --platforms termux linux wsl --strategy link
```

The source must exist in its owning repository. Whole directories require
`--strategy directory-link`; `copy` records a future explicit copy preference.
`--update` is required to change an existing ID. Repeating the identical record is
a no-op. `--replaces REPOSITORY:ID` is repeatable. Tracking does not install, move,
link, copy, stage in Git, or read the contents of the source. `add`, `remove`, `set`,
`edit`, installation planning and undo remain future commands; link will be the
default installation strategy.

## Ownership and formats

[.dots/sources.json](../.dots/sources.json) declares composition with schema 1 and
`sources` containing `id`, repository-relative `path`, allowed `roots`, `platforms`
and optional `excluded`. Dots owns common configurations; Androidots contributes
Termux-specific sources. Windots is inventoried for Windows but has no native
Windows target adapter. Neovim owns its catalog at `config/nvim/.dots/files.json`.
Missing optional catalogs are reported unavailable. Secrets are explicitly excluded;
no private submodule is initialized and no source-file contents are printed. Third-party
PowerShell and Rainmeter submodules are explicitly excluded from resource ownership.

Every participating repository owns `.dots/files.json`:

```json
{
  "schema": 1,
  "repository": "dots",
  "resources": [{
    "id": "example",
    "source": "config/example",
    "app": "example",
    "category": "config",
    "platforms": ["termux", "linux", "wsl"],
    "target": "${CONFIG}/example",
    "strategy": "directory-link"
  }]
}
```

IDs, applications and categories use lowercase letters, digits, `_` and `-`,
starting with a letter. Sources stay repository-relative without `..`. Targets
start with `${HOME}`, `${CONFIG}`, `${BIN}` or `${TERMUX}` and contain no traversal.
CONFIG uses XDG_CONFIG_HOME or HOME/.config; BIN is HOME/.local/bin; TERMUX is
HOME/.termux and resolves only on Termux. A null target records an unmapped source.
Catalog and lock symlinks are refused. Source symlinks remain observable data.

Resources are never silently overridden by repository order. Exact target claims
conflict unless one explicitly replaces every other claimant. A directory resource
owns its descendants: a second nested target conflicts, even when the directory is
already linked. These are observations, not installation decisions. Correct links,
broken links, other links, existing files/directories, absent sources, inactive
platforms, unmapped targets, unsupported destinations and conflicts are distinct
statuses. `replaced_by`, `conflicts` and `replacement_unavailable` explain composition.
There is no content hashing or claim that an existing copy matches its source.

The JSON catalog is a small implemented inventory model, separate from the proposed
module/profile manifests in [specification.md](specification.md). Future installation
must consume explicit ownership and the transaction rules in [safety.md](safety.md).

Theme publication may deliberately connect Termux colors to generated state instead
of the catalogued baseline source. Inventory reports that link as `linked-elsewhere`;
it does not infer adoption or overwrite it. General installation will need to account
for these specialized generated targets explicitly.
