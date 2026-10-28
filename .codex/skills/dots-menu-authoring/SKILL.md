---
name: dots-menu-authoring
description: Plan or implement Dots FZF menus with shared popup selection, safe command handoff, metadata and native shell parity. Use when adding or changing a Dots launcher or picker; not for unrelated application menus.
---

# Dots Menu Authoring

Start with the requested menu's purpose and the current checkout. Follow [command maintenance](../dots-command-maintenance/SKILL.md) for routes and [CLI presentation](../dots-cli-presentation/SKILL.md) for human/data boundaries. Read the applicable focused plan before implementing it. The [popup-menu plan](../../../plans/popup-menus.md) records the implemented shared library, launcher, shortcuts and session picker; do not advertise a route before its goal lands.

## Define the menu

Every command change needs a recorded menu assessment through command maintenance, even when no popup is appropriate. Reuse or update an existing family before introducing another launcher. Keep application-plugin paths and installation ownership aligned through [plugin maintenance](../dots-plugin-maintenance/SKILL.md).

Use [the copyable menu-plan template](assets/menu-plan.md) when a new menu needs a focused plan. Record the route, stable entry identities, explicit action mappings, data source, terminal ownership, output modes and applicable platform limits. Reuse an existing workflow for actions that already exist. Selection may open its review; it never substitutes for the workflow's approval or journal.

Choose the smallest requested menu. The launcher/session plan's entries and bindings are specific to that feature, not mandatory additions to every menu. Add registry or configuration mechanisms only when the task needs them. Keep missing-information questions limited to choices that change behavior and cannot be resolved from the checkout.

## Reuse verified interfaces

For additions to `dots menu`, prefer an `Action` in the appropriate `FAMILIES` tuple. Add a root group only when the requested scope needs one; let the existing stack handle Back, F1 and query restoration. Use `kind='output'` for reports/help so they are captured once and remain scrollable; keep interactive workflows in `terminal` or cooperating `popup` actions. Use `kind='document'` only for a cooperating interactive controller that hands a prepared page back with `page_text(..., defer=True)`; this closes its selection host before the fitted reader opens. The session kind is a special navigation outcome, not a generic command runner. Git sync's `sync` kind is a specific preview/confirmation workflow, not an automatic mutation approval.

Read [shared APIs and worked examples](references/existing-patterns.md) before adapting the selector. Prefer `menus.Menu`/`Entry`, `choose`, `dots_argv` and `run_action` for new menus. Recheck signatures and caller behavior; existing key/file/theme callers are not automatically migrated.

For row-specific shortcuts, opt into the validated event and focus APIs described in the pattern reference; keep action execution after FZF closes. The project/session browser is an example with explicit mutation confirmations and a platform-specific handoff, not a requirement that other menus manage sessions.

Separate stable identity, sanitized display label and action arguments. Let the shared selector validate numeric tokens; never turn selected display text into shell code. Pass preview snapshots through the established environment/file transport with numeric tokens. Keep previews inert and action execution outside FZF bindings.

For a tmux picker, capture or consume `TmuxContext` only on an interactive path, with an explicit client when a background launcher can supply it. FZF owns its popup. Close it before handing off, and distinguish children that own a popup from children needing an ordinary terminal. A `kind='popup'` child must consume `DOTS_MENU_CONTEXT` through the shared adapter; passing a pane alone does not ensure exact-client targeting. Outside tmux and on native Windows, use the supported terminal path; do not silently invoke WSL.

Keep FZF capability probes inside interactive paths. Preserve the task's documented plain fallback, noninteractive modes and data bytes. Use the shared reader sizing and capture lifecycle rather than opening a fixed-height pager: output captures once in a compact loading host, then the fitted reader opens; prepared messages use `page_text(..., context=context)` directly. When a later action depends on review, use `review_output` and require both `code == 0` and `reviewed` before presenting an explicit default-Cancel confirmation. Reader cancellation is separate from the original command status. Cancel or failed selection cannot approve an action or rerun a workflow. Returning to the parent menu is distinct from retrying its action. Preserve CLI status 130; normalize it only in a shortcut wrapper when that shortcut's contract calls for quiet cancellation.

## Complete the change

Maintain static metadata, longest-prefix routing and native PowerShell dispatch together. Keep optional-tool probes and inventory scans out of help, completion and shell startup. Use current semantic colors and caller presentation settings; do not copy a fixed palette from a screenshot.

Follow the focused plan's [presentation acceptance gate](../../../docs/presentation.md#acceptance-gate) and [test isolation guide](../../../agents/guides/testing.md). Check literal arguments, missing tools, empty/stale results, cancellation, terminal handoff and exact data output where applicable. Use private tmux sockets/PTYs and test-owned roots; record native platform evidence separately from fixtures.

Update canonical docs and the wiki through [documentation maintenance](../dots-documentation-maintenance/SKILL.md). Preserve existing key routes and dirty files. Refresh this skill's pattern reference when a shared menu API actually lands. Ordinary menu authoring does not authorize live reloads, installation, commits or publication; follow the user's existing task authorization.
