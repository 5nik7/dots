# Repository-local Codex workflows

Skills live here and are discoverable through relative links under .agents/skills.
AGENTS.md remains the operating contract; skills point to maintained project docs.
This directory is not a replacement CODEX_HOME and contains no credentials, model
selection, permission overrides, sessions or machine-local state.

Codex/tmux attention preferences and their maintenance procedure are recorded in the [Codex notification guide](../agents/guides/codex-notifications.md). Preserve that documented user contract when changing notification, title, status or focus handling.

- [dots-theme-maintenance](skills/dots-theme-maintenance/SKILL.md)
- [dots-theme-template](skills/dots-theme-template/SKILL.md) — create default application templates and verify their generated colors in the consumer.
- [dots-shell-integration](skills/dots-shell-integration/SKILL.md)
- [dots-codex-attention](skills/dots-codex-attention/SKILL.md) — maintain cross-session attention, conservative Termux focus and explicit acknowledgement.
- [dots-command-maintenance](skills/dots-command-maintenance/SKILL.md)
- [dots-todo](skills/dots-todo/SKILL.md) — general project/global goal management and progress through the transactional CLI.
- [dots-todo-planning](skills/dots-todo-planning/SKILL.md) — interview about a selected goal, preserve full notes/subtrees and save/implement an agreed linked goal tree after leaving Plan Mode, with progress and verified completion.
- [dots-todo-maintenance](skills/dots-todo-maintenance/SKILL.md) — maintain Todo's CLI, storage, popup and Codex handoffs using the [Todo guide](../agents/guides/todo.md). All three Todo skills are available across projects through their managed resources.
- [dots-cli-presentation](skills/dots-cli-presentation/SKILL.md) — shared CLI layouts, resource colors/icons and progress; preserves custom views and data interfaces.
- [dots-menu-authoring](skills/dots-menu-authoring/SKILL.md) — plan or implement FZF menus using existing selection patterns, a worked example and a copyable plan template; the implemented launcher/session patterns and remaining acceptance work are indexed in the [menu plan](../plans/popup-menus.md).

- [dots-documentation-maintenance](skills/dots-documentation-maintenance/SKILL.md) — align canonical docs with implementation and wiki exports.
- [dots-wiki-maintenance](skills/dots-wiki-maintenance/SKILL.md) — generated pages, sidebar and associated Git workflows.

- [dots-plugin-maintenance](skills/dots-plugin-maintenance/SKILL.md) — portable application plugins, combined installation and receipt-led legacy migration.

- [dots-profile-maintenance](skills/dots-profile-maintenance/SKILL.md) — profile ownership, generated variables/maps, aliases and configuration.
- [dots-files-maintenance](skills/dots-files-maintenance/SKILL.md) — core registry, profile mappings and transactional file operations.
