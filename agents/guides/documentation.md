# Documentation Work Guide

Read this guide when changing project documentation or when implementation work affects documented behavior.

## Documentation Layers

- `AGENTS.md` — concise project-wide rules and routing.
- `agents/guides/` — task procedures: what to read and do when changing an area.
- `docs/` — canonical user guides and durable architecture/behavior references; mapped documents generate the wiki.
- `plans/` — scoped sequencing, acceptance criteria, open questions, and status.
- `README.md` — compact project introduction, essential setup, first commands and documentation navigation.
- `.codex/README.md` — authoritative command-family skill ownership; `.codex/skills/` holds focused workflows discovered through `.agents/skills/` links.

Do not turn `AGENTS.md` into an exhaustive design document. Link to the authoritative reference instead.

## Root README Policy

The main `README.md` is a compact getting-started page. Keep the existing light/dark logo, a short introduction and platform summary, a prominent wiki link, safe Bash and native PowerShell checkout/install examples, a few first commands and brief contributor links. Link fresh-machine bootstrap, detailed prerequisites, updates and uninstall to the installation guide. Aim for roughly 350–450 words; content relevance matters more than an exact count.

Update the README only when those introductory claims, setup steps, first commands or navigation need to change. A new feature, setting, command, bug fix or user-visible behavior does not by itself require a README addition. Put detailed usage, options, appearance controls, platform caveats and troubleshooting in the appropriate canonical topic guide, and verification history or pending acceptance in the focused plan. Keep the README's links useful without duplicating the wiki's topic inventory.

During documentation delivery, record **README update** or **no README change needed**, with a short reason in the focused plan or change notes. When shortening the README, confirm that useful details already exist in their topic guides and move any missing information before removing it. Preserve relevant uncommitted additions through that same check. Review additions against this policy instead of appending a feature announcement or change log.

This policy applies to the root README. Application, directory, documentation-index and skill-index READMEs keep their specialized roles. Older plan/checklist wording that requires README updates for every user-facing change is superseded by this relevance review; completed records remain historical evidence.

## Status Language

Use status labels consistently:

- **Implemented** — present and verified in the repository.
- **Proposed** — intended direction that may still change.
- **Draft** — incomplete specification requiring decisions or validation.
- **Paused** — further work is on hold until the owner requests resumption; this scheduling status does not change whether existing functionality is implemented.
- **Deprecated** — still present for compatibility with a documented replacement.
- **Removed** — historical only; do not show as usable.

Never place a proposed installation command in the README as if it is safe to run.

## Synchronization Matrix

| Change | Required documentation |
| --- | --- |
| Component or directory ownership | `docs/architecture.md` |
| Product invariant or priority | `docs/principles.md`, plus a decision record when material |
| Command, flag, help, output, or metadata | `docs/commands.md`, affected topic guides and generated reference; apply the [root README policy](#root-readme-policy); `docs/presentation.md` owns shared human output policy |
| Project introduction, essential setup, first commands or documentation navigation | Root README when affected, under the [root README policy](#root-readme-policy) |
| Data schema, variable, or precedence | `docs/specification.md` |
| Mutation, backup, rollback, force, package, or secret handling | `docs/safety.md` |
| Platform paths, detection, capability, or limitation | `docs/platforms.md` |
| Test runner, safety case, benchmark, or CI claim | `docs/testing.md` |
| Milestone, scope, dependency, or open question | Applicable file under `plans/` |
| Command maintenance ownership or skill workflow | `.codex/README.md`, affected skills/discovery links and task guide; `AGENTS.md` for project-wide requirements |

## Style

- Write complete sentences and use direct language.
- Do not hard-wrap prose at an arbitrary column; break at structural boundaries.
- Use relative links for repository files.
- Prefer tables for exact mappings and comparisons.
- Mark examples as conceptual when the command or manifest is not implemented.
- Keep one authoritative exhaustive list and link to it elsewhere.
- Use `Termux`, `Linux`, `WSL`, `Windows`, `PowerShell`, `Bash`, and `Zsh` consistently.
- Spell the project and command as lowercase `dots` except at the beginning of a title.

## Plans and Decisions

- Plans are living documents while work is active.
- Every plan inherits the [presentation gate](../../plans/README.md#presentation-gate-for-every-plan). Link the shared contract rather than maintaining separate palettes or layout rules, and distinguish accepted requirements from verified runtime coverage.
- Update checkboxes and status in the same change that completes or changes work.
- Move durable conclusions from a plan into the relevant reference document.
- Record a material architectural decision in `docs/decisions/` rather than leaving its reasoning only in chat or a completed plan.
- Do not rewrite a decision record to hide history; add a superseding decision.

## Verification

Before finishing a documentation change:

1. Run `git diff --check`.
2. Verify every relative Markdown link resolves.
3. Search for stale names, paths, and status claims.
4. Confirm examples do not imply unimplemented behavior.
5. Confirm repeated lists have a named source of truth.
6. Update the applicable plan status.
7. For accompanying command changes, verify the recorded [configuration review](commands.md#configuration-integration-review), menu assessment and [family owner](../../.codex/README.md#command-family-owners). Use [dots-config](../../.codex/skills/dots-config/SKILL.md) for applicable integrations. Pure documentation changes need no new setting or assessment of unchanged commands.
8. Record the README relevance decision under the [root README policy](#root-readme-policy). For a README edit, verify the logo assets, linked wiki page IDs/anchors and both shell examples; check that removed details remain in their canonical guides.

For skill changes, validate each new/modified skill with the available skill-creator validator, check its references and relative discovery link, and compare family coverage with static command metadata including built-ins. Keep shared requirements in the task guide and link to them from skills; do not create competing configuration or subcommand inventories.

For bounded Git/file operations, synchronize `docs/git.md`, `docs/files.md`, `docs/safety.md` and the focused Git/file plan. Do not describe optional retained snapshots as required for every operation or imply that Git publication has atomic rollback.

## Dual-shell maintenance

Every first-party change must cover Bash on Termux/Linux/WSL and native Windows PowerShell 5.1/7: routes, flags, aliases, contextual completion, exact data output, styled human output, progress and optional pickers. Keep native filesystem/app differences in adapters and reuse transactions. Read [native PowerShell](../../docs/powershell.md); update its capability limits and the [parity plan](../../plans/powershell-parity.md) when affected. Run focused isolated tests for both controller paths, require actual PowerShell engines in Windows CI, and report missing native/desktop evidence explicitly.

Wiki documentation is generated from canonical Dots sources. For behavior/documentation changes, update source docs, then rebuild and check the wiki when its checkout is available; otherwise run source-only validation and report synchronization pending. Use the `dots-documentation-maintenance` and `dots-wiki-maintenance` skills and follow [the wiki guide](wiki.md). Documentation work does not authorize commits or pushes.
