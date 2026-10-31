# Package workflows

`pkgs` and `dots pkgs` share the bundled core on Termux, Linux and WSL. Native Windows supports help/version, static discovery, `format`, `manifest` and the Dots Config editor; package operations return status 3. Dots never launches WSL.

## Upgrade and scope

```sh
pkgs upgrade --dry-run
pkgs upgrade
pkgs upgrade --manager npm --global
pkgs upgrade --manager apt ripgrep
```

Bare `upgrade` authorizes supported user-wide updates without another pkgs prompt, including without a controlling terminal. It selects one system database, global npm, uv tools, pip-owned base-interpreter distributions, user RubyGems and Go tools. Arch prefers the configured available helper, otherwise paru, yay or pacman, and deduplicates that database. Active Python virtual environments and Bundler projects exclude those languages from automatic selection. pip ownership requires `pip inspect` and a system ownership check when that database is available; unknown/system-owned/source installs are skipped. User RubyGems excludes default and system gems. Language inventories do not discover arbitrary project directories.

Explicit `--manager` restricts the operation; named operands retain selected scope. Explicit npm defaults to the current project unless `--global` is used; explicit pip uses pkgs' interpreter and gem uses its active environment. The configured `upgrade.managers` list restricts automatic selection. System operations precede language operations, preserving order within each group.

Native noninteractive flags are supplied where supported. sudo uses `-n` without a controlling terminal and never runs on Termux. Privilege and native package protections may still fail. Independent managers continue after a failure; a failed command stops that manager's remaining recipe. The final status is nonzero if any manager failed. Ctrl-C stops the run. Completed package effects remain; there is no Dots package rollback.

`pkgs refresh` also authorizes its repository metadata refresh without an extra flag or controlling terminal. It supports APT, DNF and XBPS; Arch still requires `upgrade` to synchronize and upgrade together. Install, uninstall and restore retain approval prompts; `--yes` approves intentional noninteractive execution. Dry-run prints plans/skips and executes no mutation commands or recipe hooks, although local inventory queries still run. The upgrade and restore menus review the preview and require an explicit **Run** choice.

## Go tools

`pkgs list --manager go --installed` reads build metadata in `GOBIN`, or the first `GOPATH`'s `bin`, without executing binaries or downloading a toolchain. Install takes a full module package path. Upgrade uses available `go-global-update` with selected binary names, otherwise `go install PATH@latest`; custom build flags use direct Go installation. The helper is never installed automatically.

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

## Output

```sh
pkgs upgrade --raw
some-package-command 2>&1 | pkgs format --manager apt
```

`auto` styles owned subprocess output in terminals/menu readers and forwards ordinary redirected streams unchanged. `styled` explicitly enables formatting; `raw`/`--raw` preserves bytes. Concurrent stdout/stderr draining retains unknown messages and partial prompts; carriage-return updates become readable lines. Formatted output strips terminal controls and recognizes manager events with shared semantic colors. Preparation uses shared progress controls. Explicit color, Dots color preferences, native color fallback and independent icons retain their precedence. JSON, completion and exported manifests remain undecorated.

Help and operation previews use shared Dots headings, aligned fields and narrow-terminal wrapping. Bare invocation, `help`, `-h`, `-H` and `--help` share this layout without running package managers. Plain terminal mode keeps the layout; ordinary redirected help retains argparse text. The formatted APT stream suppresses only its exact “apt does not have a stable CLI interface” advisory; other warnings and errors remain visible. Raw forwarding retains every byte, including that advisory.

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
records; existing pins remain authoritative. Missing files are created. Dry-run
prints proposed JSON and the destination without writes; replacement retains
the normal confirmation, guards and backups. An unchanged update does not rewrite
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

Groups identify manager, scope and optional platforms (default Termux/Linux/WSL). System exports record the current platform. Scopes are `system` for system managers, `global`/`project` for npm, `base`/`venv` for pip, `user`/`active` for gem and `tools` for uv/Go. Project/environment scope is relative to the invocation, without saved machine-specific paths. Duplicate database/scope groups, duplicate identities, malformed/unknown fields and unsupported pins are rejected. The limit is 8 MiB. Manifests contain data, never executable recipes; `manifest` validates without probing managers.

`observed_version` records evidence. Missing unpinned packages use the manager's current default; installed unpinned versions are kept. Exact `pin` requests that version, including a downgrade where supported. Pin adapters are apt, dnf, npm, pip, uv-tool, gem and Go; native availability/protections still apply. `--pin-versions` emits pins for supported adapters and notices for the others, retaining observed versions without pins. Restore verifies state after successful commands and never removes unlisted packages. RubyGems allows coexisting versions: a gem pin requires that version to be installed, without removing other versions or changing Bundler/project resolution.

Restore respects disabled entries, platform filters and skip policies. Missing managers preview as deferred prerequisites. System groups run first, then languages are rediscovered. Missing prerequisites/failed groups produce an incomplete result while independent groups continue. Manifest/config drift after review requires a new preview. `--yes` approves; `--json` emits schema-1 per-group statuses with execution logs on stderr.

## Optional setup stage

```sh
./install.sh --packages packages.json --dry-run
dots files install --packages packages.json
dots init --setup --packages packages.json --yes
```

Without `--packages`, setup keeps its file-only behavior. With it, setup previews both stages, restores declared packages, rechecks configuration guards and then applies managed files. It never invents bootstrap packages for missing managers. Incomplete restoration prevents configuration writes. Successful packages remain after later failures; file rollback/undo never removes them. Repeat setup retains satisfied packages. `--update` preserves the absolute manifest path across its restart; source updates retain their separate approval.

PowerShell accepts `-Packages FILE`. On native Windows the stage refuses before configuration changes because package backends are unavailable; ordinary Windows setup remains supported. See [installation](installation.md) and [tests](testing.md).

Adapter references: [uv tool constraints](https://docs.astral.sh/uv/concepts/tools/#upgrading-tools), [DNF exact-version installation](https://dnf.readthedocs.io/en/latest/command_ref.html#install-command), [RubyGems commands](https://guides.rubygems.org/command-reference/) and [Go helper](https://github.com/Gelio/go-global-update).
