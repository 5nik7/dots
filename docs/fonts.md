# Personal fonts

`dots fonts` and standalone `fonts` share a Python controller for per-user font
management. They work from the Bash and native PowerShell frontends. Font parsing
requires Python 3.11+ and `fontTools`; install the dependencies in your chosen
Python environment with `python -m pip install -r tools/requirements-fonts.txt`.
Help, inventory, completion and metadata browsing do not require fontTools.
Dots setup includes the standalone command adapter; it does not install fonts or
Python packages. Native Windows runtime and application acceptance remain pending.

## Find and save fonts

The main Fonts popup includes **Configuration** for display, preview and shared
layout controls. The catalog and glyph pickers also open it with **Alt-O**;
`dots menu` → Fonts → Font configuration opens the matching Config entries.

Human reports, help, reviews and errors use Dots CLI formatting and semantic
styles. All Fonts selectors use shared menu field/icon styles and layout. Catalog
previews wrap at the actual preview-pane width. JSON, exact `path`, single-glyph
formats and ordinary redirected output retain their data/undecorated formats.

### Output preferences

```sh
dots config browse --query apps.fonts
dots config set apps.fonts.list_details full
dots config set apps.fonts.preview.position right
dots config set apps.fonts.preview.size 40
dots config set apps.fonts.preview.sample false
dots config unset apps.fonts.preview.position
```

These controls inherit shared defaults, parent profiles and the current profile.
They apply on the next Fonts command or reopened picker, including after returning
from its Configuration menu. They do not set a font or publish a theme.

| Key under `apps.fonts` | Default | Human consumer |
| --- | --- | --- |
| `list_details` | `summary` | `summary` counts retained faces in list/search/installed/downloaded reports; `full` expands faces and provenance. `show` and previews retain details. |
| `provenance` | `true` | Show provenance in detailed human reports and previews; JSON and redirected output always retain it. |
| `menu_descriptions` | `true` | Show secondary text in nested choices and catalog/glyph rows; labels and selection identities remain available. |
| `preview.enabled` | `true` | Show the catalog/glyph preview pane. |
| `preview.sample` | `true` | Render actual downloaded font samples when optional ImageMagick and Chafa are available; `false` shows metadata only. |
| `preview.position` | `down` | Place the preview below (`down`) or beside (`right`) the list. |
| `preview.size` | `33` | Integer percentage from 10 through 80 of the picker height or width. |
| `preview.wrap` | `true` | Wrap preview text in FZF. |

Use existing `formatting.apps.cli` and `formatting.apps.menu` for indentation,
tab stops, label width/gap and alignment; use `apps.menu.popup` for the shared popup
frame, position, dimensions and colors. Font-specific report style roles are
`colors.fonts.heading`, `label`, `identity`, `version`, `source`, `face` and `glyph`.
Each supports foreground, background and text attributes, inheriting the shared
semantic style until overridden. CLI-scoped overrides use
`colors.apps.cli.fonts.<role>.<field>`. The font icon is `icons.menu.fonts`, with
independent styling in `colors.icons.menu.fonts`. Null/unset resets an override.

Nested choices use shared `colors.menu.*` roles and per-entry
`formatting.apps.menu.entries["fonts:MENU:ENTRY"]` overrides. Examples are
`fonts:Fonts:installed`, `fonts:Actions:show`, `fonts:catalog:nerd:JetBrainsMono`
and `fonts:icons:ICON_NAME`; field suffixes such as `.label.fg` style only that
entry. Display preferences never change the literal command arguments or glyphs.

### Catalogs and downloads

```sh
dots fonts update                       # Explicitly refresh both official catalogs
fonts search JetBrains                  # Search the cached catalogs, offline
fonts download nerd:JetBrainsMono       # Review and save a family with its license
fonts show nerd:JetBrainsMono           # Versions, exact faces and provenance
fonts install nerd:JetBrainsMono --variant mono
fonts list --installed
```

