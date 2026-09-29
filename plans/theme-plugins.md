# Theme plugins

**Status: Implemented and verified in native Termux fixtures; live desktop appearance remains unverified.** Owner-authorized local-hook exception; broader Go work and Anodize.nvim changes remain out of scope.

## Design

- Add `dots theme plugins` help and list/enable/disable/run/doctor routes using static command metadata and read-only name completion. All plugins default disabled; selections live in XDG config, not scripts.
- Discover numeric-prefix Bash files only in the bundled directory and the explicit user `dots/hooks/theme-set.d` directory. Reject ambiguous names. Never discover hooks in downloaded themes.
- Run once from the shared publisher after commit, including unchanged explicit refresh. Load the published normalized palette JSON; export documented Dots and no-hash compatibility variables. Independent Bash children, failure isolation, recursion refusal, nonblocking locks, clean JSON, and shared presentation/progress are required.
- Keep automatic failures separate from publication success. User hooks have arbitrary user privileges and no automatic rollback. Retain the theme lock through execution; manual runs acquire theme then plugin locks, children inherit neither. Read-only commands remain lock-free.
- Bundle GTK 3 and Qt6ct because both have tracked configuration. Render through existing templates and journal copies plus narrow configuration registration through the existing Store, including ownership receipts and retained backups. Disabled plugins must not follow the moving current pointer.
- Preserve unrelated settings and custom scripts; refuse unsafe paths, unmanaged output collisions, managed-content drift, and ambiguous registrations. No package installation, desktop settings mutation, or process termination.

## Provenance

Read-only reference: `~/src/shellscript/theme-hook-plugin-manager`, revision `d244119418cc8bc02c04abc803f0c6d346bfa0ed`. Inspected README, plugin documentation, thpm, runtime, hooks, installers and tests. No license grant was found in the checkout: independently author code/templates, copy no substantial upstream code. Format references: GTK CSS documentation and Qt6ct's upstream palette reader/QPalette roles.

## Acceptance

- Disposable roots/stubs: discovery/order/enablement/persistence/collisions; missing dependencies/platform skips; ordinary and Anodize shared publication; unchanged refresh/manual retry; no execution or persistent writes in read-only/dry-run paths; downloaded-script isolation.
- Failure/exit/recursion/concurrency and interrupted execution; app idempotence, preservation, preflight, rollback/recovery and drift-aware undo; help/completion and JSON integrity.
- Run focused tests plus existing theme/workflow/file/framework and Anodize integration suites, available shell syntax/ShellCheck, Markdown links and `git diff --check`. Measure publication overhead and record actual platforms, baseline failures and skips.
- Synchronize README, theme/plugin authoring, commands, architecture/safety/platform/testing docs and plan index. Apply the presentation acceptance gate: coherent human views, plain fallbacks, data output without decoration, optional tools optional.

## Deferred

Remote plugin installation, self-update, upstream uninstall behavior, GTK 4, native Windows execution and live desktop visual acceptance. No live theme activation, hook enablement, packages, commits or pushes during development.

## Evidence

Native Termux / Android ARM64, 2026-09-29. All runtime tests used disposable HOME/XDG/repository roots; desktop commands were stubs. No source installer, package manager, live theme/hook activation, commit or push was performed.

| Check | Result |
| --- | --- |
| New theme plugin suite | 20 passed: selection, ordering, compatibility colors, JSON, Bash startup isolation, recursion, manual/automatic concurrency, native PTY progress policy, corrupt published data, app preservation/idempotence, BOM/charset preservation, unsafe objects, rollback, abrupt interruption, recovery and drift-aware undo |
| Existing theme suite | 23 passed |
| Bash command framework | 23 passed |
| File operations | 21 passed |
| Anodize verifier | Go tests/vet and 17 CLI acceptance tests passed, including the new shared-publication/inert-authoring case |
| Anodize shell integration | 4 passed; generated integration freshness passed |
| Shared progress | 11 passed |
| Theme workflow | 12 passed, 2 existing 33-versus-34 catalog-count failures; both reproduced with HEAD publisher/render/commands and no plugin routes/templates in disposable fixtures |
| Zsh | 15 passed, 2 existing `ll` alias expectations failed; reproduced without plugin publication/routes |
| Zsh/FZF-tab PTY | Existing `command not found: box` preview diagnostic; reproduced with plugin publication/routes removed |
| Static checks | New Bash/Python syntax, warning-level ShellCheck, and `git diff --check` passed |
| Markdown | Full checker still stops at the existing `docs/testing.md` link to the absent legacy Yazi symlink-plugin README. An exhaustive local-link pass found only that known failure (493 links inspected); the link also exists in HEAD |

Initial new-test failures were fixture-only: file undo/recover required a disposable `.dots/sources.json`. After supplying it, both passed. The plugin fixture also avoids accidentally collecting the imported legacy theme suite a second time. A new PTY assertion also caught a generic progress label; the coordinator now updates the active plugin label and the final 20-case suite passes.

### Advisory timing

Six warm samples per case, native Termux, redirected output, isolated roots, no concurrent verification workloads. Alternated baseline/current order for new `nord`/`white` publication and unchanged refresh. Baseline used HEAD publisher/core/render/commands with the new hook callback/routes/templates removed from a disposable copy; unrelated working-tree data was retained in both fixtures.

| Operation | Baseline median | New median |
| --- | --- | --- |
| New publication, no selection file | 1700.9 ms | 1653.9 ms |
| Unchanged refresh, no selection file | 138.7 ms | 139.7 ms |
| Unchanged refresh, saved empty selection | — | 293.6 ms |
| Unchanged refresh, GTK and Qt6ct enabled | — | 800.4 ms |
| Manual unchanged run, GTK and Qt6ct enabled | — | 668.8 ms |

The publication spread was broad (1391–1897 ms baseline, 1412–1766 ms current); this is not evidence of a speedup. Default refresh with no selection file remained effectively unchanged. A separately measured saved empty selection (six samples: 289.6, 288.1, 307.7, 311.8, 297.6, 289.3 ms) still starts the manager to validate configuration, adding roughly 154 ms over the default path. This affects explicit refresh/publication, not shell startup. Enabled adapters deliberately pay for isolated Bash/Python children, palette/target validation and journal-aware inspection. App writes were idempotent; no caching was added. These results do not establish live desktop performance or native Windows support.
