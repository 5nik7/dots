---
name: dots-anodize-maintenance
description: Maintain Dots Anodize palette authoring, its CLI, previews and engine integration. Use for changes to dots anodize or bundled Anodize; use theme maintenance for ordinary palette publication and connectors.
---

# Dots Anodize Maintenance

Read [Anodize](../../../docs/anodize.md), [authoring boundaries](../../../docs/decisions/0011-anodize-authoring.md) and the affected [plan](../../../plans/anodize.md). `plugins/anodize/cli.py`, `authoring.py` and `interactive.py` own Python authoring/workflows; `integration.py` bridges Dots. The reusable Go package under `plugins/anodize/engine` owns palette algorithms without filesystem/process access. Keep native invocation and mutation outside that package.

Standalone `anodize` and `dots anodize` share behavior. Help must work without a built engine; authoring uses a prebuilt engine and never builds/downloads it at runtime or startup. Saving a user theme is separate from applying it. Preserve user-default saves, explicit built-in promotion, literal imports/exports, preview purity and retained transactions; use [theme maintenance](../dots-theme-maintenance/SKILL.md) for publication/connectors and [plugin maintenance](../dots-plugin-maintenance/SKILL.md) for installed assets.

Follow [command maintenance](../dots-command-maintenance/SKILL.md) for config/menu assessments and frontend parity, and [dots-config](../dots-config/SKILL.md) for any configuration integration. Palette definitions and authored artwork keep their own ownership. Preserve the exact LOGO1/LOGO2 contract and candidate palette/background in previews; raw exports, app config and completion remain undecorated. Use [menu authoring](../dots-menu-authoring/SKILL.md) for interactive reader handoffs.

Choose checks from `tools/test_anodize.py`, `tools/test_anodize_integration.py`, `tools/test_anodize_interactive.py`, `tools/test_anodize_logo.py` and `tools/test_native_anodize.py` according to the changed boundary. Engine work follows `tools/verify_anodize.py` and its documented build/check workflow; do not silently install Go or use the user's active theme as a fixture. Generated metadata is checked with `python3 -B tools/generate_anodize_integration.py --check`. Verify saves versus activation, cancellation, literal output, rollback and native runtime limits. Finish through [documentation maintenance](../dots-documentation-maintenance/SKILL.md).
