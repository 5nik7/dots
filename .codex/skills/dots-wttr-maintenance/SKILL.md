---
name: dots-wttr-maintenance
description: Maintain Dots wttr weather reports, cache/provider behavior, widgets and browser. Use for dots wttr and standalone wttr implementation; Android location providers and terminal notification behavior retain their own owners.
---

# Dots Weather Maintenance

Read [weather behavior](../../../docs/wttr.md) and the [weather plan](../../../plans/wttr.md). `lib/dots/wttr/commands.py` owns grammar, `core.py` owns custom JSON/provider/cache behavior, `stock.py` owns curl passthrough, and styling/browser/completion remain separate. Standalone and Dots forms share the controller; keep stock bytes, upstream JSON and scalar fields undecorated.

Preserve explicit location, configured default and existing Termux city-helper precedence; no implicit IP fallback or direct Android-provider access. Config selection remains explicit file, platform user configuration, then checkout default. Normal foreground refresh may acquire location through the helper; widget/format/daylight paths use its cached-location surface even during refresh. Keep deadlines, cooldowns, stale-data bounds and unavailable states honest; do not leak provider stderr or coordinates into diagnostics.

Opening/filtering/previewing the browser reads caches without provider calls, locks or refresh workers. Reports and explicit Refresh use the documented refresh policy. Session location/units changes do not save configuration. Fallback to an ordinary report can refresh data and must retain that report's status. Preserve exact-client popup ownership, single report capture, cancellation and query/session state.

Follow [command maintenance](../dots-command-maintenance/SKILL.md) for config/menu review and [dots-config](../dots-config/SKILL.md) for Dots integration. Native weather options and condition artwork keep their owners; shared detail icons/styles use the established visual bindings. Use [menu authoring](../dots-menu-authoring/SKILL.md) for browser changes. Tmux widgets must escape literals and restore incoming colors/attributes.

Run `tools/test_wttr.py`, `tools/test_wttr_browser.py` and `python3 -B tools/generate_wttr_commands.py --check`; add affected tmux/Android adapter checks for clock changes. Fixtures own roots and mock geo/HTTP/curl; do not use live weather, coordinates, permissions or the user's tmux server. Cover cache failures/recovery, provider-free previews/help, literal locations, raw/stock compatibility and narrow-terminal views. Report native Windows limits and finish through [documentation maintenance](../dots-documentation-maintenance/SKILL.md).

Configuration coverage includes foreground/background, nullable icon styles, labels/values, indentation/tab stops, spacing, alignment and native placement where useful. Follow [dots-config](../dots-config/SKILL.md) for typed controls and consumer verification; use [dots-config-audit](../dots-config-audit/SKILL.md) for requested broad discovery. Preserve native ownership and data output, and record a reason for controls deliberately left unchanged.
