# Platform profiles and shell startup

Dots keeps universal configuration in the root `config`, `bin`, `scripts`,
`shells`, `lib`, and documentation trees. Platform-specific resources live in
`profiles/termux`, `profiles/windows`, `profiles/linux`, and `profiles/wsl`.
A profile may contain `config`, `bin`, `scripts`, `lib`, `shells`, `docs`, and
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
`${PROFILE}` means the declaring profile directory. They do not execute shell
code. Explicit nonempty environment values win over defaults. Checkout identity
paths remain owned by the selected checkout. Bash/Zsh track assignments so a
reload can update a previous default without overwriting a later user override.

A profile's `.dots/files.json` uses the existing catalog schema and explicit
resource `replaces` declarations. Replacing a whole application directory must
use an explicit directory mapping; there is no automatic file-format or tree
merge. Installation, backups and undo stay in the managed-files workflow.
Windows destinations remain native app mappings, separately from WSL state.
When an app reads an explicit environment path, declare the matching profile
environment override alongside its catalog mapping.

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
