---
name: dots-command-maintenance
description: Maintain Dots command routes, metadata, contextual completion and human/data output. Use when adding commands or changing CLI presentation.
---

# Dots Command Maintenance

For a new family or subcommand, start with [command authoring](../dots-command-authoring/SKILL.md) and its reusable plan template. This skill supplies shared command mechanics and reviews; the selected family skill retains behavior ownership.

Read [command guide](../../../agents/guides/commands.md) and [presentation contract](../../../docs/presentation.md).
For layout and styling work, use [CLI presentation](../dots-cli-presentation/SKILL.md).
For a Dots launcher or picker, use [menu authoring](../dots-menu-authoring/SKILL.md) for selection, popup ownership and terminal handoff patterns.

Select the primary owner in the [family index](../../README.md#command-family-owners); new first-party families must identify or introduce an owner there. For every new or changed command, record **add**, **update**, or **no configuration integration change needed**, with a reason, under the [configuration review](../../../agents/guides/commands.md#configuration-integration-review). Use [dots-config](../dots-config/SKILL.md) for applicable integration work; existing controls may already satisfy the need.

For every new or changed command, assess menu suitability before implementation. Record **add**, **update**, or **no menu** with a short reason in the focused plan or change notes. Prefer menus for repeated selection/browsing or guided workflows; keep scalar/data interfaces and infrequent recovery operations direct unless a menu materially helps. Check existing family entries when a route changes. This review does not authorize running the workflow or adding approval flags.

Keep ordinary dispatch targeted. Static help/completion must not execute extensions. New external routes need matching metadata, argument/option completion, docs and a commands --check pass.

Use tools/test_bash_dots.py cases for dispatch and nonexecution. Use the relevant theme suite for family grammar: --color=MODE decorates output, while --color NAME queries a palette color. Force decoration around scalar/JSON/init outputs to verify their byte contracts. Review 40/80/120-column views and light/dark backgrounds.

Reuse the renderer and optional-interaction adapters. Keep filesystem mutation in its existing transaction engine; a new command must not invent an unjournaled shortcut. Preserve unrelated dirty commands and avoid full concurrent Termux suites.

Maintain Bash (Termux/Linux/WSL) and native Windows PowerShell 5.1/7 together. Cover matching flags, completion, data output, progress and picker behavior; use native adapters and shared transactions. Follow [PowerShell parity](../../../docs/powershell.md), and distinguish fixture tests from native terminal/desktop evidence.

When this change affects documentation, follow [documentation maintenance](../dots-documentation-maintenance/SKILL.md), including the generated wiki check.

Configuration coverage includes foreground/background, nullable icon styles, labels/values, indentation/tab stops, spacing, alignment and native placement where useful. Follow [dots-config](../dots-config/SKILL.md) for typed controls and consumer verification; use [dots-config-audit](../dots-config-audit/SKILL.md) for requested broad discovery. Preserve native ownership and data output, and record a reason for controls deliberately left unchanged.
