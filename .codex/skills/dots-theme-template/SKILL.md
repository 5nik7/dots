---
name: dots-theme-template
description: Create or adapt Dots default application theme templates and connect their generated colors to consumers. Use for new default/themed templates, not general app configuration.
---

# Dots Theme Templates

Read [theme architecture](../../../docs/themes.md), the consumer's current config and the relevant sections of [testing](../../../docs/testing.md). Follow the repository's theme-maintenance workflow for publication and app connectors.

Trace one existing template through `render.bash`, generation preparation and its consumer before adding another. Templates under `default/themed` are source; current/theme files are generated. Preserve personal-template precedence, input fingerprints, and preparation before pointer publication. Add only literal, validated expansions when the existing semantic names cannot express the consumer format; never evaluate template text as shell code.

Map the reference theme's purpose to shared semantic colors instead of copying palette-specific hex values. Use resolved Git roles for Git state colors, including configured overrides. Preserve readable dark/light foreground and background pairs. Document any attributes or fallback colors the consumer cannot represent.

Use [dots-config](../dots-config/SKILL.md) when a connector exposes a configurable binding or changes preference refresh; retain template and application ownership for other inputs. If commands change, record their configuration and menu assessments through [command maintenance](../dots-command-maintenance/SKILL.md).

Keep user identity, credentials, aliases, commands and layout in editable application configuration. Prefer a generated include or existing connector for colors. Use the established transaction/backup mechanism when adding a live connector; source editing and live activation are separate actions unless the task already authorizes both.

Validate every selectable palette for unresolved tokens and format correctness, then exercise the actual application in disposable HOME/config/state/cache roots. Inspect warnings and rendered colors: accepting a config does not prove a custom syntax cache was loaded. Check refresh idempotence, user overrides, missing optional tools and rollback where the integration changes them. Preserve machine-readable output; do not run real credential helpers, user hooks or custom modules as tests.

Update the consumer guide, theme reference and focused tests. Report which native consumers/platforms ran and whether live publication occurred. Do not add a global skill, a second palette source, or an app-specific runtime process when the existing literal generation/connector workflow suffices.

Configuration coverage includes foreground/background, nullable icon styles, labels/values, indentation/tab stops, spacing, alignment and native placement where useful. Follow [dots-config](../dots-config/SKILL.md) for typed controls and consumer verification; use [dots-config-audit](../dots-config-audit/SKILL.md) for requested broad discovery. Preserve native ownership and data output, and record a reason for controls deliberately left unchanged.
