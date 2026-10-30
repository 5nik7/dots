# Implementation Plans

Plans describe active, paused, proposed, or completed work. Durable architecture and behavior belong in `docs/`; plans link to those references rather than redefining them.

## Planning Documents

Everyday maintenance and focused feature work are tracked below. A proposed next task is a recommendation until the owner requests implementation.

| Plan | Current role |
| --- | --- |
| [Personal fonts](fonts.md) | Official catalogs, retained versions, per-user registration, app connectors, font/glyph browsers and native acceptance. |
| [Weather command and browser](wttr.md) | Shared standalone/Dots weather, cached-preview browser, session controls and platform acceptance. |
| [Configuration popup](config-popup.md) | Profile/default browsing, typed edits, guarded review and per-change undo. |
| [Profile configuration](profile-configs.md) | Checkout-local settings, file mappings and reversible migration into platform profiles. |
| [Todo goals](todo.md) | Project/global goal tracking, contextual completion, popup, Codex planning handoff and managed general/planning/maintenance skills. |
| [Bundled applications](bundled-applications.md) | Absorb Blastoff and pkgs with dual command forms and combined installation/removal. |
| [Portable plugins](portable-plugins.md) | Consolidated application ownership, backed-up legacy migration, menus and maintenance skills. |
| [Global less colors](less-style.md) | Implemented: exact theme colors for less standout text through shell and popup readers; native runtime acceptance recorded. |
| [Popup menus](popup-menus.md) | G1–G6 complete, including project-aware session actions. G6 corrections add compact previews, Alt-H help, generic automatic Termux sessions and a verified device launch fallback. Native Linux/WSL/Windows and human visual checks remain pending. |
| [Tmux status and sessions](tmux-status-and-sessions.md) | Implemented Termux startup ordering and cross-session Codex attention; selective activation and remaining owner/native acceptance recorded. |
| [Bat custom syntaxes](bat-syntax-cache.md) | Implemented shared syntax snapshots and cache invalidation; Termux checks and live refresh complete, native Windows acceptance pending. |
| [Zsh personal keys](zsh-keys.md) | Implemented centralized ZLE configuration and themed substring-history search; native Termux verification. |
| [Anodize](anodize.md) | Implemented core/CLI, local Neovim integration, completions and manual. |
| [Anodize terminal branding](anodize-logo.md) | Exact LOGO1/LOGO2 defaults, three-stop theme gradients, complete palette panels, explicit alternative rendering and Extract popup. |
| [Anodize next steps](anodize-next.md) | Proposed foundation hardening, then separately scoped frontend work. |
| [Git and managed files](git-and-file-operations.md) | Implemented bounded operations and quieter discovery. |
| [Verbose operations](verbose-operations.md) | File/setup/theme action details with shared resource styling and progress. |
| [Operation progress](progress.md) | Delayed terminal spinners and phase bars across core commands. |
| [Gum confirmations](gum-confirmations.md) | Optional confirmations for file operations, Anodize and Git publish. |
| [File workflow pickers](file-pickers.md) | Shared FZF selection and bounded previews for everyday file commands. |
| [Tracked-config browser](files-browser.md) | Implemented Gum/FZF/plain browser with guarded operation review. |
| [Files catalog](files-catalog.md) | Implemented catalog; later mutations belong to the Git/files slice. |
| [Missing-source check](files-check.md) | Interactive catalog-only cleanup with journaled undo. |
| [Managed file repair](files-repair.md) | Automatic link repair, interactive issue resolution and journaled recovery. |
| [Stash and edit mappings](files-mappings.md) | Disabled resources, mapping edits and the bounded Git XDG migration. |
| [Unified theme CLI](theme-cli.md) | Consolidation on `dots theme` with native palette queries. |
| [Theme shortcuts](theme-command-unification.md) | Generated family commands, collision suffixes and shared completion mappings. |
| [Generated theme files](theme-files.md) | Active-generation inspection, connection checks and read-only browsing. |
| [Shared syntax theme](syntax-theme.md) | Catppuccin reference adaptation, dynamic colors and shared consumer verification. |
| [Theme plugins](theme-plugins.md) | Explicit local hooks and journaled GTK 3/Qt6ct integrations. |
| [Omarchy-style themes](omarchy-themes.md) | Implemented flat themes, fixed connectors and explicit wallpaper adapters. |
| [Git theme colors](git-theme-colors.md) | Shared theme roles for Dots Git metadata and status output. |
| [Leaf UI and syntax](leaf-theme.md) | Semantic template, journaled connectors and local external syntax support. |
| [Shared themes](themes.md) | Completed original shared palette slice; historical editor evidence. |
| [Additional theme families](theme-families.md) | Completed family expansion; historical editor evidence. |
| [Configuration paths](config-path-migration.md) | Completed migration; compatibility aliases remain. |
| [Platform identity cleanup](platform-file-identities.md) | Retired Ruby environment and canonical platform file IDs with legacy recovery. |
| [Shell initialization](shell-init.md) | Unified native shell hooks and startup migration. |
| [User-local shell completions](local-shell-completions.md) | Native directory discovery and user-local precedence in Bash, Zsh and Fish. |
| [Bash dispatcher](bash-dispatcher.md) | Implemented live command framework and three-shell completion. |
| [Common helpers](common-helpers.md) | Consolidated Bash/Zsh helpers, explicit color arrays and migrated callers. |
| [Shared shell utilities](util.md) | Historical utility optimization before consolidation. |
| [Zsh startup](zsh-startup.md) | Completed optimization; current regression limits recorded separately. |
| [Worktree lifecycle](worktree-lifecycle.md) | Implemented optional helper; older workflow rules are historical. |
| [GitHub workflow repairs](ci-repairs.md) | Installation durability, receipt modes and portable CI fixtures; native acceptance tracked separately. |

