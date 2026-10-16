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
