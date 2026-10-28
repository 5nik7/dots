---
name: dots-theme-maintenance
description: Maintain Dots palettes, file styles, templates and publication with isolated consumer checks. Use for theme generation or app connector changes.
---

# Dots Theme Maintenance

Read [theme architecture](../../../docs/themes.md), [file styles](../../../docs/file-colors.md) and the testing guide sections matching the consumer.

Trace inputs through the actual publisher before editing. Defaults, per-theme data and user overlays are source; files beneath current/theme are generated snapshots. Include new inputs in fingerprints and complete new artifacts before pointer publication. Preserve old-generation startup fallback and keep missing optional tools distinct from malformed data.

For Codex/tmux attention styling or Termux toast colors, preserve the [notification preferences and maintenance contract](../../../agents/guides/codex-notifications.md).

Use tools/test_file_colors.py for rules and panels, then selected publication/rollback cases from tools/test_themes.py. Test the real consumer in an owned home; for Yazi include its native theme runner with private DDS sockets. Separate scalar/JSON/Lua bytes from human presentation, and test light/dark foreground/background pairs. Run Termux batches sequentially.

Refresh live state only when the task authorizes it. Source changes alone do not imply permission to switch selections or prune old generations. Record what was published and which native checks actually ran.

Maintain Bash (Termux/Linux/WSL) and native Windows PowerShell 5.1/7 together. Cover matching flags, completion, data output, progress and picker behavior; use native adapters and shared transactions. Follow [PowerShell parity](../../../docs/powershell.md), and distinguish fixture tests from native terminal/desktop evidence.

When this change affects documentation, follow [documentation maintenance](../dots-documentation-maintenance/SKILL.md), including the generated wiki check.
