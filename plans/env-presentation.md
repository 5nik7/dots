# Dots CLI presentation skill and environment view

**Status: Implemented, 2026-10-16.**

Create and validate a local `dots-cli-presentation` skill, then apply it to
`dots env`. Follow the [presentation acceptance gate](../docs/presentation.md#acceptance-gate).
Use shared terminal colors without theme resolution or new runtime dependencies.

- [x] Skill entrypoint, UI metadata, discovery and index; validate and apply it.
- [x] Human environment renderer with theme/settings/paths sections, provenance,
      boolean explanations, aligned or stacked fields and safe complete values.
- [x] Preserve scalar, version-1 JSON and unforced redirected listing formats.
- [x] Isolated native PTY/color/data tests, shell-environment and dispatcher suites,
      Bash syntax, ShellCheck, documentation links and whitespace checks.
- [x] Synchronize user and command documentation.

Preserve the preceding theme-view changes. No setting resolution, shell startup,
publication, installation, commit or unrelated-command redesign belongs to this task.

Verification: skill validator, reference/discovery/UI metadata checks, 8 shell
environment tests and 24 Bash dispatcher tests passed. Native Termux PTY checks
cover 40/80/120 columns with and without colors; representative output was also
reviewed. Path wrapping prefers slash boundaries and retains every character.
Bash syntax, ShellCheck (dynamic-source SC1091 and pre-existing quoting SC1003
notices excluded), relative documentation links and whitespace checks passed.
No native Windows support claim is added by these Termux checks.

## Home abbreviation (2026-10-23)

**Implemented and verified on Termux.** Human path fields abbreviate the home directory as `~` and its descendants with a leading tilde. Exact directory boundaries prevent shortening unrelated prefixes. Bash abbreviates before escaping/wrapping and retains the original resource path for styling; the native Python controller uses `Presentation.path()` with native separators. JSON, scalar queries and ordinary redirected listings retain full paths. No schema, flags, startup behavior or Windows application destinations change.

Acceptance covers exact home, descendants, unrelated prefixes, spaces/Unicode, color/plain 40/80/120-column PTYs, control-character escaping and unchanged data output. Native Windows PowerShell 5.1/7 acceptance remains pending; running its Python controller on Termux does not establish Windows execution.

Verification: all 9 shell-environment and 24 Bash dispatcher tests pass, including both controllers' display/data comparisons and Bash color/plain 40/80/120-column PTYs. Bash syntax, relative Markdown links and `git diff --check` pass. ShellCheck reports only the existing SC2209 warning on `resource_kind=file`, outside the changed lines. Earlier completion edits and the unrelated logo edit are preserved.
