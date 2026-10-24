# Platform file identities and retired Ruby environment

Status: implemented and verified in isolated Termux fixtures; native platform limits below.

## Scope

Remove `DOTRUBY` and `RUBYCOMP`, inherited provenance, and the obsolete checkout `ruby/completion` PATH entry from native initialization. Keep `config/ruby` and unrelated Ruby paths. Use `termux`/`windows` file source IDs in catalogs, replacements, selectors, setup metadata and completion. Reject old CLI names with replacement hints.

Normalize legacy catalogs and receipt entry IDs only while reading. Preserve raw receipt guards, original backup references, drift protection, journal history and undo/recovery. Inspection and no-op installation must not write metadata. Do not migrate live state, remove compatibility links or modify unrelated Git submodule names.

## Acceptance

- Both Bash and native PowerShell controllers share file selection and setup validation; Windows app destinations are unchanged.
- Disposable shell fixtures verify inherited cleanup and repeated initialization.
- Disposable catalogs and receipts verify no-op installs, mapping edits, stash, uninstall, drift, rollback and recovery.
- Metadata/completion advertise canonical names; JSON/scalars remain undecorated. Existing shared error presentation is reused, under the [presentation gate](README.md#presentation-gate-for-every-plan).
- Run the focused retirement suite and affected existing file/environment/profile suites sequentially; verify docs and whitespace.
- Native Windows PowerShell 5.1/7, Linux/WSL and Xonsh acceptance remain pending where unavailable. Termux shell execution and portable fixtures are separate evidence.

## Verification

- Retirement suite: 13 passing tests, including native Bash/Zsh/Fish/Nushell reload, both completion controllers, old CLI refusals, legacy receipts, no-op installation, retargeting, drift protection, undo and interrupted recovery.
- Catalog: 9; file operations: 21; mappings: 28 before the additional bundled-profile case, followed by all 6 Git migration tests passing; installation: 25; shell environment: 9; profiles: 13; file checks: 16; Bash dispatcher: 24. Native controller suite: 14 tests, one PowerShell-runtime skip.
- Bash and native command metadata both validate 116 external commands. Python/shell syntax, relative Markdown links and `git diff --check` pass.
- Startup timing used disposable public fixtures and 15 sequential alternating warm interactive integration samples. Without/with the cleanup, median Bash startup was 51.766/52.388 ms; Zsh was 49.984/51.777 ms. These measure local cleanup overhead, not the owner's full startup configuration.
- No live installation receipts, generated themes or parent-shell environment were changed. Open a new shell or reload initialization to clear inherited Ruby state. Existing unrelated staged/worktree changes remain preserved.
- Native Windows PowerShell 5.1/7, Linux/WSL and Xonsh runtime acceptance remain pending. Windows app destinations and state boundaries are unchanged.
