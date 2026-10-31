---
name: dots-env-maintenance
description: Maintain dots env effective-environment inspection, provenance, redaction and human/data output. Use for the reporting command; use profile maintenance and shell integration for generating or activating environments.
---

# Dots Environment Reporting Maintenance

Read [environment reporting](../../../docs/profiles.md#environment-reporting) and the [shell environment contract](../../../docs/shell-environment.md). `bin/dots-env` forwards to `lib/dots/environment.py`; the native controller uses the same reporting logic. `profile_environment.py` and native startup adapters own generated declarations/activation. Keep reporting separate from those producers.

Distinguish saved profile declarations, generated paths/application defaults, inherited exports and observed Dots hook evidence. A subprocess cannot observe unexported parent-shell variables or prove that an inactive profile is loaded. Do not rerun startup/private hooks, evaluate shell code or dump unrelated environment values to fill missing evidence. Preserve origin labels and redaction of sensitive/private-hook values in every output mode; bundle manifests must not capture caller values.

Scalar queries remain exact and undecorated. JSON retains its versioned value/source contract, and redirected listings retain their documented format. Use [CLI presentation](../dots-cli-presentation/SKILL.md) for owned human views without styling data output. File/path rendering must not turn missing paths into created directories.

Follow [command maintenance](../dots-command-maintenance/SKILL.md) for the required config/menu review and [dots-config](../dots-config/SKILL.md) when a reported setting gains an integration. Changes to generated namespaces or precedence also require [profile maintenance](../dots-profile-maintenance/SKILL.md); activation belongs to [shell integration](../dots-shell-integration/SKILL.md).

Verify `tools/test_shell_environment.py`, affected `tools/test_profile_config.py`/`tools/test_profile_backend.py` cases and both dispatcher paths when routing changes. Check inherited overrides versus saved defaults, unavailable evidence, secret redaction, empty/scalar/JSON/redirected output and inspection purity using owned environments. Report native runtime gaps and update canonical docs/wiki through [documentation maintenance](../dots-documentation-maintenance/SKILL.md).
