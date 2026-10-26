# {{MENU_TITLE}}

**Status: Proposed.**

Copy this template into `plans/`, replace the `{{...}}` fields, remove inapplicable cases and add the resulting plan to the plans index. Paths below are repository-relative references; turn applicable ones into links relative to the new plan. This template defines a plan, not executable menu code.

## Outcome and boundaries

{{Describe the user's task, what selection accomplishes, the audience and the concrete completion condition.}}

{{Record authorized delivery scope and excluded actions. Distinguish planning, source implementation and live activation.}}

## Route and entries

Proposed route: `{{ROUTE}}`. Existing implementation to reuse: `{{CURRENT_CONTROLLER_OR_WORKFLOW}}`.

| Stable identity | Display label | Data source | Explicit action and arguments | Availability |
| --- | --- | --- | --- | --- |
| {{ENTRY_ID}} | {{LABEL}} | {{SOURCE}} | {{ACTION}} | {{CAPABILITY_OR_PLATFORM_RULE}} |

{{Define ordering, initial query, selection/back/exit behavior, and whether the menu returns after a child finishes. Record whether summaries come from static metadata. For a launcher addition, reuse its family stack, compact icon/name rows, F1 help and per-menu query restoration; identify any deliberate exit exception.}}

{{Define supported flags, human/printed/redirected/JSON modes, empty results and error statuses. For new JSON, specify its exact versioned contract before exposing it.}}

## Interaction and action boundary

{{Name the existing renderer/selector or explicitly proposed shared helper; separate identity from display text and action arguments.}}

{{Specify who owns the popup/terminal, how initiating client/pane/cwd context survives handoff, how reports reuse the fitted scrollable reader and preserve command status separately from reader cancellation, whether a document needs deferred handoff, and behavior outside tmux.}}

{{Specify missing-tool behavior, cancellation versus actual errors, stale selections and literal-argument handling. Previews must remain inert.}}

{{Name the existing review/confirmation/transaction path if an action can mutate state. Selection alone is not approval.}}

## Platforms and compatibility

{{Record Bash and native PowerShell routes/metadata/completions, Windows application destinations or their lack of change, and any explicit unsupported operations.}}

{{Record existing routes, shortcuts, data interfaces and performance-sensitive paths that must be preserved. Note proposed binding collisions and activation scope.}}

## Goals

| Goal | Status | Dependencies | Completion evidence |
| --- | --- | --- | --- |
| {{GOAL}} | Proposed | {{DEPENDENCIES}} | {{OBSERVABLE_RESULT}} |

## Validation and documentation

Use `docs/presentation.md` and its acceptance gate. Choose applicable populated/empty/error cases, 40/80/120-column views, light/dark colors, plain icons/colors and exact undecorated data checks.

Use `agents/guides/testing.md` for owned home/config/state/cache/repository roots and private tmux servers/PTYs. Cover relevant cancellation, missing dependencies, literal arguments, stale data, multi-client targeting, terminal handoff and nonexecuting help/completion/preview cases. Record real native evidence separately from fixtures and named pending checks.

{{List existing runnable checks and label new test runners proposed until created. Document benchmark needs only where startup/dispatch/planning changes.}}

{{Name affected command metadata, completion tests, user/reference docs and plan status updates. Use canonical sources and normal wiki preview/build/check; preserve existing changes.}}

## Evidence

{{Record completed checks, pending acceptance, remaining risks and whether live activation occurred. Proposed behavior must remain labeled until implemented.}}
