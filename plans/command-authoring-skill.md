# Command authoring skill

Status: implemented and verified. Goal `343d5be6948e4ee19e18783e5a909b23` (`dots-command-authoring`), normal priority.

Create a repository-local workflow and reusable plan template for new Dots command families and subcommands. The completed skill foundation `1b5eb9b806a843b0b992d92c889d29c3` is a satisfied dependency and remains complete. One root goal covers this bounded task; no children are needed.

## Implementation

Add [dots-command-authoring](../.codex/skills/dots-command-authoring/SKILL.md), its [command-plan template](../.codex/skills/dots-command-authoring/assets/command-plan.md) and relative repository discovery link. Route new-command work from the agent contract, command guide, skill index, command-maintenance skill and contributor references. Keep existing family ownership and canonical preference sources.

The workflow carries command behavior, metadata/completion, Bash/native PowerShell adapters and verification through implementation. It requires shared semantic presentation, current profile controls and preserved data interfaces. Configuration and popup assessments require concrete implementation and consumer/interaction acceptance for add/update decisions; no-change decisions need reasons. Native application ownership, managed transaction/recovery paths and scoped visual exceptions remain intact.

This change adds guidance and discovery only. Configuration assessment: no runtime integration change needed. Menu assessment: no menu change needed. Runtime commands, Windows application destinations and platform support are unchanged. No generator, user-wide installation or live activation is included.

## Acceptance

1. The skill and reusable template cover command creation through implementation, documentation and verification.
2. They enforce current style, color, icon and formatting preferences while preserving data interfaces.
3. They require useful configuration and popup integrations to be implemented, with reasoned no-change decisions where appropriate.
4. Discovery, routing, references, validation and local wiki synchronization pass.

## Verification

Validate new/modified skill definitions and repository discovery links. Check references, family ownership coverage and static command metadata. Walk through a scalar utility, configurable report and interactive managed operation to assess decisions without installing example commands. Run documentation-link and whitespace checks, then preview/build/check the available local wiki. Runtime acceptance for future commands remains part of their own work; these document checks do not establish native Windows or terminal behavior.

Record evidence here and through Todo CLI. Reconcile scoped JSON before every mutation, preserve acceptance and full UUID identity, then mark the goal done only after verification. Preserve unrelated working-tree changes; no commit or push.

### Walkthrough results

Reviewed the skill and filled decision paths from its template for three hypothetical requests. These are instruction walkthroughs, not installed example commands or runtime tests.

| Request | Decisions and required verification |
| --- | --- |
| Return one resolved resource path | Keep the scalar exact under forced color/icons and use styled diagnostics on stderr only. Reuse existing resolution; no new persistent setting or popup is justified. Check literal arguments, missing resources, metadata and both frontends. |
| Report inventory with a persistent visibility preference | Reuse shared presentation controls; integrate the requested behavior preference through its existing owner or a supported new setting. Record type/default/precedence and prove save/reset changes report content while JSON stays valid. Use the existing configuration menu; a separate report popup needs a browsing use case. |
| Select resources for a managed operation | Add the useful family selection/popup workflow, stable identities, inert preview and exact-client handoff. Keep invocation flags transient unless persistent behavior was requested. Selection leads to existing review/confirmation and Store preflight. Check cancellation, missing UI tools, stale input, rollback/undo, idempotence and direct/data modes. |

All paths retain the family owner and applicable native checks. The template requires reasons for no-change decisions and observable outcomes for integrations, avoiding both unused preferences and automatic popups on data commands.

### Checks

Verified on Termux on 2026-10-30:

- Skill-creator validation passed for the new authoring and updated command-maintenance definitions.
- All 26 repository discovery links resolve correctly. Checked 570 Markdown references and 151 anchors across 36 skill/source files.
- The unchanged family map covers 20 top-level routes, including four built-ins. `dots commands --check` passed for all 234 external commands.
- `python3 -B tools/verify_docs.py` passed for 1159 links in 149 files; `git diff --check` passed. Tracked diff sections outside this task match the captured baseline.
- Wiki preview/build changed only the generated Commands page and manifest. Retained transaction `4978783d7dc94c3ba7d6d33c1fb38308`; `dots wiki check` reports healthy.

No runtime behavior or native platform claims changed. Future command implementations must run their own consumer, terminal and native acceptance checks. No user-wide installation, application activation, commit or push occurred.
