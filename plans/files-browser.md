# Interactive tracked-file browser

**Status: Implemented, 2026-09-28.**

Implement the owner-approved `dots files browse` flow: current-platform tracked
resources, one at a time, searchable by identity/app/status/paths, with details,
Link and Stop managing. Reuse catalog observation, managed planning and guarded
transactions. Discovery, editing, batches, recovery browsing and native Windows
mutation remain deferred. Preserve the previous Gum/theme work and leave changes
uncommitted; no live configs are test targets.

Gum is preferred, with FZF and plain-numbered fallbacks. Back is the default at
review; only Apply uses the exact approved operations and guards. Retained backups
start with the configured preference and can change for this session only. Refresh
the catalog after successful operations; refuse drift instead of recomputing an
approved plan. Browsing, previews and cancellation create no state or locks.

- [x] Add the route/controller and private bridge to the shared interaction adapter.
- [x] Verify isolated browsing, planning, Apply, drift, backups, refusals and native PTY interactions.
- [x] Synchronize metadata/completion, user/contributor docs, safety and verification evidence.

Apply the [presentation gate](../docs/presentation.md#acceptance-gate): human
terminal-only UI, existing semantic roles and detail renderer, color/icons/plain
modes, 40/80/120-column review and safe path display. Existing JSON/scalar/help and
completion interfaces remain exact. Record native and fixture evidence separately.

Verification on 2026-09-28: browser checks passed 17/17, file catalog 9/9,
file operations 21/21, Bash dispatcher 23/23 and theme picker 14/14. Browser tests
include installed Gum and FZF under native Termux PTYs, Gum details at 40/80/120
columns, and a real Gum-driven link into a disposable target. Common POSIX catalog
fixtures report Linux because platform environment inputs are isolated; this is
not native Linux evidence. A separate 40-column forced-color/icon transcript was
reviewed. Syntax, focused ShellCheck, relative Markdown links and whitespace checks
passed. No live configuration, state, wallpaper, editor or repository history was
changed. Native Linux/WSL/Windows interaction remains unverified.