Nerd Fonts comes from [official release archives](https://github.com/ryanoasis/nerd-fonts/releases).
`fonts update --source nerd --version v3.4.0` also catalogs an exact release and its
matching glyph index. A refresh of an older tag does not replace an already known
latest release. Install selects all styles of one `mono`, `nerd` or `propo` variant;
Mono is the initial default when available. Subsequent installs retain the chosen
variant unless explicitly changed.

Google Fonts comes directly from the [Google Fonts repository](https://github.com/google/fonts),
without an API key or whole-repository clone. IDs have the form
`google:ofl/abel`; search also accepts family-name fragments. Download retains the
root family TTF/OTF files, variable fonts in their original form, and licenses.
Records identify an exact repository commit and family-tree fingerprint. Unchanged
family trees do not trigger upgrades just because another family changed upstream.
Custom variable-axis instances and font patching are outside this interface.

Catalog refreshes are explicit. Reads, completion, popup opening and `--dry-run`
do not fetch data. Failed refreshes/downloads retain the last saved catalog/library.
`search --monospace` filters fonts whose downloaded metadata establishes that
property; it does not infer it from an unexamined upstream filename.

## Library and versions

| Command | Effect |
| --- | --- |
| `update` | Refresh catalog metadata and Nerd Fonts glyph indexes. |
| `download FONT` | Save a family/version and licenses without registering it. |
| `import PATH` | Copy regular local TTF/OTF files and licenses; preserve originals. |
| `list`, `show FONT`, `versions FONT` | Inspect the library and known versions. |
| `list --system` | Inspect external fonts through fontconfig or the Windows registry. |
| `export FONT --output NEW_DIRECTORY` | Copy a retained version and its licenses to an unoccupied directory. |
| `install FONT... [--from SOURCE]` | Install retained versions into a Dots directory or register one variant for the current user; missing cataloged versions can be downloaded. |
| `pin FONT --version VERSION`, `unpin FONT` | Prevent or allow version changes and upgrades. |
| `upgrade [FONT]` | Upgrade unpinned installed families and active Termux selections. |
| `rollback FONT --version VERSION` | Install an exact retained version, with the same safety checks. |
| `uninstall FONT` | Remove owned registrations/files, retaining downloaded versions. |
| `remove FONT --version VERSION` | Remove an unused, unpinned retained version. |
| `undo TRANSACTION` | Reverse a fonts transaction after checking for drift. |

Imports use content-derived `local:` identities. Their upstream version is recorded
as unknown; filenames do not establish a Nerd Fonts release. Originals are never
moved or adopted implicitly. Upgrades skip imports without known upstream metadata.
Explicit `--keep-archive` retains a newly downloaded Nerd Fonts ZIP alongside its
extracted files; it does not refetch an already saved version.

An installed family has one version and one variant. Other versions remain in the
library for rollback. Upgrade also updates tracked application selections, requiring
the same family/style for every active face; incompatible replacements are refused.
For a Termux-only selection, upgrade and rollback replace its active face without
adding desktop font registration.
Uninstall refuses active families. Removal refuses installed, migrated, active or pinned
versions, changed payloads and unowned paths. Select another font or undo the Set
transaction before removing an active selection.

## Store versions in a Dots directory

`--directory` selects a backend-owned font directory by name or absolute path. `DOTFONTS` is the checkout's `fonts` directory; `PROFILEFONTS` is the active profile's directory. Canonical names such as `DOTSTERMUXFONTS`, `DOTSLINUXFONTS`, `DOTSWSLFONTS`, `DOTSWINDOWSFONTS` and configured aliases such as `DROIDOTSFONTS`/`WINDOTSFONTS` resolve through the same backend. `fonts directories` lists the current names and paths without creating them. The option accepts literal names in every shell, without requiring an environment reload or evaluating shell expressions. In PowerShell, an expanded path can also be passed as `--directory $env:DOTFONTS`.

```sh
fonts directories
fonts update --source nerd --version v3.4.0
fonts install nerd:JetBrainsMono --version v3.4.0 --directory DOTFONTS --dry-run
fonts install nerd:JetBrainsMono --version v3.4.0 --directory DOTFONTS
fonts versions nerd:JetBrainsMono --directory DOTFONTS
fonts use nerd:JetBrainsMono --version v3.4.0 --variant mono --directory DOTFONTS
fonts current --directory DOTFONTS
```

Directory `install` copies the available faces and licenses from a retained version, or downloads the selected cataloged release. `download` requests the complete cataloged family, expanding a partial copy when its exact source is available. It neither registers fonts nor changes application settings. `import PATH --directory NAME` explicitly copies local fonts into the same store. Existing loose fonts are not imported automatically. Managed payloads live in the directory's Git-ignored `.dots-fonts/library` subtree; originals and unrelated files are left in place.

| With `--directory NAME` | Effect |
| --- | --- |
| `install FONT --version VERSION` | Store that version without activation. Omit the version to use the source pin/installed/preferred version, or the cached latest release when no retained version is available. |
| `update FONT [--version VERSION]` | Store a cataloged update for one unpinned family. Does not refresh catalogs or activate it. |
| `upgrade [FONT]` | Store cached latest versions for unpinned families; preserve older versions. Without FONT, skip families with no remaining stored versions. |
| `use FONT [--version VERSION]` | Copy the version into the personal library and register one variant for this user. |
| `set FONT --target APP` | Copy the version into the personal library and set explicit apps; desktop targets also register the font. A Termux-only target needs no desktop registration. |
| `rollback FONT --version VERSION` | Explicitly activate a retained version, preserving existing active face choices. |
| `uninstall FONT --version VERSION` or `remove FONT --version VERSION` | Remove only this directory's copy of that version; preserve its provenance, checksums and version history. Pinned versions must be unpinned first. |
| `list --installed` or `list --downloaded` | List families with versions currently stored in this directory. Plain `list` also includes uninstalled history. |
| `versions FONT`, `show FONT`, `current` | Inspect stored/cataloged/uninstalled versions, provenance and activation references for this directory. |
| `undo TRANSACTION` | Undo a transaction belonging to this directory, refusing later drift. |

Bare `update` still refreshes shared catalogs. Refresh first when checking for new upstream releases. `pin`/`unpin`, `path` and `export` operate on the selected directory. Choose `--variant` on `use`/`set`, since directory installation copies all available variants. `use --target APP` can combine registration/application selection; all changes are reviewed together. A plain `use` registers the font and updates tracked choices of that family, without selecting a new application target.

Each destination has an independent inventory in the local Dots state store. Removing a directory copy preserves other directory copies and the activated personal-library copy. `current --directory` can therefore report an active version whose directory copy is now uninstalled. Activation always uses the current execution platform: selecting `DOTSWINDOWSFONTS` on Termux is storage in that profile directory, not Windows activation. The local inventory is not a portable manifest: moving the checkout or manually copying `.dots-fonts` does not transfer ownership. Export/import explicitly instead. Default commands without `--directory` retain the personal-library behavior described above.

## Installed fonts and transfers

`fonts installed` includes managed fonts, external user fonts, system fonts and the current Termux font. Stable `installed:` IDs identify paths; ownership and unsupported-format reasons appear in reports. Discovery uses optional fontconfig on Termux/Linux/WSL and native font registrations on Windows. Missing discovery tools produce a notice while managed selections remain available. Discovery never runs during startup or completion.

```sh
fonts installed --json
fonts copy INSTALLED_ID --directory DOTFONTS
fonts migrate INSTALLED_ID --directory PROFILEFONTS
fonts browse --downloaded
fonts install nerd:JetBrainsMono google:ofl/abel --from DOTFONTS --directory PROFILEFONTS
fonts install nerd:JetBrainsMono --from PROFILEFONTS --variant mono
```

Replace `INSTALLED_ID` with a complete ID from the inventory. Copy preserves the installed original. Migrate adopts ordinary user-owned font files only in supported user-font roots (or the current Termux font); protected, linked or uncertain sources are copy-only. POSIX migration leaves a lookup link at the original location. Windows migration requires the matching HKCU registration and preserves its native lookup path. Termux retains its ordinary `font.ttf` copy. Backups and ownership receipts make changes reversible. A later native Install consolidates migrated aliases into the standard Dots installation; Uninstall checks and removes owned aliases, retaining stored versions. Changed aliases are refused.

Downloaded browsing includes all backend stores unless `--directory` limits the scope. Its Install action offers a Dots directory or native user installation. `--from personal` or a backend name/path fixes the source independently of the destination. Without `--from`, lookup searches the personal store then registered Dots stores. Batch install accepts several families and reviews their resolved exact versions in one transaction. Use `--version` with one family only; identical destinations are no-ops and a conflict in any member prevents the whole apply. Individual installed files may likewise be copied or migrated in one batch.

## Set an application font

```sh
fonts targets
fonts set nerd:JetBrainsMono --variant mono --face JetBrainsMonoNerdFontMono-Regular.ttf --target termux
fonts set nerd:JetBrainsMono --target vscode-editor --target vscode-terminal
fonts current
fonts set --file /absolute/path/MyFont.ttf --target termux --no-reload
```

Use the exact face names reported by `show`; upstream filenames can change between
releases. Without `--face`, Set requires an unambiguous regular face. Set downloads an absent cataloged version as needed and includes desktop registration in its reviewed plan. `--target` is required and
repeatable. `--config ABSOLUTE_FILE` selects one explicit unmanaged configuration
for a single desktop target. Dots never searches for an arbitrary file to edit.

| Target | Setting and ownership |
| --- | --- |
| `termux` | Copy a TTF face to this Termux home's `.termux/font.ttf`, retaining the previous file. This does not change Android system fonts. |
| `kitty` | One literal `font_family` setting; retain other options and size. Native Windows is unavailable. |
| `wezterm` | One literal `config.font = wezterm.font(...)` or `font_with_fallback(...)`; preserve fallback entries and other fields. Computed expressions require manual configuration. |
| `windows-terminal` | JSONC `profiles.defaults.font.face`, or one exact GUID selected by `--app-profile`; native Windows only. |
| `vscode-editor` | JSONC `editor.fontFamily`. |
| `vscode-terminal` | JSONC `terminal.integrated.fontFamily`. |

Default desktop destinations come from the active Dots catalog. Managed sources
are edited so linked configurations follow. Managed file copies also require a
matching installation receipt and unchanged target; their copy and receipt are
updated in the same transaction. Copied directories and ambiguous mappings are
refused. Comments, line endings, fallback families, sizes and unrelated fields are
preserved. WSL never edits Windows host settings through path translation.

Every Set (including `use --target`) retains the selected font in the **active profile's** fonts directory. `--directory` on Set selects its source, not the automatic retention destination. Termux retains just the selected TTF plus licenses; desktop apps retain every available style of the selected variant. If a partial upstream family lacks known styles, Set obtains that exact release before applying. Compatible later selections expand the retained version without replacing earlier faces. Switching families or versions preserves prior files, including a valid custom Termux font that existed before the first Set. Conflicting content or an unreadable previous custom font stops the operation for review.

Set also writes `profiles/<active-profile>/fonts.json`, with exact family ID, version, variant, face, required file checksums, application target and any explicit config/profile selection. This is a font-preferences file; it does not adopt missing app configurations. Storage, registration, app edits, preferences and the local collection share one transaction. Upgrades and rollbacks synchronize affected preferences as well.

Re-selecting the same exact font also fills in missing profile retention and preferences for selections made before this feature was added. An already matching active font file is left untouched; repeating the completed Set produces no changes.

```sh
fonts defaults                         # Inspect this profile's saved choices
fonts restore termux --dry-run         # Review one exact saved choice
fonts restore                          # Review all saved choices together
```

Restore never upgrades a saved version. It uses retained copies or the saved official source description to fetch the exact release, checking the saved face hashes. Missing local imports need their original files imported again. Manually copied payload folders remain unowned; Restore does not bypass the collection's ownership rules. No font choice is activated during shell startup or setup. Profile preferences are ordinary repository configuration; large `.dots-fonts` payloads remain Git-ignored unless separately managed by the user.

Termux reload runs after a successful Set/upgrade/undo unless `--no-reload` is given.
Fontconfig refresh and Windows session notification also happen after commit.
Refresh failures are reported separately: the transaction remains recoverable and
applications may need restarting. Native Windows files locked by a running
application cause a guarded failure; close the application and retry.

## Browser and icons

The Dots launcher's Downloaded fonts entry opens `fonts browse --downloaded`. Its availability checks the browse command, independently of the number of retained fonts or network access.

Plain interactive `fonts` opens an action menu: Installed fonts, Set application font, Downloaded fonts, Browse catalogs, Font directories, Current fonts, Saved defaults / Restore, and Icon search. The Dots launcher exposes these workflows too. `fonts set` with no operands opens an app-first chooser; noninteractive Set still requires explicit selection. `fonts --query TEXT` and `fonts browse` keep the catalog browser. `fonts installed --json` / `--print` are read-only inventories.

The catalog browser offers details, version selection and reviewed actions. Use Alt-U to update catalogs, Alt-N to
import, Alt-D to select a directory or the personal library, Alt-L for local records, Alt-S for catalogs, Alt-T for targets and Alt-G
for glyphs. The current storage scope is shown; search, selection and directory survive returning from actions. The Fonts submenu also offers a directory report. Esc goes back;
Ctrl-C cancels. Optional ImageMagick and Chafa render samples from the actual
downloaded font; otherwise the preview clearly identifies metadata-only content.
The glyph preview uses the terminal's current font, which may lack that glyph.

`fonts icons` uses cached release-matched Nerd Fonts glyph metadata. Its default
index matches a single installed Nerd Fonts version, otherwise the last refreshed
index; `--version` chooses explicitly. Enter or Alt-Y copies and closes. Alt-I
inserts a literal glyph into the verified originating tmux pane without sending
Enter. Alt-P prints the glyph and closes. Outside tmux, use copy or print.
Clipboard failures remain visible and leave the browser open. No global keybinding
or shell insertion widget is installed.

For scripts, `fonts icons SEARCH --format glyph|name|codepoint` requires one match
and prints exactly that value without a newline. `--copy`/`--insert` also require
one match. `--json` is schema-1 JSON without decoration; `fonts path FONT --face
FILENAME` prints one absolute font path plus newline. Redirected inventories and
explicit `--print` do not open a browser. FZF is optional; unavailable rich browsing
falls back to readable inventory. Bash, Zsh, Fish and PowerShell completion read
only saved state and static metadata.

## Review and recovery

Mutations show a review and ask for confirmation. Noninteractive mutations require
`--yes`; review with `--dry-run` first. Dry runs can parse local inputs in temporary
staging, but do not change persistent state, refresh caches, reload apps or download.
A download/upgrade dry run identifies the intended remote version; actual payload
and active-face validation precede its eventual apply. Bare `update` refreshes metadata without a second confirmation; `update FONT --directory NAME` reviews the storage change like other mutations.

Library, configuration, registration and collection changes use the shared file
transaction journal with retained backups. Sources, destinations and metadata are
checked again before apply. `undo` refuses drift. Use `dots files history` to find
transaction IDs and `dots files recover ID` for an interrupted transaction. These
commands never silently repair unrelated configuration or remove external fonts.

`getnf` and `chnf` now delegate to this controller. `getnf -i FAMILY[,FAMILY]`
downloads and installs Nerd Fonts; `-f` refreshes the catalog and `-k` retains new
archives. With no `-i`, it opens the Nerd Fonts browser. `chnf -l` lists legacy and
library TTF faces; `-i`, `--font`, `--apply` or a positional query selects a face.
Legacy files under `TERMUX_NF_FONT_DIR` or `$PREFIX/share/termux-nf/fonts` are copied
into the library when selected. `-r` remains accepted; reload now occurs by default
and `--no-reload` skips it. Both wrappers support `--yes`/`--dry-run`; force never
bypasses pins, ownership or confirmation. See [data contracts](specification.md#font-library-and-catalogs)
and [platform acceptance](../plans/fonts.md#evidence).

## Checkout setup integration

The optional Fonts setup component restores exact saved versions, hashes, faces and application targets, or a reviewed retained face. It stages acquisition and combines library retention, native user registration, app edits and metadata with the installer's final transaction. It never reloads applications. Run-only choices retain payloads without replacing profile `fonts.json`; Save choices uses the normal Fonts preference owner. An expected catalog-managed `.termux` link uses a guarded physical destination; arbitrary links remain refused. Selective Fonts uninstall restores unchanged installer-owned app settings and previous selection metadata while retaining font libraries/registrations.
