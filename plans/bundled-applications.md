# Absorb Blastoff and pkgs

**Status: Implemented and locally verified; native Windows and WSL acceptance pending.** Clean source snapshots are absorbed into first-party Dots directories, preserving the original repositories and existing Dots changes. This is a source absorption, without nested Git repositories, history rewriting, or automatic changes to the live installation.

The source layout and installation migration are now maintained by the [portable plugins plan](portable-plugins.md); the verification below records the original absorption.

## Goals and implementation

- [x] Import Blastoff 0.1.12 and pkgs 0.1.1, retaining runtime sources, assets, tests, manuals, licenses and provenance. Keep historical release evidence clearly separate from Dots acceptance.
- [x] Provide `blastoff`, `pkgs`, `dots blastoff` and `dots pkgs`, forwarding every argument, subcommand, stream and exit status to the same bundled core. Generate static Dots discovery/help/completion metadata from the application grammars; ordinary dispatch must not scan all commands.
- [x] Extend the shared installer receipt to cover both applications' launchers, standalone completion files and manuals. Root and bundled public lifecycle scripts must use the combined Dots installer. Preserve backups, pre-existing-link nonownership, idempotence, rollback and drift-aware uninstall; never remove application data or packages as application uninstallation.
- [x] Cover Bash on Termux/Linux/WSL and native PowerShell entry points. Blastoff retains its configuration paths and native core. pkgs' POSIX package backends remain an explicit native Windows exception; help/version and static Dots discovery remain available, with actionable refusal for unsupported operations.
- [x] Synchronize README, command/install/architecture/platform/safety/testing references and generated wiki. Preserve original application output and machine interfaces, following the [presentation gate](README.md#presentation-gate-for-every-plan).

## Verification

Use disposable home/config/state/cache/data/repository roots. Check complete argument forwarding (including spaces, Unicode, empty strings, leading dashes and literal separators), help/version/data equivalence, static completion without backend execution, metadata synchronization, first install/update/uninstall, collision preflight, original-baseline restoration, interrupted rollback, no-op repeat install and drift preservation. Run imported core suites and relevant Dots dispatcher/native/installation suites sequentially. No tests may change host packages or active configuration.

Review narrow human help and plain/JSON output. Run shell syntax, documentation links, command validation and wiki source/build checks. Record actual Termux results separately from native Windows PowerShell 5.1/7 and WSL acceptance, which remain pending without those hosts. No commits, pushes, source-repository deletion or live installation are part of this task.

## Verification evidence (2026-10-28)

- Blastoff behavior suite: 233 tests, passed with three optional native/real-tool checks skipped. Retired standalone archive/prefix-install tests are explicitly separate from Dots lifecycle acceptance.
- pkgs behavior suite: 85 tests passed after the final bundled Fish status adjustment.
- New application lifecycle tests verify retained launcher baselines, no-op repeat installation, preserved drift/pre-existing links, missing-file refusal and rollback after a bundled command replacement. Root and nested public scripts produce the same combined dry-run plan.
- The existing strict full-checkout theme idempotence case fails because repeat setup republishes the theme. This was reproduced using the unchanged HEAD installer in the same disposable fixture. It is not caused by application absorption. The strict test remains intact; a separate full-checkout case checks the bundled assets' no-op repeat and combined removal while retaining that baseline finding.
- Source application repositories remain clean. Dots' pre-existing `config/blastoff/themes/dots.toml` EOF whitespace warning is preserved; scoped whitespace and all documentation links pass.
- Native Windows PowerShell 5.1/7 and WSL runtime acceptance remain pending. No host packages, active configuration, commits or remote repositories were changed by validation.

- Final integration suite: 17 cases completed successfully with one native PowerShell skip, including native Blastoff alias transport, dependency-status preservation and pkgs version without Python. The separate full-checkout bundled install/repeat/remove case passed.
- Shared regressions: file-platform 5 passed; Bash dispatcher 24 passed; native controller 14 cases passed with one engine-dependent skip; installer adapters 10 cases passed with five native skips; local completion 6 passed. PowerShell startup's 22 cases were skipped because no engine is installed locally. The earlier installation run passed its other 24 cases; its strict fresh-checkout theme repeat failure is recorded above.
- Direct-dispatch comparison against HEAD, Termux ARM64, 15 measured samples after three warmups: zero extra routes 47.771 ms before / 48.605 ms after; 1,000 extra routes 49.123 ms before / 48.085 ms after. This confirms targeted lookup scaling locally, not a cross-platform timing guarantee.
- All tracked files from both original repositories are included, retaining Blastoff's reference artwork and project workflow files. Git internals, untracked files and ignored machine-local state were not imported.
- Generated metadata is current and command validation passes for 184 routes. Canonical documentation validation passes for 942 links in 130 files; imported application links also pass. The local wiki was rebuilt under transaction `593de993b09b48d29839e5bb747f8427`, and `dots wiki check` reports healthy. Existing wiki changes were retained; nothing was published.
