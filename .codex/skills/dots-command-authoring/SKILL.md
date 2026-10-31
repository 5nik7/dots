---
name: dots-command-authoring
description: Create a new Dots command family or subcommand from behavior design through implementation and verification, including Dots presentation, useful configuration and popup integration. Use for new commands; existing-command repairs retain their family maintenance workflow.
---

# Dots Command Authoring

Read the checkout's agent contract and [command guide](../../../agents/guides/commands.md). Inspect existing routes, the [family owner](../../README.md#command-family-owners), nearby implementations and current profile preferences before choosing a design. Keep an existing family's grammar and owner; identify or add a maintenance owner for a new family. This skill coordinates creation across families and does not replace their owners.

## Define the command

Settle the user's outcome and material unknowns after inspecting discoverable facts. Define route/operands, flags, exit statuses, human/data modes and mutation boundaries before editing. Add standalone entry points only when the task calls for them. Use the [command-plan template](assets/command-plan.md) for nontrivial work, keeping decisions and observable acceptance together. Follow actual Codex mode and existing task authorization; an approved implementation request needs no new interview or separate save gate.

Use [command maintenance](../dots-command-maintenance/SKILL.md) for collisions, longest-prefix dispatch, static metadata, contextual completion and frontend parity. Reuse existing shared controllers and native adapters; do not require Bash on native Windows or scan/execute extensions during help, completion or direct dispatch. Keep managed filesystem changes in the existing transaction engine and use the owning workflow for other side effects.

## Carry the user's presentation preferences through

Use [CLI presentation](../dots-cli-presentation/SKILL.md) and the current [presentation contract](../../../docs/presentation.md), including its acceptance gate. Read relevant family exceptions; Todo spacing, key-browser styling and authored palette artwork are scoped preferences, not defaults to spread to every new command.

Choose the existing renderer and named semantic roles for concise headings, labels, muted context, status text and actual resource paths/icons. Resolve current defaults and profile overrides through shared helpers; do not freeze personal colors or glyphs into a command. Preserve readable plain layouts, independent color/icon controls, `NO_COLOR`, terminal detection and explicit overrides. Use appropriate shared progress for slow human work; keep help and routine fast output quiet. Review help, empty results, diagnostics and partial failures as well as successful output. Keep complete identifiers and recovery information usable at narrow widths.

Identify data interfaces explicitly: scalar/path queries, JSON, completion, generated code and raw exports retain exact bytes even under forced decoration. Preserve documented redirected formats. Style only Dots-owned human views; forwarded application output and exact palette previews retain their own contracts.

## Build configuration and popups where useful

Record both required assessments with reasons in the command plan or change notes. An **add** or **update** decision becomes implementation and acceptance work, not a deferred suggestion. A reasoned **no change** decision is valid when the command needs no new integration.

Use [dots-config](../dots-config/SKILL.md) to reuse existing controls and add meaningful missing persistent preferences or visual bindings. Trace each setting from owner/default through storage, inheritance and resolution to its consumer. Wire validation, supported-control catalogs, CLI/completion and configuration-menu details where applicable. Verify effective values, reset, activation and failure recovery; visual refresh and nonvisual reload/install rules remain distinct. Do not expose unused keys, duplicate application settings or turn every invocation flag into a persistent preference.

Use [menu authoring](../dots-menu-authoring/SKILL.md) for repeated browsing, search, selection or guided workflows. Add/update the appropriate family launcher entry when useful. Reuse shared FZF/Gum adapters and existing approval/transaction paths. Preserve exact-client popup ownership, close selectors before handoff, keep previews inert and capture reports once. Test cancellation and missing-tool fallbacks while keeping direct/data modes usable without a popup. Selection never approves a mutation.

## Verify and finish

Implement Bash on Termux/Linux/WSL and native PowerShell surfaces together, recording explicit platform exceptions. Use owned homes, repositories, state, PTYs and tmux clients. Choose the owning component's checks plus metadata/completion tests; run `dots commands --check`. For affected human views, verify 40/80/120 columns, light/dark and plain modes, long/Unicode values, sanitization and exact data under forced decoration. Exercise actual configuration consumers and popup paths when added. Include stale inputs, preview purity, rollback/undo and idempotence where the operation requires them. Native evidence remains separate from fixtures.

Use [documentation maintenance](../dots-documentation-maintenance/SKILL.md) to update metadata-derived help, user/reference docs, the family index when needed, plan status and local wiki. Finish only after the recorded config/menu decisions are implemented or justified, checks pass and remaining native limits are named. Report delivery and activation separately; command authoring does not itself authorize live installation, publication or unrelated changes.

Configuration coverage includes foreground/background, nullable icon styles, labels/values, indentation/tab stops, spacing, alignment and native placement where useful. Follow [dots-config](../dots-config/SKILL.md) for typed controls and consumer verification; use [dots-config-audit](../dots-config-audit/SKILL.md) for requested broad discovery. Preserve native ownership and data output, and record a reason for controls deliberately left unchanged.
