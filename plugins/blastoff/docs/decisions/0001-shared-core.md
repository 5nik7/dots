# 0001 — One shared core, thin shell entry points

Status: selected by Nick on 2026-09-30 for this review build.

The existing Bash and PowerShell versions duplicate path resolution, listing,
selection and mutation behavior, and already diverge. Keeping identical behavior
is easier to verify when they execute the same implementation.

Use Python 3.11+ with the standard library. `tomllib` validates real TOML without
a third-party runtime dependency. Bash and PowerShell remain first-class entry
points; native PowerShell does not require Bash or WSL. The Bash path does not
require PowerShell. Starship is required only for built-in preset operations.

This adds a Python runtime requirement on every host and has higher startup
cost than a small compiled executable. Version avoids the heavy imports. Help
still starts Python and argparse. Record native Termux and Windows measurements
before setting host budgets or choosing a compiled core; do not silently treat
a preference for speed as approval to change the selected language.

A conservative section-based module editor preserves unrelated text and checks
semantic equivalence with `tomllib`. It safely rejects layouts it cannot edit.
A future extension could use an established TOML editing library if its extra
dependency, startup/storage cost and supported layouts are justified.

Copy-on-apply avoids privileged Windows symlink creation and accidental edits of
stored themes. Existing active config symlinks require explicit conversion and
get both content and link-text backup evidence. Native platform tests are still
required; a shared core does not prove wrapper parity or filesystem semantics.

The 0.1.7 extension is documented in [decision 0002](0002-provenance-and-interactive-editing.md); it retains this shared-core choice.

The 0.1.8 frontend/lifecycle boundary is recorded in [decision 0003](0003-picker-output-and-powershell-lifecycle.md); shared business logic remains Python.
