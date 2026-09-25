# Implementation Plans

Plans describe active, paused, proposed, or completed work. Durable architecture and behavior belong in `docs/`; plans link to those references rather than redefining them.

## Planning Documents

The [roadmap](roadmap.md#current-priority) owns current priorities. Everyday maintenance is active; general Go implementation/migration is paused. The implemented [Anodize slice](anodize.md) is an owner-authorized exception, not a resumption of the general roadmap. A proposed next task is a recommendation until the owner requests implementation.

| Plan | Current role |
| --- | --- |
| [Roadmap](roadmap.md) | Current priorities and retained, paused Go phases. |
| [Anodize](anodize.md) | Implemented core/CLI, local Neovim integration, completions and manual. |
| [Anodize next steps](anodize-next.md) | Proposed foundation hardening, then separately scoped frontend work. |
| [Git and managed files](git-and-file-operations.md) | Implemented bounded operations and quieter discovery. |
| [Files catalog](files-catalog.md) | Implemented catalog; later mutations belong to the Git/files slice. |
| [Omarchy-style themes](omarchy-themes.md) | Implemented flat themes, fixed connectors and explicit wallpaper adapters. |
| [Shared themes](themes.md) | Completed original shared palette slice; historical editor evidence. |
| [Additional theme families](theme-families.md) | Completed family expansion; historical editor evidence. |
| [Configuration paths](config-path-migration.md) | Completed migration; compatibility aliases remain. |
| [Bash dispatcher](bash-dispatcher.md) | Implemented live command framework and three-shell completion. |
| [Zsh startup](zsh-startup.md) | Completed optimization; current regression limits recorded separately. |
| [Worktree lifecycle](worktree-lifecycle.md) | Implemented optional helper; older workflow rules are historical. |
| [Phase 1 portability](phase-1-portability.md) | Completed experiments and historical evidence; remaining gates deferred. |
| [Phase 2 command center](phase-2-command-center.md) | Implemented development Go slices; further implementation paused. |
| [Termux MVP](termux-mvp.md) | Bounded operations exist; general profiles and live MVP drill deferred. |
| [Planning review](planning-review-2026-09-25.md) | Completed consistency review and evidence limits. |

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
