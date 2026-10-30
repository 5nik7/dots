# Platform profiles and shell startup

Dots keeps universal configuration in the root `config`, `bin`, `scripts`,
`shells`, `lib`, and documentation trees. Platform-specific resources live in
`profiles/termux`, `profiles/windows`, `profiles/linux`, and `profiles/wsl`.
A profile may contain `config`, `bin`, `scripts`, `lib`, `shells`, `docs`, `fonts`, and
`skills`; only populated directories are needed.

## Inspect the current context

```sh
dots profile
dots profiles
dots profile --json
dots env
dots env BAT_CONFIG_PATH
dots env --json
```

`profile` explains the detected execution platform, distro, architecture,
runtime, and active inheritance layers. `profiles` lists definitions in this
checkout. Both are read-only. Inspection does not install applications, switch
platforms, execute profile hooks, or initialize optional sources.

The canonical platforms are `termux`, `linux`, `wsl`, and `windows`. Native
Windows takes precedence over inherited Unix environment markers. Termux uses
its prefix evidence; WSL uses Linux kernel/environment evidence. Distro IDs and
families come from literal `os-release` fields. MSYS/Cygwin are reported as
Windows runtimes; this does not establish full Git Bash/Cygwin support or
translate Windows and WSL paths. MSYS/Cygwin setup is refused; use native
Windows Python for Windows installation.

## Definitions and inheritance

Each populated profile has a literal `profile.json`:

```json
{
  "schema": 1,
  "id": "linux/ubuntu",
  "description": "Ubuntu-specific overrides",
  "extends": ["linux/debian"],
  "environment": {"EXAMPLE_CONFIG": "${PROFILE}/config/example"},
  "path": ["bin", "scripts"],
  "replaces_commands": []
}
```

This example requires an existing `linux/debian` definition. Distro definitions
live at `profiles/linux/distros/ubuntu/profile.json`, using IDs such as
`linux/ubuntu`. No placeholder distro directories are shipped.

Linux resolves universal defaults, its platform layer, then an exact distro
layer or the first available `ID_LIKE` family layer. Explicit `extends` parents
load before their child. WSL applies the Linux layers first, then WSL and its
matching distro/family layer. Termux and native Windows use their own layers.
Invalid identities, missing parents, cycles and paths escaping a profile fail
validation. Unknown distros retain their detected identity and use available
base definitions.

Full Bash/Zsh startup sources existing `shells/init.bash` or `shells/init.zsh`
from active profiles in inheritance order. These are trusted hooks whose exported
changes are tracked; lightweight `dots init` does not execute them.

Environment declarations contain literal strings with `${NAME}` references;
`${PROFILE}` means the active profile directory. Generated profile paths are resolved before application templates. They do not execute shell
code. Explicit nonempty environment values win over defaults. Checkout identity
paths remain owned by the selected checkout. Bash/Zsh track assignments so a
reload can update a previous default without overwriting a later user override.

The `LESS=--mouse` application default merges mouse support with inherited pager options, such as batpipe's `-R`, instead of replacing them or being suppressed by them. Existing mouse options are preserved. A different profile default for `LESS` retains the ordinary precedence rule; see [less mouse support](shell-environment.md#global-less-mouse-support).

A profile's `profile.json` stores `settings` and `files` alongside `environment`.
The `files` object maps repository IDs to complete resource lists using profile implementation fields and explicit resource `replaces` declarations. Replacing a whole application directory must
use an explicit directory mapping; there is no automatic file-format or tree
merge. Installation, backups and undo stay in the managed-files workflow.
Windows destinations remain native app mappings, separately from WSL state.
When an app reads an explicit environment path, declare the matching profile
environment override alongside its catalog mapping.

## Generated profile paths

The backend generates `$PROFILE` for the active profile, plus `$PROFILEBIN`,
`$PROFILECONFIG`/`$PROFILECONFIGS`, `$PROFILESCRIPTS`, `$PROFILELIB`,
`$PROFILEFONTS`, `$PROFILESHELLS`, `$PROFILEDOCS` and `$PROFILESKILLS`.
These standard values exist even when their directories do not. Other visible
immediate directories add names; nested and hidden directories do not. Generation
creates no directories and adds no inactive profile paths to PATH. Shared
`SHELLS` and application `DOCS` keep their existing meanings.

