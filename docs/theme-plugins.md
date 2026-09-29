# Theme plugins

Dots runs explicitly enabled local integrations after successful theme publication.
Ordinary themes and Anodize themes use the same publisher and plugin runner.
All bundled and newly discovered user plugins start **disabled**.

```bash
dots theme plugins
dots theme plugins list
dots theme plugins doctor
dots theme plugins enable gtk
dots theme plugins enable qt6ct
dots theme plugins run
dots theme plugins run gtk
dots theme plugins disable gtk
```

Enable and disable change selection only. Enabling a user hook is approval to run
that trusted file with your privileges on future publication or explicit runs.
Review its contents first. Disabling stops future execution: it neither deletes
generated files nor restores previous application settings. A named disabled
plugin cannot run; enable it explicitly first.

`list`, `doctor [NAME]`, and `run [NAME]` accept `--json`. Their stdout is one
schema-1 object with `action` and `plugins`; per-plugin records contain `name` and
either discovery fields (`origin`, `file`, `enabled`, `availability`, `problems`)
or run fields (`status`, `detail`, and an exit code when a child ran). Successful
managed writes also report a transaction ID. Diagnostics and bounded hook output
go to stderr. Human views use Dots presentation and delayed progress; set
`DOTS_PROGRESS=never` to suppress animation. No Gum/FZF dependency is required.

Doctor inspects hook syntax, publication data, dependencies and app write plans;
it does not execute hooks, create state, or recover transactions. Missing optional
apps are availability warnings; malformed selections, ambiguous names, syntax
errors and unsafe/drifted managed targets return failure. Custom hook dependencies
cannot be inferred: the hook must check its own requirements.

## Selection and discovery

- Selection: `${XDG_CONFIG_HOME:-$HOME/.config}/dots/theme-plugins.json`.
- Custom hooks: `${XDG_CONFIG_HOME:-$HOME/.config}/dots/hooks/theme-set.d/`.
- Bundled scripts: `lib/dots/themes/plugins/` in the Dots source checkout.
- Execution lock and app ownership receipts:
  `${XDG_STATE_HOME:-$HOME/.local/state}/dots/theme-plugins/`.

The selection file is schema 1 with an `enabled` object mapping logical names to
`bundled/FILENAME` or `user/FILENAME`. Prefer enable/disable over hand editing.
Those commands serialize updates and atomically publish the file. Scripts are
never renamed, copied, or deleted by selection changes.

Hook filenames match `NUMBER-name.sh`, where name begins with a lowercase letter
and continues with lowercase letters, digits or hyphens. The CLI name excludes
the number and `.sh`. Order is numeric prefix, then filename (so `2-early.sh`
precedes `10-later.sh`). Files need read permission, not executable permission.
Hooks and their parent directories must not be symlinks; special files are refused.
Roots may contain spaces or Unicode, but must be absolute and exclude controls.

Duplicate logical names, including collisions with bundled plugins, are errors.
An enabled file that disappears is reported, not forgotten. Disable it before
renaming; a different filename does not inherit approval. Editing an already
enabled trusted file keeps it enabled. This is a trusted-file convention, not
protection against a malicious user concurrently replacing their own files.

Downloaded themes are **data only**. Dots never discovers hooks in a theme source,
theme download, or generation, and never executes `colors.toml` or template code.

## Publication and failures

New generations run enabled plugins once after the publisher has committed its
palette, pointer and existing fixed connectors. This includes `dots theme set`
and `anodize apply`. An unchanged set/apply remains a no-op. Explicit
`dots theme refresh` retries plugins even when the generation is unchanged.

No hook runs during a failed publication, preview, dry-run, listing, doctor,
help, completion, or Anodize create/edit/save/export. Existing Fish/FZF, tmux,
Kitty, Termux, btop, bat and Yazi paths retain their existing owners.

Manual runs use the current committed generation at
`${XDG_STATE_HOME:-$HOME/.local/state}/dots/current/theme`. The publisher's
nonblocking lock pins it throughout execution. Manual runs acquire that lock
before the plugin lock; automatic runs retain the publisher lock after commit.
Enable/disable acquire only the plugin lock. Conflicting mutations fail with
retry guidance rather than waiting. Read-only Dots commands remain lock-free.

Each hook runs in a separate noninteractive Bash process, with stdin closed,
working directory `$HOME`, and no inherited lock descriptors. `BASH_ENV`, `ENV`
and exported Bash functions are removed. Exit 0 means success, 77 means skipped,
and other statuses mean failure. Later hooks still run after an individual
failure. At most 16 KiB of each hook's combined output is retained in memory for
diagnostics; output/environment are not persisted as logs.

Manual run returns 1 if any hook fails (skips succeed). An automatic failure warns
that the theme remains published and points to `dots theme plugins run` or
`dots theme refresh`. Existing reload-failure and explicit wallpaper-failure
semantics remain unchanged. Interrupting a run stops its owned child process
group and releases locks; detached processes are outside that cleanup guarantee.
An interruption can leave hooks unrun or partially applied. Retrying reruns the
selected hooks, including earlier successes; custom hooks should be idempotent.

A recursion marker refuses plugin-triggered theme publication, plugin runs and
enable/disable changes. Hooks may call read-only commands such as
`dots theme current` or `dots theme plugins list`. This guard is not a sandbox:
trusted code could deliberately unset it or bypass Dots entirely.

