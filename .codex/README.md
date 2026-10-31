# Repository-local Codex workflows

Skills live in `.codex/skills` and are discoverable through relative links under `.agents/skills`. [AGENTS.md](../AGENTS.md) remains the operating contract; skills point to maintained project docs. This directory is not a replacement `CODEX_HOME` and contains no credentials, model selection, permission overrides, sessions or machine-local state.

## Command family owners

This is the authoritative family-to-primary-skill mapping. Select the family owner before changing a command, then use shared skills for affected boundaries. A family skill covers its subcommands, aliases and standalone entry points; static metadata and [command documentation](../docs/commands.md) remain the route inventory. New first-party families must add or identify an owner here in the same change.

| Top-level route | Primary skill |
| --- | --- |
| `anodize` | [dots-anodize-maintenance](skills/dots-anodize-maintenance/SKILL.md) |
| `blastoff` | [dots-blastoff-maintenance](skills/dots-blastoff-maintenance/SKILL.md) |
| `commands` | [dots-command-maintenance](skills/dots-command-maintenance/SKILL.md) |
| `completion` | [dots-command-maintenance](skills/dots-command-maintenance/SKILL.md) |
| `config` | [dots-config](skills/dots-config/SKILL.md) |
| `debug` | [dots-debug-maintenance](skills/dots-debug-maintenance/SKILL.md) |
| `env` | [dots-env-maintenance](skills/dots-env-maintenance/SKILL.md) |
| `files` | [dots-files-maintenance](skills/dots-files-maintenance/SKILL.md) |
| `fonts` | [dots-fonts-maintenance](skills/dots-fonts-maintenance/SKILL.md) |
| `git` | [dots-git-maintenance](skills/dots-git-maintenance/SKILL.md) |
| `help` | [dots-command-maintenance](skills/dots-command-maintenance/SKILL.md) |
| `init` | [dots-shell-integration](skills/dots-shell-integration/SKILL.md) |
| `keys` | [dots-keys-maintenance](skills/dots-keys-maintenance/SKILL.md) |
| `menu` | [dots-menu-authoring](skills/dots-menu-authoring/SKILL.md) |
| `pkgs` | [dots-pkgs-maintenance](skills/dots-pkgs-maintenance/SKILL.md) |
| `profile` | [dots-profile-maintenance](skills/dots-profile-maintenance/SKILL.md) |
| `theme` | [dots-theme-maintenance](skills/dots-theme-maintenance/SKILL.md) |
| `todo` | [dots-todo-maintenance](skills/dots-todo-maintenance/SKILL.md) |
| `wiki` | [dots-wiki-maintenance](skills/dots-wiki-maintenance/SKILL.md) |
| `wttr` | [dots-wttr-maintenance](skills/dots-wttr-maintenance/SKILL.md) |

## Shared and task workflows

Start new command families and subcommands with [dots-command-authoring](skills/dots-command-authoring/SKILL.md) and its [command-plan template](skills/dots-command-authoring/assets/command-plan.md). It coordinates implementation, current presentation preferences, useful config/popup integrations and verification; the table above retains family maintenance ownership.

Every new or changed command records **add**, **update**, or **no configuration integration change needed**, with a reason, under the [configuration integration review](../agents/guides/commands.md#configuration-integration-review). Use [dots-config](skills/dots-config/SKILL.md) for applicable integration work; review does not require adding a setting. Existing command, menu and presentation reviews still apply.

- [dots-command-maintenance](skills/dots-command-maintenance/SKILL.md) covers dispatch, metadata, help, completion and command reviews across families.
- [dots-cli-presentation](skills/dots-cli-presentation/SKILL.md) covers shared human layouts, resource colors/icons and progress while preserving data interfaces.
- [dots-menu-authoring](skills/dots-menu-authoring/SKILL.md) covers shared FZF selection, popup ownership and terminal handoff, with a plan template and verified patterns.
- [dots-plugin-maintenance](skills/dots-plugin-maintenance/SKILL.md) covers portable application ownership, installation assets and receipt-led migration. Use the application's family skill for its own behavior.
- [dots-theme-template](skills/dots-theme-template/SKILL.md) covers generated application templates and consumer verification.
- [dots-codex-attention](skills/dots-codex-attention/SKILL.md) preserves the [notification contract](../agents/guides/codex-notifications.md), focus handling and explicit acknowledgement.
- [dots-documentation-maintenance](skills/dots-documentation-maintenance/SKILL.md) aligns canonical docs with implementation; [dots-wiki-maintenance](skills/dots-wiki-maintenance/SKILL.md) handles generated exports and associated Git workflows.
- [dots-todo](skills/dots-todo/SKILL.md) manages goals through the transactional CLI. [dots-todo-planning](skills/dots-todo-planning/SKILL.md) interviews in actual Plan Mode and saves/implements an agreed linked tree in execution mode. These are separate from Todo implementation maintenance; all three Todo skills retain their existing managed resources for cross-project use.

## Discovery and maintenance

Add a skill as `.codex/skills/NAME/SKILL.md` with accurate `name` and `description` frontmatter, then create `.agents/skills/NAME` as the relative link `../../.codex/skills/NAME`. Keep instructions focused on component ownership, non-obvious constraints and meaningful verification; link shared procedures instead of copying them. Check referenced paths, validate changed skills with the skill-creator validator, and compare this table against first-party static command metadata, including built-ins. Audit affected existing skills when responsibility changes.

These links expose workflows within the repository. Installing additional user-wide skills is a separate managed-file task; ordinary skill authoring does not edit user configuration or install links into `CODEX_HOME`. Source docs and the wiki follow the [documentation guide](../agents/guides/documentation.md).

Use [dots-config-audit](skills/dots-config-audit/SKILL.md) for requested repository-wide configuration discovery, with the read-only `tools/audit_config.py` helper. It reviews colors, icons, formatting/placement and application controls before routing approved integration to the owning skill. It is available through the repository `.agents/skills` link; no user-wide installation is implied.
