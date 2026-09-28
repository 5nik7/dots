# Gum confirmations

Status: **Implemented**, 2026-09-28.

Add optional Cancel/Apply confirmations to managed-file operations and Anodize, and Cancel/Publish to Git publishing. Cancel is the default. Preserve existing previews, operation plans, guards, rollback, locks and JSON contracts. No routes or flags change.

Use the shared Bash interaction adapter and neutral Python bridge. Require usable input/output/error terminals and Gum; Python also requires Bash. Otherwise retain each command's existing text prompt. Never retry after selector failure. Explicit Cancel preserves command cancellation results; interruption exits 130.

Bypass tool probing for JSON, explicit approval, dry runs and read-only routes. Preserve the browser and theme picker. No shell startup changes, installation or live activation.

Acceptance follows the [presentation contract](../docs/presentation.md#acceptance-gate): isolated approval/cancellation/failure and drift tests, plain/JSON/redirected/color modes, native Gum PTYs, existing affected suites, documentation links and whitespace checks. Publication fixtures use local bare remotes only.

Verification on native Termux:

- Confirmation checks: 8/8, including fixture approvals/errors, JSON and text fallbacks, drift during review, and real Gum Cancel/Apply/Publish/Escape/Ctrl-C at 40/80 columns. Git publication used local bare remotes only. The final terminal `--yes`/`--dry-run` bypass case also passed separately.
- Anodize verifier: Go checks and 16/16 CLI tests passed, including two new confirmation cases using fixture Gum.
- Browser 17/17, picker 14/14, file operations 21/21, Git operations 25/25, catalog 9/9 and Bash dispatcher 23/23 passed.
- Reviewed a real 40-column Gum confirmation transcript. Bash/Python syntax, focused ShellCheck with script-relative source resolution, Markdown links and whitespace passed.

Common POSIX fixtures and Termux execution do not establish native Linux, WSL or Windows behavior. Existing previews, transaction guards and Git publication semantics remain unchanged. No live configuration, theme or remote was modified by verification.

Broader verification: shared themes passed 23/23. Theme workflow passed 12/14;
the two pre-existing failures (`test_flat_palette_catalog` and
`test_presentation_and_raw_theme_queries`) still expect 33 themes while the
catalog contains 34. No confirmation regression was found; those unrelated count
assertions were left unchanged.
