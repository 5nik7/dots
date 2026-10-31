---
name: dots-debug-maintenance
description: Maintain dots debug inspection, startup tracing, PATH recording and curated self-tests. Use for diagnostic implementation and reporting changes, not as permission to run live startup or repair the user's environment.
---

# Dots Debug Maintenance

Read [debugging](../../../docs/debug.md), [diagnostic safety](../../../docs/safety.md#explicit-startup-diagnostics) and [profile behavior](../../../docs/profiles.md). `lib/dots/debug_cli.py` routes into `debug/inspect.py`, `startup.py`, `record.py`, `changes.py` and `selftest.py`; native tracing adapters also live under `lib/dots/shell`. Keep inspection, opted-in tracing and recording separate.

Default checks explain declared paths, command resolution and cache metadata. They must not execute discovered commands, source cache guards, prepare caches, activate profiles or repair files. Startup traversal without `--live`/`--isolated` describes potential modules, not observed execution. `--live` executes ordinary child-shell startup and its side effects; do not select it automatically or promise sandboxing. Use the existing owned public fixture for `--isolated` and curated tests.

Preserve bounded, sanitized trace data: no expanded command/function/alias bodies or secret values. Keep raw shell-state comparison in its existing transient transport, and preserve explicit sensitive-value refusal. PATH recording requires explicit opt-in, owns only its hooks/private temporary data, refuses conflicts and never reconstructs history before activation. Inspection must not install recorders or prune another session's files.

Follow [command maintenance](../dots-command-maintenance/SKILL.md) for config/menu assessments and [dots-config](../dots-config/SKILL.md) for changes to diagnostic settings. Use [shell integration](../dots-shell-integration/SKILL.md) and [profile maintenance](../dots-profile-maintenance/SKILL.md) at their boundaries. Verify with `tools/test_profile_debug.py`, `tools/test_debug_tracing.py` and affected shell suites in owned roots. Cover read purity, redaction, timeout/partial traces, malformed/stale cache data, hook cleanup and exact JSON. Record native engine limits and finish through [documentation maintenance](../dots-documentation-maintenance/SKILL.md).