The shared backend also exports `DOTFONTS` as `<checkout>/fonts` in every shell adapter. It is a generated path, not an application environment override; profiles cannot redefine it. `PROFILEFONTS`, canonical profile names and alias `*FONTS` values point at their respective profile directories. These values create no directories. The [fonts directory workflow](fonts.md#store-versions-in-a-dots-directory) resolves these names directly from the backend, so a literal `--directory DOTFONTS` also works before shell reload.

Every declared profile also has a canonical namespace, including inactive and
distro profiles: `DOTSWSL`, `DOTSWSLBIN`, `DOTSWINDOWSCONFIGS`, or
`DOTSLINUX_UBUNTUBIN`. Non-alphanumeric characters become underscores. Directory
keys use lowercase, scalar suffixes uppercase. Name collisions fail validation.

An optional non-inherited `alias` adds another prefix and map. Termux ships with
`DROIDOTS`, Windows with `WINDOTS`. The canonical namespace remains available.

```sh
dots config get profile.alias --profile windows
dots config set profile.alias WINDOTS --profile windows
dots config unset profile.alias --profile windows
dots env PROFILEBIN
dots profile env windows
```

Edit the same option under Profile in the config popup. Unset removes only the
alias. Alias values must be shell identifiers; names that collide with generated
paths, reserved shell variables or maps are rejected before saving.

| Shell | Active bin | Named profile | Alias |
| --- | --- | --- | --- |
| Bash/Zsh | `${profile[bin]}` | `${wsl[bin]}` | `${windots[configs]}` |
| PowerShell | `$DotsProfile.bin` | `$wsl.bin` | `$windots.configs` |
| Xonsh | `profile['bin']` | `wsl['bin']` | `windots['configs']` |
| Nushell | `$env.profile_map.bin` | `$env.wsl_map.bin` | `$env.windots_map.configs` |
| Fish | `$profile_bin` | `$wsl_bin` | `$windots_configs` |

PowerShell's built-in `$PROFILE` is preserved; use `$env:PROFILE` for the generated
scalar. Maps are native shell values, not portable exported arrays. Generated
scalars are authoritative checkout paths; `environment` is for application
variables such as `EDITOR` or `APP_CONFIG`, not Dots path declarations.

Profile `.env` files are removed. Compatibility exports `DROIDBIN`, `DROIDCONFIGS`,
`DROIDSHELLS`, `DROIDZSH`, `DOTERMUX`, `WINDOTFILES`, `WINDOWCONFIG`, `RAINMETER`
and the `droid`/`windot` maps are generated centrally. Personal Zsh navigation
aliases and `zsh[local]` remain in profile hooks. Reload removes obsolete generated
names and rebuilds maps. Startup caches include every profile manifest and shallow
directory inventory; warm Bash/Zsh/Fish startup uses metadata guards without
Python or directory scans. Failed generation leaves the prior profile environment.

## Profile configuration

`dots config` edits configuration in the selected checkout. The detected profile is the default; `--profile ID` selects a definition for inspection or editing without activating it. Configuration belongs to that profile, including on native Windows. Runtime state, generated themes and installation receipts retain their existing platform state directories.

```sh
dots config
dots config path
dots config set DOTS_INIT_THEME 0
dots config get DOTS_INIT_THEME
dots config set settings.files.backup true
dots config set environment.EDITOR nvim
dots config unset environment.EDITOR
dots config check
dots config list --profile windows --json
```

Bare `dots config` browses in a terminal and lists when redirected. Use explicit `list` for a noninteractive report. `get KEY` prints an undecorated scalar, or a styled report for a structured value; `--json` selects structured output. `list` and `get` merge configured values from the active inheritance layers; they do not substitute process overrides or built-in defaults. Use `dots env` for effective settings and their origins. `path [NAME]` prints the destination inside the selected profile; `path themes` retains the user theme directory. Every route accepts `--json` and `--profile`.

`set KEY VALUE` and `unset KEY` save immediately through a retained file transaction. Both accept `--dry-run`; `set --json-value` parses the value as JSON. Bare `DOTS_*` names select `settings`; explicit names use `settings.NAME`, `environment.NAME`, `files.REPOSITORY`, or `profile.alias`. Shell settings use their existing string values (`0`/`1`, for example); `settings.files.backup` is a JSON boolean. Environment strings remain literal templates. Sensitive declarations must reference an environment variable, and their values are redacted in inspection. An unset removes only the selected profile's override and can reveal an inherited value. Saving does not reload shells, install files, publish themes, or run hooks.

### Configuration popup

Run `dots config` in a terminal, `dots config browse --query icons`, or choose Config
in `dots menu`. `--profile ID` opens another profile without activating it;
`--defaults` limits editing to shared colors and icons. In tmux, FZF owns the
popup on the initiating client. Elsewhere it uses the current terminal, including
native Windows. An unavailable FZF or preview shell produces a report instead.
`--client CLIENT` is for a launcher with explicit originating tmux context.

Enter opens Edit, Reset override and Details. Alt-G changes the category, Alt-S
changes profile/default scope, Alt-N adds an environment declaration, and F1 shows
help. Each scope/category retains its search and selected row. Escape goes back;
Ctrl-C exits with status 130. Colors offer palette roles or custom hex values;
booleans and enumerations use typed choices. Icons accept literal strings,
including an empty string. Application overrides use the supported visual consumers.
Text input uses optional Gum; its readline fallback also accepts `/cancel` to go back.

The preview distinguishes the saved value and its source from process overrides.
Built-in setting defaults appear in the browser (`files.backup` defaults to false); explicit `list`/`get` retain their
configured-values-only contract. Environment references stay literal, and sensitive
values stay redacted. Enter a variable reference when replacing a sensitive value.

Each change reviews the old value, new value and write destination. Cancel is the
default; Save applies that exact guarded plan, reports its undo command, and returns
to the same row. Reset removes only the selected profile override and previews the
inherited result. Shared defaults remain set-only. A file changed during review
requires a fresh review. Saving does not activate a profile or publish a theme.

File rows show source, destination template, strategy and ownership. The active
profile can open the existing mapping editor or file browser; those workflows keep
their own review and approval. Other profiles expose mapping details only.
`dots config browse --json` returns the same configuration document as `list --json`.

### Manifest fields

The additive schema-1 fields look like this:

```json
{
  "schema": 1,
  "id": "linux",
  "settings": {"DOTS_INIT_THEME": "0", "files.backup": true},
  "environment": {"EDITOR": "nvim"},
  "files": {
    "dots": [{
      "id": "example", "source": "config/example", "target": "${CONFIG}/example",
      "strategy": "link", "app": "example", "category": "config"
    }]
  }
}
```

This is a format example: the source must exist before installation and `dots:example` must be registered in the core `.dots/files.json`. Each `files.REPOSITORY` value replaces that repository's entire inherited resource list. Source paths remain relative to the owner in `.dots/sources.json`. The most specific list wins. The core registry always retains qualified resource IDs and platform eligibility; profiles own implementation details and a single target, without `platforms` or `targets`. An empty or absent effective list installs nothing for that owner. Independent sources such as Neovim have explicit profile mappings; legacy source catalogs remain readable in older schema-1 compositions. File editors save into the active leaf profile. `files edit --platform windows` explicitly edits the Windows base profile; live apply requires the active profile. Registry and profile changes are guarded and journaled together, including tracking.

Format-specific configuration lives beside `profile.json`: `file-colors.toml`, `git.conf`, `theme-plugins.json`, `hooks/`, `file-colors/`, `themed/`, `backgrounds/`, and `projects.json`. Readers choose the most specific existing profile input, then fall back to the legacy Dots config directory. File-style and plugin-selection edits write the current profile. These inherited files are selected as a whole; parent and child documents are not recursively merged. The visual preference files `icons.toml` and `colors.toml` use per-key inheritance as described below. The files retain their existing format-specific validation. `themes/` continues under the platform user configuration directory.

### Migrate existing configuration

```sh
dots config migrate
dots config migrate --apply --yes
```

Migration is a read-only preview by default. It moves configuration from `${XDG_CONFIG_HOME:-~/.config}/dots` on POSIX, or `%APPDATA%/dots` on native Windows unless XDG is explicit, to the selected profile. It incorporates `config.env` into `settings` and `files.json`'s backup preference into `settings.files.backup`. All other configuration files/directories keep their names. `themes`, runtime `state`, `cache`, `logs`, `transactions`, and `backups` stay in place. No theme publication or plugin execution occurs.

Conflicting destinations/settings, links, special files and suspected credentials are refused before mutation. Matching destination content is retained. Apply uses the captured plan, complete preflight, retained copies, reverse rollback and drift-aware undo through `dots files undo TRANSACTION`. A second unchanged migration is a no-op. Preview and apply are separate invocations, so apply rechecks the current configuration and prints its result; `--apply --yes` explicitly authorizes the migration observed by that invocation. No automatic startup migration, commit or publication occurs.

Existing profile `bin` and `scripts` directories contribute to PATH, with more
specific layers first. Completion directories, docs, libraries and skills do
not become executable paths. Skills and documentation are available at their
profile paths; detection does not rewrite an agent's configuration.

Profile `bin` directories also supply `dots-*` commands. Duplicate routes fail
unless the higher-priority profile declares the route in `replaces_commands`.
Core reserved commands cannot be replaced. Initialized Bash/Zsh sessions export
the resolved command directories for direct dispatch; reload startup after
changing profile definitions. Read-only profile inspection resolves fresh facts.

## Environment reporting

The application registry has `defaults` (literal default templates) and
`observed` (known runtime export owners) sections. Runtime-only exports are
reported only when inherited; owner metadata does not claim activation.

`dots env` reports settings, checkout paths, detected context, application
defaults, inherited theme/tool exports, registered PATH contributions, and
changes observed around Dots-invoked initialization hooks. It shows provenance
and whether an inherited value matches the resolved value. It does not dump
unrelated process variables or rerun hooks.

Bash/Zsh hook records contain names, provenance, sensitivity and set/unset
status. Private-hook values and sensitive names are redacted in human, JSON and
scalar output. Values are never stored in bundle manifests. Hook evidence is
limited to observed exported variables; a child command cannot inspect
unexported parent-shell state. Later changes outside tracked hooks may change
inherited values without supplying new provenance.

`--json` retains version 1 and the `values` map with `value` and `source`, adding
metadata and platform/profile/PATH information. A named JSON query returns only
its selected value record. Scalar output remains undecorated; redirected lists
retain `NAME=value [source]` lines. Human paths may abbreviate the home directory.

## Native startup bundles

`dots init` remains lightweight Dots integration. Repository Bash/Zsh rc files
load the full personal configuration: functions, aliases, prompts, completions,
tools and existing plugin integrations.

Python prepares a Bash/Zsh bundle on first use or after known inputs change.
Warm startup checks source metadata and sources native code, without invoking
Python. The cache lives under `${XDG_CACHE_HOME:-~/.cache}/dots/startup`.
Immutable generations and an atomic current pointer prevent readers from seeing
a partially published bundle. Changes to known sources, profile definitions,
profile directories, checkout identity and shell version trigger preparation.
Settings remain literal runtime inputs, so changing settings does not bake
caller values into the cache. No whole-checkout scan or prompt-time rebuild is
performed. Generated theme files and third-party plugin/tool caches keep their
own lifecycle.

PowerShell and Fish prepare smaller native environment adapters. Nushell reads
inert environment JSON through Python, and Xonsh uses its Python runtime. No
adapter requires Bash on native Windows. Missing preparation prerequisites or
unwritable storage leave minimal integration available and report the limitation.

## Missing-checkout bootstrap

Generate a startup snippet for the shell that will receive it:

```sh
dots init --bootstrap bash
dots init --bootstrap zsh
dots init --bootstrap powershell
```

Generation prints code and makes no installation changes. Keep the emitted code
in a regular file outside the checkout if it must survive checkout removal; a
startup symlink into a missing checkout cannot bootstrap itself. Place the resulting
snippet in the shell's startup file through an explicit edit or managed-file
installation. When run, it loads an existing checkout or acquires a missing
checkout using installed Git and Python. Defaults are `~/dots`, the public
HTTPS `5nik7/dots` repository, and branch `main`.

`DOTS_BOOTSTRAP_DIR`, `DOTS_BOOTSTRAP_SOURCE`, and `DOTS_BOOTSTRAP_REF` customize
those choices. Sources may be HTTPS or a local repository and must not embed
credentials. Fetches are bounded and noninteractive. Existing destinations are
never reset or updated. No packages, application configuration, secrets or
recursive submodules are installed.

Acquisition uses a sibling staging directory, a process lock and a durable
status journal. Linux/Termux use an atomic no-replace rename; native Windows uses
its no-replace rename behavior. Failed/interrupted staging remains available for
inspection. Existing occupied destinations are refused. Unsupported acquisition
platforms leave the shell usable instead of guessing filesystem semantics.

## Androidots and Windots migration

Their tracked sources now live in `profiles/termux` and `profiles/windows`.
The `androidots` and `windots` root paths are temporary compatibility links.
File source IDs are `termux` and `windows`; resources use `termux:NAME` and
`windows:NAME`. `--repo` and `--with-source` use those names too. Old CLI names
are rejected with a replacement hint. The bundled profiles need no separate
repository acquisition. Legacy catalog and receipt IDs are recognized internally
so ownership, original backups, drift checks and recovery still work. Inspection
does not rewrite stored records; a subsequent journaled operation may persist
canonical IDs. Historical journals retain their original data.

Rainmeter remains an optional pinned submodule at
`profiles/windows/rainmeter/5ui7e`. Other optional/private submodules are unchanged.
History recovery bundles and the original working trees were archived outside
Git before removing the two platform gitlinks. The migration does not install
new live links, change themes, or rewrite Git history.

Native Termux Bash/Zsh checks and portable fixtures are distinct from native
Linux, WSL and Windows PowerShell 5.1/7 acceptance. Native desktop acceptance is
pending where those systems are unavailable.

The bootstrap source/ref must contain this startup layout. Generating a snippet
from an uncommitted checkout does not publish these files to its default remote.

## Profile inspection subcommands

Bare `dots profile` remains the current-context summary; bare `dots profiles`
remains the list. The following routes are read-only:

| Route | Purpose |
| --- | --- |
| `profile show [ID]` | Definition, resolved layers and source directories |
| `profile layers [ID]` | Ordered layers and inclusion reasons |
| `profile paths [ID]` | Directories, existence and executable PATH order |
| `profile env [ID]` | Literal declaration templates and winning origins |
| `profile files [ID]` | Catalog resources, source paths and target templates |
| `profile commands [ID]` | Command contributions and replacement precedence |
| `profile check [ID]` | Definition, dependency, catalog and command validation |
| `profiles list` | Available definitions; filter with `--platform` or `--active` |
| `profiles check` | Independent validation results for all definitions |

All routes accept `--json` and `--verbose` (`-v`). An explicit ID selects only an
inspection context. It does not activate a profile, change detection, execute its
hooks, or interpret foreign target templates as installed destinations.

`paths --kind` accepts `config`, `bin`, `scripts`, `lib`, `shells`, `docs`, `skills`,
or `path` (existing executable-path contributions in precedence order).
`--existing` hides absent directories. `--kind KIND --raw` emits absolute paths
one per line, without decoration; it excludes `--json`. `env --all` includes
superseded declarations. Use `dots env` for effective inherited values, rather
than treating profile declarations as proof of activation.

Validation reports inactive errors independently, including dependency failures.
Catalog replacements follow the existing managed-files contract: optional missing
replacement resources are allowed, while conflicting active mappings fail.
Missing optional directories are informational. Profiles cannot declare reserved
checkout/platform identity variables. Inspection success returns 0, validation
failures return 1, and invalid invocations return 2.

For startup sequence, timing, PATH and command diagnostics, see
[debugging Dots](debug.md).

## Icons and semantic colors

`default/icons.toml` and `default/colors.toml` hold shared visual defaults. Every base profile has `icons.toml` and `colors.toml` beside `profile.json`; empty files inherit defaults. Resolution merges individual keys in shared-default, inherited-parent, selected-profile order. `unset` removes a profile override and exposes its inherited value. Shared defaults remain defined and are changed with `set --defaults`.

```sh
dots config get files.termux
dots config get files.termux --json
dots config get icons.git
dots config set icons.git.branch ''
dots config set colors.ui.heading.fg cyan
dots config set colors.ui.heading.bold false
dots config set colors.apps.tmux.ui.accent.fg blue
dots config set icons.apps.yazi.git.branch 'git'
dots config unset icons.apps.yazi.git.branch
dots config get icons --defaults
dots config set colors.ui.muted.fg muted --defaults
dots config path icons --profile windows
```

The literal TOML subset accepts named tables, quoted strings, booleans and comments. Icons may be empty and contain up to 64 printable characters; terminal controls are rejected. Color fields are `fg`, `bg`, and boolean `bold`, `dim`, `italic`, `underline`, `reverse`, `strikethrough`. Foregrounds/backgrounds select semantic palette roles or `#RRGGBB`; they never execute shell or template code. Shared UI roles are `ui.heading`, `ui.label`, `ui.identity`, `ui.accent`, `ui.foreground`, `ui.muted`, `ui.selection`; status roles include info, success, warning, error, working and waiting. CLI uses terminal-palette fallbacks until a palette is published. `dots config check` validates both preference files and the profile catalog.

The `apps` namespace provides overrides for `cli`, `tmux`, `yazi`, `fzf`, `gum`, `starship`, and `gitmux`. CLI renderers support foreground/background and attributes. Native consumers use their supported fields: generated color templates use fg/bg, Gitmux/Starship use Git symbols, and Yazi uses file/Git symbols. File and Git color rules remain in `file-colors.toml`; palette definitions and exact palette swatches retain their existing owners.

| Consumer | Preference binding | When changes appear |
| --- | --- | --- |
| Dots human reports, resources, Git, Todo, menus, keys, weather detail icons and Bash utility presentation | Shared UI/status/file/Git/navigation roles; `apps.cli` overrides | Next command invocation |
| FZF and Gum templates | UI/status fg/bg, with their app overrides | Explicit theme publication/refresh and normal shell palette refresh |
| tmux and Termux activity | UI/status fg/bg and working/waiting/Codex icons | Explicit theme publication/refresh and existing reload path |
| Gitmux adapter | Git symbols in generated config; existing Git color roles | Published generation used by next status read |
| Yazi generated flavor and Dots plugin | File icons and Git symbols; existing file/Git colors | Explicit theme refresh |
| Opted-in Starship/Blastoff theme plugin | Existing Git symbol fields, shared palette | Explicit theme refresh/plugin run |

The scan separates these owned consumer bindings from imported presets, third-party code and authored artwork. Application-specific fields outside the bindings retain their native configuration owners (for example Fastfetch preset graphics and weather condition tables). Bootstrap errors before Python is available retain dependency-free fallback styling. Existing Bash-only utilities (`bak`, `remove`, `fzcmd`, `fzenv`, `fzfig`) use shared presentation aliases; their execution/platform scope is unchanged. Read-only reports never generate files, run hooks or activate consumers.

Configuration edits use retained file transactions: `--dry-run` previews, results include the transaction ID, and `dots files undo ID` detects later edits before restoring. Shell bundles fingerprint preference inputs and still avoid Python on their warm path. Generated `preferences.json`, native fragments, and `colors.json`/`colors.lua` are completed before publication; changing a preference cannot publish them implicitly. Native Windows uses the same resolver and CLI controller; native terminal/application acceptance is separate from local fixtures.