**Custom hooks run with your privileges.** Arbitrary external effects are not
sandboxed, journaled, or automatically reversible. They run outside the core
publication transaction; Dots never claims theme rollback reverses those effects.
Use a bundled managed adapter for Dots-owned application writes.

## Hook authoring and palette mapping

```bash
# ~/.config/dots/hooks/theme-set.d/30-local-preview.sh
command -v my-local-preview >/dev/null || exit 77
my-local-preview --background "$primary_background" --palette "$DOTS_THEME_PALETTE"
```

Then explicitly enable it with `dots theme plugins enable local-preview`.
Ordinary inherited environment and PATH remain available, except the Bash startup
injection variables above. The runner adds:

| Variable | Meaning |
| --- | --- |
| `DOTS_THEME_ID`, `DOTS_THEME_MODE` | Published identity and `light`/`dark` mode |
| `DOTS_THEME_DIR` | Pinned immutable generation directory; do not write here |
| `DOTS_THEME_PALETTE` | That generation's `palette.json` |
| `DOTS_THEME_CURRENT` | Stable published theme path |
| `DOTS_THEME_PLUGIN` | Logical plugin name |
| `DOTS_THEME_REASON` | `set`, `refresh`, or `manual` |
| `DOTS_THEME_PLUGIN_RUNNING` | Recursion guard; leave it set |

Colors come from the existing normalized `colors` map, not application configs.
The following source-compatible names contain lowercase six-digit hex **without
`#`**:

| Compatibility name | Published normalized color |
| --- | --- |
| `primary_background`, `primary_foreground` | `background`, `foreground` |
| `cursor_color` | `cursor` |
| `selection_background`, `selection_foreground` | Same-named colors |
| `normal_black`, `normal_red`, `normal_green`, `normal_yellow`, `normal_blue`, `normal_magenta`, `normal_cyan`, `normal_white` | `color0` through `color7`, respectively |
| Corresponding `bright_*` names | `color8` through `color15`, respectively |

Each also has an `rgb_` counterpart, such as `rgb_primary_background`, formatted
as decimal `r, g, b` (including spaces). No upstream runtime sourcing is needed.
This compatibility covers color variables, not upstream notification, shade,
installer or Omarchy helper functions.

## Bundled integrations

### GTK 3: `gtk`

Selected because Dots tracks GTK 3 settings using an Oomox theme. Requires
`gtk-launch` and an existing `gtk-3.0` config directory. Copies the generated
named-color CSS to `gtk-3.0/dots-theme.css` and inserts a single marked import in
`gtk.css`, preserving other CSS. Existing font, icon, cursor and theme selection
settings remain intact. Oomox/GTK themes consuming those names can use the palette;
styles hardcoding colors may not. This is GTK 3 support, not a GTK 4/libadwaita
styling guarantee. Restart affected apps as needed; no desktop setting or process
is changed. See [GTK user CSS](https://docs.gtk.org/gtk3/class.CssProvider.html) and
[named colors](https://docs.gtk.org/gtk3/css-overview.html).

### Qt6ct: `qt6ct`

Selected because Dots tracks Qt6ct color schemes. Requires `qt6ct` and an existing
`qt6ct` config directory. Copies the generated scheme to `qt6ct/colors/dots.conf`
and changes only `[Appearance]`'s `custom_palette` and `color_scheme_path` keys.
Other settings/comments remain intact; ambiguous duplicate sections/keys refuse
the operation. The palette includes QPalette roles 0–21, including Accent, and
uses muted foregrounds for disabled controls.

Your desktop session must select Qt6ct (normally `QT_QPA_PLATFORMTHEME=qt6ct`);
doctor reports when that variable is absent. Dots does not change the session or
restart apps. See [QPalette roles](https://doc.qt.io/qt-6/qpalette.html) and the
[Qt6ct reader](https://github.com/trialuser02/qt6ct/blob/master/src/qt6ct-common/qt6ct.cpp).

### Managed-write guarantees

Both adapters render through the existing template system and install **copies**,
not links to the moving current pointer. Disabling therefore leaves app output
fixed. All target changes and ownership receipts use the existing file Store:
complete preflight, digest guards, retained backups, journaled atomic replacement,
reverse rollback, interrupted recovery and drift-aware undo. An identical run
creates no new transaction or app writes.

Unrelated changes outside the managed import/Qt keys survive later runs. Changes
to generated output or managed registration refuse replacement. Unknown generated
files, symlink targets/parents and special files require manual review. Receipts
do not authorize following links back into tracked source directories.

Successful writes report transaction IDs. Use `dots files history`,
`dots files undo ID --dry-run`, and the existing confirmed undo/recover workflows
for deliberate restoration. Disable first if restoration should persist across
future theme publications. Undo compares installed objects and refuses drift;
custom hooks have no corresponding undo guarantee. See [managed files](files.md).

## Provenance and limits

Inspired by the locally inspected Theme Hook Plugin Manager at revision
`d244119418cc8bc02c04abc803f0c6d346bfa0ed`. Its `thpm run` delegates to Omarchy;
Dots owns execution itself. No license grant was found in that reference checkout,
so this implementation and its templates were independently authored without
substantial source copying. See [provenance](../lib/dots/themes/plugins/SOURCE.md).

Bundled updates arrive with normal Dots source updates. Remote plugin installation,
self-update, upstream uninstall behavior and automatic restoration on disable
are not implemented. Runtime execution targets the existing POSIX Linux/WSL/Termux
architecture; native Windows execution is deferred. Desktop appearance requires
separate live acceptance; fixture tests do not establish it.
