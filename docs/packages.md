# Package workflows

`pkgs` and `dots pkgs` share the bundled core on Termux, Linux, WSL and native Windows. Native Windows uses WinGet only; Dots never launches WSL.

## Upgrade and scope

Short commands share the same options and safety rules:

| Alias | Command |
| --- | --- |
| `in` | `install` |
| `un` | `uninstall` |
| `up` | `upgrade` |
| `xup` | `export --update` |
| `upls` | `upgrade --list` |

```sh
pkgs upgrade --dry-run
pkgs upgrade
pkgs upgrade --manager npm --global
pkgs upgrade --manager apt ripgrep
pkgs upls
pkgs upgrade ls --manager npm --global
pkgs upgrade --list --json
```

`upgrade ls`, `upgrade --list` and `upls` list available upgrades without
installing or running recipes. They use the same automatic manager scopes and
skip/source/ownership exclusions as bulk upgrade; explicit managers retain their
normal scope. The compact report groups names and current → candidate versions
under each manager, with skip counts and separate query failures. `--list NAME`
filters installed names. To upgrade a package literally named `ls`, use
`pkgs upgrade --manager MANAGER -- ls`.

System queries use existing indexes: APT's upgradable list, Arch's `-Qu`, DNF's
cache-only repoquery and XBPS's read-only `-un` simulation. Language queries use
native npm outdated, pip list --outdated, uv tool list --outdated, gem outdated and
Go module-version queries. These can contact registries and update their metadata
caches, but never install packages or edit project manifests. uv requires a
version supporting `tool list --outdated`; unsupported flags/query failures remain
errors while independent managers continue. Native candidates are informational:
holds, dependency resolution, uv tool constraints and custom recipes can change
what an actual upgrade does. npm reports its `wanted` version, not an unrelated
latest release outside the project's range. Go reads module identity from build
metadata and queries outside the project with automatic toolchain downloads off.
Native query contracts: [npm outdated](https://docs.npmjs.com/cli/v12/commands/npm-outdated/),
[uv tool list](https://docs.astral.sh/uv/reference/cli/#uv-tool-list) and
[XBPS dry-run format](https://man.voidlinux.org/xbps-install.1).

Bare `upgrade` authorizes supported user-wide updates without another pkgs prompt, including without a controlling terminal. It selects one system database, global npm, uv tools, pip-owned base-interpreter distributions, user RubyGems and Go tools. Arch prefers the configured available helper, otherwise paru, yay or pacman, and deduplicates that database. Active Python virtual environments and Bundler projects exclude those languages from automatic selection. pip ownership requires `pip inspect` and a system ownership check when that database is available; unknown/system-owned/source installs are skipped. User RubyGems excludes default and system gems. Language inventories do not discover arbitrary project directories.

Explicit `--manager` restricts the operation; named operands retain selected scope. Explicit npm defaults to the current project unless `--global` is used; explicit pip uses pkgs' interpreter and gem uses its active environment. The configured `upgrade.managers` list restricts automatic selection. System operations precede language operations, preserving order within each group.

Selected global npm upgrades use `npm install --global -- NAME ...`. This updates
the selected packages without `npm update --global` rechecking unrelated installed
platform-specific aliases, such as Codex's Linux ARM64 companion on Android.
Project-scoped upgrades still use `npm update`. Skip policies and replacement
recipes keep their behavior; ordinary npm batches do not receive `--force`.

Native noninteractive flags are supplied where supported. sudo uses `-n` without a controlling terminal and never runs on Termux. Privilege and native package protections may still fail. Independent managers continue after a failure; a failed command stops that manager's remaining recipe. The final status is nonzero if any manager failed. Ctrl-C stops the run. Completed package effects remain; there is no Dots package rollback.

`pkgs refresh` also authorizes its repository metadata refresh without an extra flag or controlling terminal. It supports APT, DNF and XBPS; Arch still requires `upgrade` to synchronize and upgrade together.

An APT “File has unexpected size / Mirror sync in progress” failure means the
downloaded index disagrees with the repository metadata. Compact output identifies
the mirror-sync failure and suggests retrying `pkgs refresh` later, then upgrade.
The command retains the failing exit status and does not disable integrity checks
or silently change repositories. `--raw` retains the full URL and native details.

`pkgs install NAME ...` authorizes installation without `--yes`, including without a controlling terminal. When names are omitted, accepting the install-picker selection authorizes those packages; cancelling installs nothing. Install, upgrade and refresh supply supported native confirmation flags automatically (for example, Termux APT uses `pkg install -y bun`). Native privilege checks, manager protections and custom recipe behavior still apply. Uninstall and restore retain approval prompts; `--yes` approves their intentional noninteractive execution. Dry-run prints plans/skips and executes no mutation commands or recipe hooks, although local inventory queries still run. The upgrade and restore menus review the preview and require an explicit **Run** choice.

## Go tools

`pkgs list --manager go --installed` reads build metadata in `GOBIN`, or the first `GOPATH`'s `bin`, without executing binaries or downloading a toolchain. Install takes a full module package path. Upgrade checks native latest-module versions, then runs one `go install PACKAGE@latest` for each newer eligible tool. Current or newer installed versions are left alone, including prerelease builds ahead of the latest stable release. A module shared by several tools is queried once per plan. Checks use the same comparison as `upls`, outside the working project, with toolchain downloads disabled and bounded query time. Unavailable or malformed metadata fails preparation rather than guessing which tools need updates.

Dry-run performs these read-only checks, which may contact the configured Go
proxy, and prints install commands without executing them. Native build flags
remain literal. Explicit manager/package replacement recipes own their update
behavior and bypass the default version check; they can invoke a helper if desired.
`go-global-update` is no longer chosen automatically. Use an explicit `install`
to reinstall a current tool. Version-suffixed native installs follow
[Go's installation semantics](https://go.dev/ref/mod#go-install).

Development builds, replaced modules, source builds, renamed binaries and duplicate identities are visible but skipped. Symlinks and non-Go files are not owned by the adapter. Go supports installed list/info, install, upgrade, export and restore; registry search and removal are unavailable.

## Configuration and recipes

Native `${XDG_CONFIG_HOME:-~/.config}/pkgs/config.json` is authoritative. Windows uses `%APPDATA%/pkgs/config.json` unless XDG_CONFIG_HOME is set. Changes take effect on the next invocation; the existing `commands` executable-identity map is unchanged.

```json
{
  "upgrade": {"managers": "auto"},
  "output": "auto",
  "policies": {
    "npm": {
      "skip": ["held-package"],
      "install": {"flags": ["--ignore-scripts"]},
      "packages": {
        "my-tool": {
          "upgrade": {
            "before": [["/path/check-tool", "{package}"]],
            "replace": [["/path/update-tool", "{package}"]],
            "after": [["/path/check-tool", "{package}"]]
          }
        }
      }
    }
  }
}
```

`upgrade.managers` accepts `"auto"` or a nonempty unique ordered manager-ID array. `output` accepts `auto`, `styled` or `raw`. Manager policies accept `skip`, `install`/`upgrade` recipes and `packages` overrides. Recipes accept `flags`, `before`, `replace` and `after`. Manager wrappers run once, ordinary targets batch, and package-specific recipes run separately. Replacement substitutes for the native command; overlapping manager/package replacements are rejected. Flags combine manager then package values.

Commands are nonempty literal argv arrays, with no implicit shell evaluation. Whole-token `{packages}` expands selected targets; `{package}` works only in package recipes. Name an interpreter/script explicitly for scripts. Recipes are trusted executable configuration and own their side effects, prompts and status. Reading config, completion, export and dry-run never execute them.

Skips match exact identities (Python names normalize case and `-_.`). Direct install/upgrade/restore targets are excluded. Explicitly naming a skipped package errors unless `--ignore-skip` is supplied; automatic selection/restore reports and omits it. Skips are not dependency holds. Arch bulk operations retain `-Syu` and exclude skipped/custom targets, with custom targets handled separately.

```sh
dots config get apps.pkgs.output
dots config set apps.pkgs.output styled
dots config set apps.pkgs.upgrade.managers '["apt","npm","go"]'
dots config set apps.pkgs.policies.npm '{"skip":["held-package"]}'
dots config unset apps.pkgs.output
```

Dots Config and its Apps popup edit the same file through guarded Store writes, retained backups and undo, preserving unrelated fields. No profile override is created; inactive-profile/shared-default edits are unavailable. Edit per-manager policy objects as JSON so dotted/slashed package names remain literal keys. `config explain` supplies choices and syntax.

For a Termux ARM64 Codex npm installation, a per-package replacement for both
`policies.npm.packages["@openai/codex"].install` and `.upgrade` can use this argv:

```json
{"replace": [["npm", "install", "-g", "--force", "@openai/codex@latest", "@openai/codex-linux-arm64@npm:@openai/codex@linux-arm64"]]}
```

Include `@openai/codex-linux-arm64` in the npm `skip` list: the replacement updates
it alongside the main package, while ordinary npm updates must not treat the
alias as a separately published registry package. Target `@openai/codex` for
explicit install/upgrade. The literal `-g` recipe always targets global npm.
Merge this with existing npm policies through `apps.pkgs.policies.npm`; setting
that key replaces its object. Recipe changes take effect on the next invocation.

## Output

```sh
pkgs upgrade --raw
some-package-command 2>&1 | pkgs format --manager apt
```

`auto` gives actual upgrades a compact terminal/menu view: one heading, transient progress and one result per manager. Commands, repeated download/database/requirement messages and per-package skip lists are omitted. Skips appear as a count; `--dry-run` retains the complete commands, names and reasons. Each manager keeps at most two distinct error details, two warnings and a short fallback tail for unrecognized failures; additional diagnostic lines are counted. Partial prompts remain visible. A `complete` result means the command succeeded, not that a particular number of packages changed. Independent managers still continue after failures.

Compact pip progress shows the current package and resolving, download,
preparation, build and installation stages. With pip 25.1 or newer, native
[raw progress events](https://pip.pypa.io/en/latest/user_guide/#using-pip-from-your-program)
supply actual download bytes and a percentage when the size is known. After
15 seconds without output, `quiet M:SS` shows elapsed silence alongside the last
stage. Silence does not prove a hang, and pkgs does not terminate a slow build.
Only native pip install commands in compact upgrades receive unbuffered Python
output and the raw progress default; explicit `PIP_PROGRESS_BAR` or command-line
progress options remain authoritative. Custom recipes and older pip versions
keep stage/quiet reporting from whatever output they provide.

Compact npm upgrades show the last native metadata, cached/fetched package or
install-script event. `quiet M:SS` appears after 15 seconds without output; a
completed fetch is not a percentage for the whole transaction. The compact
runner requests npm's [info log level](https://docs.npmjs.com/cli/v11/using-npm/logging/#loglevel)
only in its child environment. Explicit `npm_config_loglevel` (case insensitive)
and native CLI logging flags retain precedence. Progress labels omit registry
URLs, credentials and script commands. Native script approval rules remain,
and silence never triggers automatic termination.

Compact Go progress identifies the binary being installed before any native
output arrives, for example `go · Installing · tool`. Download or compiler chatter
does not replace that target with a dependency name. Quiet time appears after
15 seconds without output; the native process may still be building. Full package
paths and literal commands remain available in dry-run and raw output.

`styled` explicitly enables the human view, including when redirected. `raw`/`--raw` retains full commands, skip details and native subprocess bytes. Ordinary redirected output in `auto` also retains its existing full output. Compact logs are not persisted; use `--raw` when full output is wanted. Other operations and the stdin formatter retain full formatted messages. Concurrent stdout/stderr draining and actual process exit status are preserved in every mode. Child terminal settings are restored on exit, and formatted terminal newlines return to the left margin even if a child disables newline translation.

Formatting strips terminal controls and uses shared semantic colors. Preparation and upgrades use shared progress controls, suspended while showing prompts. Explicit color, Dots color preferences, native color fallback and independent icons retain their precedence. JSON, completion and exported manifests remain undecorated.

Help and operation previews use shared Dots headings, aligned fields and narrow-terminal wrapping. Bare invocation, `help`, `-h`, `-H` and `--help` share this layout without running package managers. Plain terminal mode keeps the layout; ordinary redirected help retains argparse text. Full formatted APT streams suppress only the exact “apt does not have a stable CLI interface” advisory; other warnings and errors remain visible. Raw forwarding retains every byte, including that advisory.

`format` explicitly filters stdin without requiring a package manager; `--raw` passes bytes unchanged. The subprocess runner preserves actual process status. The filter cannot recover the producer's status from text: use shell pipeline status/`pipefail` when needed. Formatting never starts or approves transactions.

## Editable manifests

```sh
pkgs export --output packages.json
pkgs export --update --dry-run
pkgs export --update
pkgs export --manager npm --global --pin-versions
pkgs manifest packages.json --json
pkgs restore packages.json --dry-run --json
pkgs restore packages.json
```

Export emits JSON to stdout by default. Automatic export inventories all supported user-wide managers independently of `upgrade.managers`; explicit selection retains ordinary manager scope. `--output FILE` uses guarded Store writes, confirms replacement, retains backups, refuses symlink/special-file destinations and avoids rewriting identical output. Partial export returns nonzero with notices in stdout JSON and does not replace a requested output file.

Slow manager discovery/inventory shows delayed progress on terminal stderr, including when stdout is redirected to a file. Each manager has a 45-second read budget; `--debug` includes query timings. Explicit `--json`, `--raw`, dry-run and `DOTS_PROGRESS=never` suppress the human progress lines. APT ownership checks for Python packages are batched after root filtering; missing evidence keeps a package disabled rather than claiming it is safe to restore.

Export prefers explicitly requested roots. `selection` records `explicit`, `inferred` or `all`; hand edits default to `manual`. RubyGems and failed system install-reason queries are labelled inferred. `--include-dependencies` requests the full selected inventory. Non-restorable source/linked/development entries remain with `enabled: false` and a reason. uv tools with source URLs, extras or additional requirements, and ambiguous duplicate installed records, also remain disabled for manual resolution.

The package menu's filename prompts default to `packages.json` in the current
profile root, beside its `profile.json`, regardless of the working directory.
On the base Termux profile this is `profiles/termux/packages.json`; a selected
Linux/WSL distro profile uses its own leaf directory. Escape and Ctrl-C return to
the package menu without exporting. **Update package manifest** uses the same
preview/Run flow as export.

`export --update` merges into that profile file by default; `--output FILE`
selects another destination. It refreshes matching `observed_version` values and
adds newly installed packages/groups, preserving existing pins, enabled states,
reasons, selection evidence, platform restrictions and packages/groups currently
absent. Foreign-platform groups remain unchanged. `--pin-versions` pins only new
records; existing pins remain authoritative. Missing files are created. The
explicit `--update` action authorizes the guarded merge/write without `--yes` or
a controlling terminal, including when `--output` selects another file. Dry-run
prints proposed JSON and the destination without writes. Updates retain stale-input
checks and backups; ordinary snapshot replacement without `--update` still requires
confirmation or `--yes`. An unchanged update does not rewrite
the file. A failed inventory cannot replace it. Bare export still emits JSON to
stdout, and no profile is required when an explicit output path is supplied.

Use `dots git publish --update-packages --dry-run` to preview an update included
in publication, then `dots git publish --update-packages` to run it with the
normal publish confirmation. See [publication boundaries](git.md#package-manifest-before-publication).

```json
{
  "schema": 1,
  "groups": [{
    "manager": "npm", "scope": "global",
    "platforms": ["termux", "linux", "wsl"],
    "packages": [{"name": "typescript", "observed_version": "5.7.3",
                  "pin": null, "selection": "explicit", "enabled": true}]
  }]
}
```

Groups identify manager, scope and optional platforms (default Windows for WinGet, otherwise Termux/Linux/WSL). System exports record the current platform. Scopes are `system` for system managers, `global`/`project` for npm, `base`/`venv` for pip, `user`/`active` for gem `tools` for uv/Go, and `user`/`machine` for WinGet. Project/environment scope is relative to the invocation, without saved machine-specific paths. Duplicate database/scope groups, duplicate identities, malformed/unknown fields and unsupported pins are rejected. The limit is 8 MiB. Manifests contain data, never executable recipes; `manifest` validates without probing managers.

`observed_version` records evidence. Missing unpinned packages use the manager's current default; installed unpinned versions are kept. Exact `pin` requests that version, including a downgrade where supported. Pin adapters are apt, dnf, npm, pip, uv-tool, gem and Go; native availability/protections still apply. `--pin-versions` emits pins for supported adapters and notices for the others, retaining observed versions without pins. Restore verifies state after successful commands and never removes unlisted packages. RubyGems allows coexisting versions: a gem pin requires that version to be installed, without removing other versions or changing Bundler/project resolution.

Restore respects disabled entries, platform filters and skip policies. Missing managers preview as deferred prerequisites. System groups run first, then languages are rediscovered. Missing prerequisites/failed groups produce an incomplete result while independent groups continue. Manifest/config drift after review requires a new preview. `--yes` approves; `--json` emits schema-1 per-group statuses with execution logs on stderr.

## Reviewed source-install cleanup

```sh
pkgs cleanup --dry-run
pkgs cleanup --json
pkgs cleanup
pkgs cleanup path/to/packages.json
```

Cleanup defaults to the active profile's manifest. It reviews disabled entries
whose reason is exactly `source or editable install; retain original source`.
Only current pip-owned source/editable installs in the matching platform and
Python scope can be selected. System-owned packages, missing/changed provenance,
unknown ownership and absent packages remain excluded with a reason. A saved
manifest flag alone never authorizes removal.

The command shows candidates, opens the existing FZF multi-select picker, displays
the selected native uninstall command and asks `Proceed? [y/N]`. Escape, Ctrl-C or
declining confirmation removes nothing. A terminal and FZF are required for
removal; `--yes` cannot bypass this review. `--dry-run` and `--json` only inspect.
Manifest, native config, profile selection and selected package provenance are
rechecked after confirmation. Drift requires a fresh review. pip performs the
uninstall, and pkgs checks that selected packages are absent afterwards; native
failures are reported without claiming success. Original source trees and disabled
manifest records are retained. A later `xup` still preserves those manual records.
Package removal has no Dots filesystem rollback.

The package menu includes **upgradable packages** as a read-only report and
**review source installs for removal** as a terminal action with this same review.

## Optional setup stage

```sh
./install.sh --packages packages.json --dry-run
dots files install --packages packages.json
dots init --setup --packages packages.json --yes
```

Selecting Packages in the setup wizard or with `--component packages` reads the active profile manifest; `--packages FILE` selects an explicit manifest. Setup previews desired selections without invoking managers in dry-run, obtains preparation approval, restores packages, rechecks guards and presents the final managed plan. It never invents bootstrap packages for missing managers. Incomplete restoration prevents configuration writes. Successful packages remain after later failures; file rollback/undo never removes them. Repeat setup retains satisfied packages. `--update` preserves the absolute manifest path across its restart; source updates retain their separate approval.

PowerShell accepts `-Packages FILE`. Native Windows restores WinGet groups through the same preparation stage, stopping at the first failed group. `--with-dependencies` can offer the pinned current-user WinGet module installation; it does not install package managers or alter repository trust. See [installation](installation.md) and [tests](testing.md).

Adapter references: [uv tool constraints](https://docs.astral.sh/uv/concepts/tools/#upgrading-tools), [DNF exact-version installation](https://dnf.readthedocs.io/en/latest/command_ref.html#install-command), [RubyGems commands](https://guides.rubygems.org/command-reference/) and [Go installation](https://go.dev/ref/mod#go-install).

## Native Windows WinGet

Use `--manager winget` with the ordinary search/list/info/install/uninstall/upgrade/refresh/export/manifest/restore workflows. User scope is the default; `--scope machine` is explicit and mutation requires an already elevated shell. Automatic Windows upgrades and export select WinGet user scope. Manifest groups use `manager: "winget"`, `scope: "user"` or `"machine"`, and default to `platforms: ["windows"]`. Exact version pins are supported; unavailable pins fail before installation.

Discovery uses the installed `Microsoft.WinGet.Client` PowerShell module through a fixed JSON bridge. Scope is proven by exact-ID WinGet list exit statuses, without parsing localized tables. Ambiguous/multiple/uncorrelated records remain visible but disabled; export retains their reasons. Package IDs are distinct from display names and compared case-insensitively. Mutations pass literal exact IDs, an explicit scope and `--source winget`. Store/private sources, Scoop and Chocolatey are excluded. Source agreements, force/hash bypass, reboot and elevation are not implied. Package acceptance applies only to the explicitly requested install/upgrade. WinGet recipe flags cannot replace the adapter's source/scope contract; existing explicit before/after/replacement recipes remain visible policy commands.

Setup offers `Microsoft.WinGet.Client` version `1.29.380` for CurrentUser when dependency preparation is selected and the module is missing. The NuGet provider and official PSGallery registration must already exist; setup checks the [PowerShellGet minimum NuGet version](https://learn.microsoft.com/en-us/powershell/gallery/powershellget/install-powershellget?view=powershellget-3.x), `2.8.5.201`, before invoking module installation. It never changes repository trust. Missing provider/source agreements require an explicit separate action. Native selection uses shared Gum or a numbered fallback without Bash; standalone Bash/Zsh/Fish completion management remains POSIX-specific. Native PowerShell completion comes from `dots init powershell`; WinGet package candidates are cache-only and never query remote sources during completion.

The [adapter tests](testing.md) run with fake managers and structured metadata. Native Windows PowerShell 5.1/7 acceptance remains pending; Termux fixtures do not establish native delivery or installer behavior.
