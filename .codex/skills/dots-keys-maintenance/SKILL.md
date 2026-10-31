---
name: dots-keys-maintenance
description: Maintain dots keys provider snapshots, live/configured evidence, key notation and browsing. Use for the Dots keybinding inspector; changing an application's actual bindings belongs to that application's configuration workflow.
---

# Dots Keys Maintenance

Read [keybinding inspection](../../../docs/keys.md) and [its safety boundary](../../../docs/safety.md#keybinding-inspection). `lib/dots/keys_cli.py` routes into `keys/model.py`, `providers.py`, `presentation.py` and `browser.py`; `codex.py` and `zsh_bridge.py` handle specialized evidence. Bundled data under `keys/data` is reference material with provenance, not proof of a running application's state.

Never execute a selected binding, evaluate returned shell/Lua code, start an app/server to load plugins or download defaults while browsing. Preserve live/configured/default/unknown distinctions and omit shell macro/command and Lua function bodies. Query only the selected provider for direct routes. Capture one snapshot for category counts, rows and mode switching so they remain consistent; browser navigation does not silently recollect data.

Native shell adapters own on-demand caller-map transport. The Zsh bridge uses existing private, bounded IPC and idle/source-pane identity checks, not injected keystrokes or code evaluation. Busy, ambiguous or unsafe endpoints fall back to configured evidence. Preserve exact key notation, stable identities, application/mode filters, descriptions/provenance and full values in details/JSON while fitting human rows.

Follow [command maintenance](../dots-command-maintenance/SKILL.md) for config/menu review, [dots-config](../dots-config/SKILL.md) for visual/configuration bindings and [menu authoring](../dots-menu-authoring/SKILL.md) for popup ownership and handoff. Changes to real shell bindings also require [shell integration](../dots-shell-integration/SKILL.md).

Use `tools/test_keys.py`, `tools/test_keys_browser.py`, `tools/test_keys_defaults.py` and affected `tools/test_keys_ipc.py`, `tools/test_keys_zle.py` or `tools/test_tmux_keys.py` cases. Fixtures must own shells, sockets, snapshots and application substitutes. Verify nonexecution, no-server behavior, timeout/fallback, accurate counts/modes, cancellation, literal data and 40/80/120-column views. Record native PowerShell/desktop limits and finish through [documentation maintenance](../dots-documentation-maintenance/SKILL.md).
