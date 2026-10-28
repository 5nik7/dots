---
name: dots-command-maintenance
description: Maintain Dots command routes, metadata, contextual completion and human/data output. Use when adding commands or changing CLI presentation.
---

# Dots Command Maintenance

Read [command guide](../../../agents/guides/commands.md) and [presentation contract](../../../docs/presentation.md).
For layout and styling work, use [CLI presentation](../dots-cli-presentation/SKILL.md).
For a Dots launcher or picker, use [menu authoring](../dots-menu-authoring/SKILL.md) for selection, popup ownership and terminal handoff patterns.

For every new or changed command, assess menu suitability before implementation. Record **add**, **update**, or **no menu** with a short reason in the focused plan or change notes. Prefer menus for repeated selection/browsing or guided workflows; keep scalar/data interfaces and infrequent recovery operations direct unless a menu materially helps. Check existing family entries when a route changes. This review does not authorize running the workflow or adding approval flags.

Keep ordinary dispatch targeted. Static help/completion must not execute extensions. New external routes need matching metadata, argument/option completion, docs and a commands --check pass.

Use tools/test_bash_dots.py cases for dispatch and nonexecution. Use the relevant theme suite for family grammar: --color=MODE decorates output, while --color NAME queries a palette color. Force decoration around scalar/JSON/init outputs to verify their byte contracts. Review 40/80/120-column views and light/dark backgrounds.

Reuse the renderer and optional-interaction adapters. Keep filesystem mutation in its existing transaction engine; a new command must not invent an unjournaled shortcut. Preserve unrelated dirty commands and avoid full concurrent Termux suites.

Maintain Bash (Termux/Linux/WSL) and native Windows PowerShell 5.1/7 together. Cover matching flags, completion, data output, progress and picker behavior; use native adapters and shared transactions. Follow [PowerShell parity](../../../docs/powershell.md), and distinguish fixture tests from native terminal/desktop evidence.

When this change affects documentation, follow [documentation maintenance](../dots-documentation-maintenance/SKILL.md), including the generated wiki check.