[Copyable next-agent prompt](prompts/anodize-hardening.md) includes the recommended scope and the owner's recorded working preferences. It does not authorize the current agent to start that future task.

## Presentation Gate for Every Plan

The [presentation contract](../docs/presentation.md) is the single source of truth for cohesive, polished human output under [decision 0009](../docs/decisions/0009-cohesive-command-presentation.md). Every plan inherits it, including completed plans when revisited and paused plans when explicitly resumed. This does not reopen completed work or resume paused implementation.

Before implementing a human view, name its renderer, human/data modes and representative states; include the contract's [acceptance gate](../docs/presentation.md#acceptance-gate) in verification. Review related commands together for consistent layout, labels, status colors and wording. Preserve structured and script-facing output, readable plain fallbacks and explicit presentation preferences. Mark inapplicable cases and unverified coverage rather than claiming project-wide runtime conformance.

## Plan Rules

- State whether a plan is proposed, active, paused, blocked, or completed. A pause describes scheduling, not the implementation status of completed work.
- Define scope, non-goals, dependencies, risks, verification, and acceptance criteria.
- Keep task status current in the same change that completes or changes the task.
- Move durable conclusions into the relevant file under `../docs/`.
- Link decision records for choices that constrain future work.
- Do not leave completed plans as the only documentation for implemented behavior.

When a plan is complete, retain it if it explains migration or decision history. Mark it complete and link the resulting implementation/reference rather than rewriting its original goal.

- [Checkout installation](installation.md): bounded catalog-backed setup, explicit source updates, retained-baseline uninstall and native adapters.

- [Live CLI presentation](cli-presentation.md) — shared resource colors/icons, Git-style views and reusable project skill.

- [Anodize user themes and interactive previews](anodize-interactive.md) — implementation and acceptance for user-default saves, built-in promotion and FZF-assisted authoring.

- [Starship default configuration](starship-default-config.md): approved default-path cleanup and Blastoff link-preserving upgrade.

- [Git info and submodule workflows](git-submodules.md): shared inspection, recursive tree/status and publication scoped to selected child trees.

- [Git identities and named navigation](git-identities-and-navigation.md): shared human identity glyphs, recursive info and contextual submodule actions.

- [Platform profiles and consolidated startup](platform-profiles.md) — active implementation and acceptance.

- [Profile inspection and debug toolkit](profile-debug.md): read-only profile
  routes, source/timing diagnostics and isolated self-tests.

- [Dots wiki](wiki.md) — generated documentation, sidebar, maintenance skills and associated Git operations.

- [Detailed debug tracing](debug-tracing.md) — nested reports, state changes, source maps and opt-in PATH history.

- [Keybinding browser](keys.md) — readable live/configured shortcuts and vi-mode Backspace consistency.

- [Profile presentation and complete inventories](profile-presentation.md): human configuration reports, profile-owned shared mappings and configurable visual roles.

- [Core registry and profile environments](profile-backend.md) — preserve the core resource registry, put implementations in profiles, and generate native path namespaces.
