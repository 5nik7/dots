# {{COMMAND_TITLE}}

**Status: Proposed.**

Copy into `plans/` for nontrivial new-command work, replace the fields and add it to the plans index. Paths below are repository-relative; turn applicable ones into links relative to the copied plan. Keep decisions and acceptance in this plan; reuse relevant menu-template sections here when needed. This is a planning template, not a command generator.

## Outcome and interface

{{State the user's outcome, audience, authorized delivery scope and observable completion condition. Distinguish source implementation from live activation.}}

Route/family: `{{ROUTE}}`. Primary maintenance skill: `{{FAMILY_OWNER}}` from `.codex/README.md`. Existing controller/grammar to reuse: `{{IMPLEMENTATION}}`. {{Check reserved names, collisions and longest-prefix routing. Identify or add an owner for a new family.}}

{{Define subcommands, operands, flags/defaults, exit statuses and literal argument handling. Include standalone/alias forms only when requested. Identify shared controller and Bash/native PowerShell adapters, static metadata and contextual completion.}}

{{Define human, scalar/path, JSON/raw, redirected and generated-code modes as applicable. Specify new data contracts and stream ownership; do not add decoration or interactive behavior to data output.}}

## Presentation, configuration and menus

Use `docs/presentation.md` and `dots-cli-presentation`. Renderer: `{{EXISTING_RENDERER}}`. {{Describe the intended heading/row/detail layout, named semantic roles, resource icons/colors and relevant family exceptions. Resolve current profile preferences through shared helpers; preserve complete usable values and optional progress.}}

Configuration assessment: **{{add / update / no configuration integration change needed}}**, because {{REASON}}. Follow `agents/guides/commands.md#configuration-integration-review` and `dots-config`.

{{For add/update, record each setting's existing or proposed owner/key/type/default, precedence, consumers/platforms and activation/recovery. Name the validation/catalog, CLI/completion and configuration-menu changes needed. Reuse controls before adding preferences; require an observable consumer check for every new binding. Remove this field when no integration is needed.}}

Menu assessment: **{{add / update / no menu}}**, because {{REASON}}. Follow `dots-menu-authoring`.

{{For add/update, specify the family entry, stable selection identities, data source, action arguments, preview policy, popup/terminal owner and handoff. Record direct/noninteractive paths, cancellation, missing-tool behavior, Back/help and state retention where relevant. Reuse shared selectors/readers and the operation's existing approval path. Remove this field when no menu is needed.}}

## Safety and platforms

{{Classify read-only and mutating operations. Name the existing preview, confirmation, transaction/recovery or domain-specific workflow. Include stale-input handling and failure reporting; no real user paths or external services as fixtures.}}

{{Cover Bash on Termux/Linux/WSL and native PowerShell 5.1/7, Windows application destinations where affected, literal paths and explicit capability exceptions. Preserve fast startup/help/completion and measure changed performance-sensitive paths.}}

## Acceptance and delivery

{{List observable outcomes and dependencies. Add/update config and menu decisions are required implementation work; no-change decisions retain their reasons.}}

Use the presentation acceptance gate: relevant help/result/empty/warning/error/preview/recovery states; 40/80/120-column views; light/dark colors; independent auto/forced/disabled color and icons; `NO_COLOR`, `TERM=dumb`, readable plain output; long paths, spaces, Unicode and control characters; exact data under forced decoration. Mark inapplicable cases with reasons.

{{Name existing focused tests and any needed cases for routing, metadata/completion, actual config consumers, resets/refresh, popup cancellation/fallbacks/handoff, and applicable rollback/undo/idempotence. Use isolated roots/private PTYs. Separate native evidence from fixtures and name pending acceptance.}}

{{Update command metadata, help/completion, user/reference docs, family ownership and plan status. Run `dots commands --check`, documentation-link and whitespace checks, then local wiki preview/build/check. Record verification, remaining limits, final Todo statuses when tracked, and whether authorized activation occurred.}}
