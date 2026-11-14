---
name: dots-shell-integration
description: Maintain Dots shell initialization, settings and palette refresh across native adapters. Use for dots init, startup variables or shell reload changes.
---

# Dots Shell Integration

Read [shell environment](../../../docs/shell-environment.md) and [shell initialization](../../../docs/shell-init.md).

Dots integration lives in lib/dots/shell; personal prompts/plugins stay in shells. Resolve shell settings from the shared schema and literal config parser, preserving their explicit environment precedence and failed-reload atomicity. Avoid exporting defaults back into the override namespace. Keep scalar PATH variables separate from shell-specific maps.

Use [dots-config](../dots-config/SKILL.md) for new/changed configuration integrations and visual preference resolution; do not apply shell-setting precedence to unrelated visual layers. Command changes require configuration and menu assessments through [command maintenance](../dots-command-maintenance/SKILL.md). `dots init --setup` delegates to installation: also follow [bootstrap guidance](../../../agents/guides/bootstrap.md) and [file maintenance](../dots-files-maintenance/SKILL.md), preserving generated-code paths as read-only.

Check every affected native adapter and old published snapshot fallback. Use tools/test_shell_environment.py plus focused tools/test_shell_init.py or tools/test_zsh.py cases, with owned roots and no private modules. Test repeated initialization, prompt exit status and hook duplication. Measure startup sequentially if its work changes; do not introduce scans or theme publication into startup.

Shared Bash/Zsh CLI formatting travels as validated `__format.*` rows through the existing literal settings reader and compiled bundle. Keep profile/default inputs in bundle invalidation, reject executable or malformed values and avoid per-row or additional warm-start subprocesses. `tools/test_config_alignment.py` checks compiled literal consumption and defaults-file invalidation; native PowerShell reports use the shared Python renderer.

Report absent PowerShell/Xonsh native verification explicitly. Do not replace launchers or install interpreters merely to make a check pass.

Maintain Bash (Termux/Linux/WSL) and native Windows PowerShell 5.1/7 together. Cover matching flags, completion, data output, progress and picker behavior; use native adapters and shared transactions. Follow [PowerShell parity](../../../docs/powershell.md), and distinguish fixture tests from native terminal/desktop evidence.

When this change affects documentation, follow [documentation maintenance](../dots-documentation-maintenance/SKILL.md), including the generated wiki check.

For generated profile paths, use [profile maintenance](../dots-profile-maintenance/SKILL.md). Keep path generation in `profile_environment.py`; preserve all native maps, inactive-profile cache inputs, aliases and stale-name cleanup.

Configuration coverage includes foreground/background, nullable icon styles, labels/values, indentation/tab stops, spacing, alignment and native placement where useful. Follow [dots-config](../dots-config/SKILL.md) for typed controls and consumer verification; use [dots-config-audit](../dots-config-audit/SKILL.md) for requested broad discovery. Preserve native ownership and data output, and record a reason for controls deliberately left unchanged.

Register shipped standalone command names and aliases alongside Dots routes in all six completion adapters. Bak uses `bak_completion.py` for static grammar and bounded catalog IDs, never payload access. Nu/Xonsh receive literal path candidates on demand. Run `tools/test_backup_completion.py` for this provider; separately verify native adapter registration/escaping.

Zsh completion appearance is owned by `completion_preferences.py` and
`completion/styles.zsh`. Preserve literal startup rows, bounded builtin prompt
checks and last-good refresh; do not publish a theme for completion-only saves.
Guard plugin interfaces and preserve insertion/group/preview identities. Keep
LS_COLORS for files, neutral unknown types and semantic selected-row spans.
Run `tools/test_completion_colors.py` with affected startup/config/completion
checks; record native desktop and optional binary-plugin limits explicitly.
Preserve semantic types when FZF-tab hides headings. Native `_arguments`
`option-*`/`argument-*` tags describe values; command-position providers must
identify commands explicitly. Standalone plugin/project adapters need their own
coverage alongside `dots FAMILY`; test actual registered functions and aliases.
Use `tools/test_project_completion_menus.py` for available associated checkouts
and `tools/check_project_completions.py --repos-root PATH --check` for ownership
discovery. Reuse `apps.completion`/`colors.apps.completion` preferences; never
hard-code a provider palette or add startup repository scans.

Distinguish completion-list colors from command-line syntax highlighting. Dots
route words use the native FSH `subcommand` role through `themes/fsh-dots.zsh`;
preserve user chroma entries, native syntax and literal BUFFER. Keep recognition
to exact paths without command execution or directory scans on redraw. Run
`tools/test_fsh_dots.py` for input regions and fallback behavior. The normal-startup
case in `tools/test_completion_colors.py` must exercise the public entry point,
Zinit lazy loading, exact-word Tab, subsequent menus and reload. Directly loading
FZF-tab before the adapter is useful unit evidence but cannot replace this check.
