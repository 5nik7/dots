---
name: dots-command-maintenance
description: Maintain Dots command routes, metadata, contextual completion and human/data output. Use when adding commands or changing CLI presentation.
---

# Dots Command Maintenance

Read [command guide](../../../agents/guides/commands.md) and [presentation contract](../../../docs/presentation.md).
For layout and styling work, use [CLI presentation](../dots-cli-presentation/SKILL.md).

Keep ordinary dispatch targeted. Static help/completion must not execute extensions. New external routes need matching metadata, argument/option completion, docs and a commands --check pass. Do not resume the paused Go migration for a Bash CLI change.

Use tools/test_bash_dots.py cases for dispatch and nonexecution. Use the relevant theme suite for family grammar: --color=MODE decorates output, while --color NAME queries a palette color. Force decoration around scalar/JSON/init outputs to verify their byte contracts. Review 40/80/120-column views and light/dark backgrounds.

Reuse the renderer and optional-interaction adapters. Keep filesystem mutation in its existing transaction engine; a new command must not invent an unjournaled shortcut. Preserve unrelated dirty commands and avoid full concurrent Termux suites.
