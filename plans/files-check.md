# Missing-source catalog check

**Status: Implemented and verified, 2026-10-16.**

Add `dots files check` to the existing Bash CLI and bounded PowerShell adapter.
Read the same catalog and platform/filter/sort model as list. Review genuinely
absent sources individually, defaulting to Skip, then confirm the selected batch,
defaulting to Cancel. `--yes` selects all eligible entries; `--dry-run` overrides
it and writes nothing. JSON requires either flag and never prompts or animates.

Only catalog records are removed. Existing source objects, broken source links,
all target objects, replacement declarations and installation receipts remain.
Unavailable/excluded repositories are reported without initialization. Ambiguous
filesystem errors fail closed. Observe source absence independently of target
conflict status. Guard composition, catalog inputs and absence; source reappearance
or metadata drift requires a fresh preview. Use Store for multi-catalog apply,
reverse rollback, durable recovery and undo from journaled catalog metadata.

Use the existing Python Presentation/resource helpers, optional Gum with text
fallback, and delayed progress. Review populated, empty, broken-link, failure,
preview, selected-batch and completed output at 40/80/120 columns. Preserve full
paths, color/icon independence, plain views and forced-decoration JSON contracts.

Acceptance: isolated selection/cancellation, filters, no-op/idempotence, absent
files/directories/parents, broken links, permissions, source/catalog drift,
unchanged targets, multi-catalog rollback/recovery/undo; command metadata and
three-shell completion; existing catalog, operations, interaction, progress,
resource, dispatcher and native-adapter regressions. No live catalog cleanup,
installation, publication or nested-repository edits are authorized by this work.

## Verification

- Missing-source check suite: 16 passing tests, including owned terminal review
  at 40/80/120 columns, delayed progress, plain output, final cancellation and
  forced-decoration JSON. A populated narrow preview was also visually reviewed.
- Shared regressions: catalog 9, file operations 21, confirmations 8, progress 11,
  resources 11 and Bash dispatcher 24 passed. Catalog coverage includes static
  route/help and Bash/Zsh/Fish option/repository completion.
- Installation adapters: 5 passed, 3 skipped because native PowerShell/Windows
  runtimes were unavailable. The new native check route has a dedicated skipped
  acceptance case; no native Windows execution claim is made.
- Python/Bash syntax, wrapper ShellCheck, 82-command metadata validation, 676
  relative Markdown links in 93 documents and `git diff --check` passed.

The shared transaction digest now treats only ENOENT as absence; permission and
other inspection errors propagate. Existing operation/recovery regressions pass.
Shared optional confirmation accepts a backward-compatible cancellation label so
per-entry review offers Skip while final approval retains Cancel.

No live catalog cleanup, installation, publication, commit or push was performed.
Existing working-tree changes and nested repositories were preserved. Durable
user behavior and JSON details are documented in [files](../docs/files.md#check-missing-sources).
