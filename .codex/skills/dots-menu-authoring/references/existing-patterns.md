# Existing Dots menu patterns

These interfaces exist in the inspected checkout. The shared library, terminal host, launcher registry and session-picker route are implemented; remaining acceptance is tracked in the [popup-menu plan](../../../../plans/popup-menus.md). Use this reference to find the maintained implementation, not as a second copy of its API.

## Implementation map

Dedicated appearance comes from [popup configuration](../../../../lib/dots/menu_popup.py): `apps.menu.popup.position`, `border` and `colors`. Shared FZF selectors and native tmux hosts apply it on their next invocation, retaining caller dimensions in auto mode and exact-client context. Ordinary FZF border flags cannot hide or replace the Dots frame. Use [documented controls](../../../../docs/profiles.md#dots-popup-appearance) instead of duplicating popup styles in a controller.

Width/height default to `auto`; explicit `fit`/`fill`, percentages and cell counts use the shared bounded sizing helper. `selector_environment` carries addressed-client dimensions so a background controller does not substitute another terminal's size. Keep content measurement inert, leave preview/terminal layout to its owner when unknown, and use `menu_pager` bounds for reports.

`menus.choose` resolves popup dimensions before final percentage columns and passes `popup_resolved=True` to `RichSelector.fzf`, preventing a second fit calculation from changing the column basis. Use that low-level flag only after applying the shared sizing preferences against the verified client; ordinary callers retain selector-owned sizing. Inert content measurement counts each trusted display line while numeric selection records remain NUL-delimited.

| Concern | Current source and useful entry points |
| --- | --- |
| Shared menu records and selection | [menus.py](../../../../lib/dots/menus.py): `Entry`, `Menu`, `add_arguments`, `dimensions`, `choose`, `dots_argv`, `run_action`, `review_output`. |
| Curated launcher | [menu_cli.py](../../../../lib/dots/menu_cli.py): `Action`, `ACTIONS`, `FAMILIES`, static `launcher` construction and selection/dispatch in `run`; [test_menu_launcher.py](../../../../tools/test_menu_launcher.py) covers all handoff kinds and actual shortcut lines. |
| Implemented session menu | [menu_sessions.py](../../../../lib/dots/menu_sessions.py): `Server.discover`, `sessions`, `select`, typed session JSON and `main`; [test_menu_sessions.py](../../../../tools/test_menu_sessions.py) exercises both frontends and private native switch/attach. |
| Exact tmux context and terminal host | [menu_tmux.py](../../../../lib/dots/menu_tmux.py): `TmuxContext.capture`, `from_environment`, `verify`, `popup`, `host`, `output`; [menu_host.py](../../../../lib/dots/menu_host.py): private transport worker. |
| Shared menu contracts and native fixtures | [test_menus.py](../../../../tools/test_menus.py): inert output, literal argv, cleanup and two-client FZF/terminal-host checks. |
| FZF selection | [interaction.py](../../../../lib/dots/interaction.py): `RichSelector.fzf`, `SelectionEnded`, `rich_fzf_available`, `terminal`. |
| Shared human rendering and colors | [catalog.py](../../../../lib/dots/files/catalog.py): `Presentation`; [picker.py](../../../../lib/dots/files/picker.py): `fzf_colors`. |
| Category sizing and identities | [keys/presentation.py](../../../../lib/dots/keys/presentation.py): `menu_rows`, `menu_dimensions`, `MENU_HEADER`. |
| Category selection and binding preview | [keys_cli.py](../../../../lib/dots/keys_cli.py): `picker_ui`, `choose_category`, `browse`. |
| Static route headers | [dots-keys](../../../../bin/dots-keys), [dots-menu-tmux-keys](../../../../bin/dots-menu-tmux-keys), [command_metadata.py](../../../../lib/dots/command_metadata.py). |
| Native first-party dispatch | [cli.py](../../../../lib/dots/cli.py): mappings to the same Python controllers; no Bash dependency on native Windows. |
| Shortcut context and cancellation | [tmux.conf](../../../../config/tmux/tmux.conf): inspect the current Prefix ? launcher, including its target-pane bridge. |
| Isolated interaction examples | [test_keys.py](../../../../tools/test_keys.py), [test_tmux_keys.py](../../../../tools/test_tmux_keys.py), [test_file_pickers.py](../../../../tools/test_file_pickers.py), [test_native_cli.py](../../../../tools/test_native_cli.py). |

`RichSelector.pick` requires terminal streams and may use its existing fallback chain. `RichSelector.fzf` accepts explicit popup sizing and is used directly after the key browser's capability/context checks. Do not assume the low-level call provides those checks. It returns validated list indexes, not selected label strings, and raises `SelectionEnded(130)` on cancellation. It isolates FZF defaults and handles native preview-shell selection.

`RichSelector.pick(..., include_cancel=False)` lets a controller supply its own first Back/Cancel entry without a duplicate fallback Cancel row; Escape/Ctrl-C still abort. Existing callers retain the default injected Cancel. The [repair helper](../../../../lib/dots/files/repair_picker.py) uses this option with metadata-only previews and a guarded decision queue, followed by separate transaction approval. It runs in the invoking terminal and does not introduce a popup host.

The key browser opts into `info`, `initial_indices`, `navigation` and `navigation_keys` on `RichSelector.fzf`. The optional event map replaces the default Escape/F1 navigation events; query capture works even with an empty result set. Ctrl-C remains cancellation. Its [mode selector](../../../../lib/dots/keys/browser.py) closes the binding popup before opening a compact chooser, then restores the binding query. Numeric indices always refer to the original snapshot. `hscroll=False` anchors columns and `preview_position` keeps width budgeting consistent with pane placement. Other callers retain their defaults. The [browser tests](../../../../tools/test_keys_browser.py) cover mode navigation, previews and native terminal behavior.

## Worked example: adding a menu with the shared library

To add an explicitly requested workflow, add an `Action` to the appropriate `menu_cli.FAMILIES` tuple after implementing its normal route and static header. `route` contains command words; `options` contains fixed extra arguments. Use `kind='output'` for scrollable reports, `terminal` for interactive workflows, and `popup` only for a child that consumes the private context. A `submenu` action names another family; the shared stack handles Back, F1, new-child query reset and parent query restoration. The optional `tool` field checks executable presence without running it. Update mapping tests and command docs; never enroll arbitrary extensions automatically.

For a new requested family, the following is a conceptual registration fragment, not an installed workflow. Existing families need only the leaf addition. Help is appended by `actions()` automatically:

```python
from menu_cli import Action, group
# Add to ACTIONS only when a new root family is wanted:
root_entry = group('example', '󰈔')
# Add this tuple as FAMILIES['example']:
family_entries = (
    Action('status', 'status', ('example', 'status'), kind='output'),
)
```

`choose(..., compact=True, navigation=frame, prompt="dots·example")` returns inert entries and updates the frame's query. The optional prompt replaces only the interactive prompt stem and its sizing; the selector adds `: ` and printed/JSON titles stay intact. The launcher already derives the stem from its family path, so new family registrations inherit it without extra title code. Delegated pickers keep their own prompts. `SelectionEvent('back'|'help')` is separate from `SelectionEnded(130)` (menu Ctrl-C). Ordinary selectors retain their existing cancellation behavior. The launcher consumes delegated cancellation and returns to its menu. Only a completed session choice closes it; `menu_sessions.browse` returns an explicit internal outcome to distinguish empty inventories from success.

The [output reader](../../../../lib/dots/menu_pager.py) captures a report once, pages complete stdout/stderr with less or a read-only FZF fallback and cleans private files. The reader scopes UTF-8/private-use character handling to less so Nerd Font icons render without modifying command output or global pager settings. Use `run_action(..., kind='output', title='...')`; do not pipe a command to a pager or use the pager's exit status as the command's result. In tmux the loading host captures and prepares output, then closes before the parent opens a reader fitted to display rows (six-row minimum, 90% height cap). `review_output` returns `OutputResult(code, reviewed)` when a later decision needs normal dismissal as well as command success; require both before offering a separate confirmation. Git sync uses this gate, then default-Cancel selection, without adding approval flags. `page_text(..., context=context)` opens prepared messages directly at the fitted size. For a cooperating interactive document controller, register `kind='document'` and call `page_text(..., defer=True)` after selection; the private handoff closes its selection host before the parent opens the reader. Without that handoff, `page_text` reads inline. Preserve direct raw/data modes. [Reader tests](../../../../tools/test_menu_pager.py) exercise cleanup and status separately from navigation.

This is a controller fragment for a new menu, not an installed command. It uses only implemented APIs. Keep actions outside display records and capture tmux context only after deciding the invocation is interactive:

```python
import argparse
import os
from interaction import terminal
from menus import Entry, Menu, add_arguments, choose, dots_argv, run_action
from menu_tmux import TmuxContext

parser = argparse.ArgumentParser()
add_arguments(parser)
args = parser.parse_args()
menu = Menu('example', 'Example workflows', (
    Entry('files', 'Tracked configs', 'Inspect configs and review changes'),
))
interactive = args.menu_mode == 'browse' or (
    args.menu_mode == 'auto' and terminal() and os.environ.get('TERM') != 'dumb'
)
context = TmuxContext.from_environment() if (
    interactive and os.name != 'nt' and os.environ.get('TMUX')
) else None
entry = choose(menu, mode=args.menu_mode, query=args.query, context=context)
result = run_action(dots_argv(['files', 'browse']), context=context) if entry else 0
```

Handle `SelectionEnded` with its existing status and report real errors on stderr at the command boundary. `dots_argv` selects the checkout's Bash executable or native Python frontend; it never evaluates a command string. The returned entry identifies a trusted controller-owned action, not an approval. The [snapshot contract](../../../../docs/specification.md#shared-menu-records) excludes argv, icons and private environment.

For a static result use `run_action(..., kind='output', context=context, title='Report title')`; an ordinary interactive workflow uses the default `terminal` kind. A child that owns its own popup uses `kind='popup'` and must consume the inherited private context via `TmuxContext.from_environment()` before calling `choose`. The key browser and session picker consume that context. Other popup-owning children must implement consumption explicitly; the environment variable alone does not adapt a caller.

## Worked example: the existing key category chooser

This excerpt illustrates the current category flow after `picker_ui`, FZF availability checks and collection of the source/default-filtered snapshot. It is a reference fragment, not a standalone command or a new menu framework:

```python
from interaction import RichSelector
from files.picker import fzf_colors
from keys.presentation import menu_rows, menu_dimensions, binding_prompt, picker_colors, MENU_HEADER

rows = menu_rows(ui, coverage)  # Positive counts; stable identity plus styled label.
labels = [label for _, label in rows]
width, height = menu_dimensions(labels)
selected = RichSelector().fzf(
    binding_prompt(ui), labels, False, None,
    ui.color, ui.icons, picker_colors(fzf_colors(ui)),
    popup=f"center,{width},{height}" if in_tmux else False,
    height=height, header=MENU_HEADER, info="inline-right",
)
category = rows[selected[0]][0]
```

`ui` and `in_tmux` represent caller-validated presentation/context; `coverage` contains counts across all modes of the filtered snapshot. Empty results bypass the selector. `menu_dimensions` excludes ANSI styles from visible width and can consume the verified client size; a different menu must account for its own header and exact client. The `category` filters the existing snapshot without recollecting providers or executing a binding. `browse` writes inert preview data once and renders aligned labels for each selected mode; numeric identities remain stable throughout navigation. Existing `--print`, `--json` and redirected output bypass selection. Actual tmux callers also retain their scoped `TmuxContext.selector_environment()` adapter.

This example deliberately imports key-specific helpers to explain the existing implementation. New menus should use the shared library above, leaving key-specific labels/providers in their current owner. Do not make unrelated menus depend on the key provider inventory or refactor the existing key browser merely to add a new menu.

## Terminal handoff and compatibility

The existing Prefix ? command runs in the background so FZF can own its popup. It maps only cancellation to success. Preserve its current pane-target and live-shell capture behavior rather than replacing it with an older shortened example.

The [tracked-config browser](../../../../lib/dots/files/browser.py) and [generated-theme inspector](../../../../lib/dots/themes/inspection.py) require terminal input/output; simply running them from `run-shell -b` is insufficient. `run_action` supplies a targeted terminal only after `choose` returns. A browser that already owns an FZF popup must not be put inside a second popup host. The output reader retains a scrollable result until dismissal, preserves its status and carries caller argv/environment through private, transient transport. Never print the request contents or expose them through menu JSON.

Native FZF previews currently require `--with-shell` support and an available native PowerShell. Inspect `rich_fzf_available` and the selected caller's fallback policy before changing that capability gate. Menu help/completion use metadata without starting selectors or extensions. Keep command data output and platform support claims governed by the [command guide](../../../../agents/guides/commands.md) and [PowerShell reference](../../../../docs/powershell.md).


## Row-specific actions and shared styling

`RichSelector.fzf(..., navigation=frame, navigation_keys={"alt-r": "rename"},
event_selection=True)` returns a `SelectionEvent` with `action`, a validated
numeric `index` (or `None` for an empty match set), and `query`. Use the index to
retrieve a controller-owned record; never execute the displayed label. Ordinary
navigation callers retain their existing contract without this option. Enter
still returns selected indices and Ctrl-C raises `SelectionEnded(130)`.
`focus_index` restores a row after an action; with a nonempty query the adapter
uses FZF's inert filter ordering before opening the UI. Do not assume the raw
inventory position equals the fuzzy match position.

For a compact bottom preview, opt into `preview_position="down"` and
`preview_lines=N`. Budget preview borders separately from the content dimensions
reported by `FZF_PREVIEW_LINES` and verify the installed FZF geometry. Session previews
use `preview_wrap=False` to keep each session on one row, clip overflow at the
right edge and size by logical line count; they normally use five rows and cap
at eight. Callers that need wrapping can use `preview_wrap=True`, budget content
width after borders/padding and count wrapped display cells after stripping
trusted ANSI. Keep a stable height for the view and cap it against the terminal.
Default percentage sizing and wrapping for other callers are unchanged. FZF's `~N` syntax fixes header lines; it does not
size a preview to its contents.

Trusted `bindings` are applied after built-in preview keys, allowing an explicit
caller override of Alt-P. Todo uses this for adaptive result/resize transforms
and visibility-preserving toggling through its read-only numeric sizing helper.
Keep query/goal text out of generated action syntax; unsupported capabilities
retain the compact layout and native toggle. Other callers keep their defaults.

The [session browser](../../../../lib/dots/menu_sessions.py) refreshes project
and session snapshots after actions, leaves query/focus in each navigation frame,
and opens name input or default-Cancel confirmation only after its chooser has
closed. Its single `Alt-H: keys` hint opens a separate read-only FZF reference
from the same control table that defines action events. Enter is ignored;
Escape/Alt-H returns, Ctrl-C cancels. Handle help before row selection so empty
matches work, and preserve pending project-submenu actions as well as query/focus.
Empty match sets still accept New/F1/Back. `choose(header=...)` allows an action-specific warning/control header; keep confirmation counts visible on narrow terminals. Create/rename/delete are
explicit terminal-session operations, outside managed-file transactions; deleting
the invoking session must close parent navigation. Its private
[Termux adapter](../../../../lib/dots/menu_session_host.py) uses shared platform
detection and a fixed attach helper, without running labels as shell text. Probe
`termux-am`, then the Termux-installed legacy `am`, only for New Termux and before
creating a session. Never retry a launch request after an error or timeout.
Automatically created sessions marked `@dots-termux-default=1` remain generic
regardless of their name or working directory.

Use [shared picker styles](../../../../lib/dots/picker_style.py) for palette-derived
`styles`, display-cell `fit` and `picker_colors` when following the key popup's
field styling. `named_styles(ui)` resolves muted/emphasis, true theme accent,
orange, green, `bright_green`, yellow, blue, red, `foreground` and `light_foreground` roles in one
palette read; `styles(ui)` retains its
original muted/emphasis/orange tuple. Keep role names explicit when painting
independent count fields. Session icons share the name span, so width budgeting
uses the plain icon text before adding ANSI. These helpers load no key providers. Keep domain-specific rows
and inert previews in their own controller, as demonstrated by
[session presentation](../../../../lib/dots/menu_session_ui.py).

The session controller accepts `create_session(server, None, directory, project, context)` for managed creation with an immutable ID and automatic project naming. Explicit names retain manual creation semantics. Popup New uses the managed form without a name prompt; all subsequent actions retain the returned native session ID. See `lib/dots/tmux_workspaces.py` and the workspace plan for lifecycle ownership.

Anodize Help pins text/horizontal (LOGO2 when wide, otherwise LOGO1); Preview and Extract pin text/base (LOGO1). Both read-only interactive results cooperate with `page_text(..., defer=True)` using the document action kind. Follow the [logo contract](../../../../docs/anodize.md#terminal-logo) and assert actual captured artwork; terminal/capture capabilities must not change the default mark. Logo gradients use published colors for Help and candidate colors for Preview/Extract, with independent hint/info/accent symbol/wordmark gradients and selected backgrounds covering logos, headers and details.

## Document action keys

`menu_pager.action_page(text, title=..., actions=..., frame=..., context=..., notice=...)` is an opt-in fitted FZF reader. Pass trusted key-to-(action ID, label) pairs; it returns an action ID, `actions` for Enter, or `back`. Query and focused line stay in the caller-owned frame across copying or reopening. Execute actions after the selector closes, and export the original complete text rather than selected/search-filtered lines. Ordinary `page_text` and less/FZF read-only readers keep their existing contracts. Todo demonstrates full-brief copy/print/launch actions and returns a typed handoff so its containing launcher exits on print or Codex launch.


### Shared text input and config review

`menu_input.prompt(initial, title, context=None, multiline=False, back=False)`
provides optional Gum input with a readline fallback and private exact-client
terminal handoff. `back=True` reports Escape as `SelectionEvent('back')`; Ctrl-C
remains `SelectionEnded(130)`. `todo_input` retains the original import entry point.
The config browser keeps its transaction plan across input and review, uses numeric
preview snapshots and default-Cancel Save, then applies the original guarded plan.
It never rebuilds a plan after approval or adds approval flags to file handoffs.
