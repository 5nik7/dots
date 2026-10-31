# Documentation, topic discovery and manual

**Status: Implemented and locally verified.** Selected Todo goal: `7ddc1895c7ad48989b6591e9edd043fd` (`docs-update`).

## Agreed outcome

Keep a compact getting-started README with existing light/dark logo assets, safe POSIX/PowerShell setup examples and a prominent wiki link. Preserve unique README information in canonical guides. Add practical core, configuration and Neovim guides and improve Commands/Environment entry points; retain existing wiki IDs and linked headings.

Add offline `wiki search QUERY --topics` and `wiki browse --query QUERY` using current source documents and static command metadata in memory. Match every case-insensitive query term, rank title/heading matches before body matches, and break ties in manifest/document order. Display page/heading context, a snippet and a GitHub heading URL. Keep literal search, raw output and existing JSON contracts. Browse pages, focused sections and whole pages through the existing selector/reader, including plain fallbacks and exact-client handoff.

Generate `man/dots.1` from the same public first-party inventory as the wiki command reference, including global options, declared arguments/options and examples. Keep the generator deterministic, non-executing and checkable. Manage `dots:manual` as part of core: detected Termux prefix `share/man/man1`, Linux/WSL `~/.local/share/man/man1`; Windows uses the equivalent wiki reference. Retain installer preflight, receipts, rollback and drift-aware removal.

## Work and dependencies

| Work | Todo ID | Dependency |
| --- | --- | --- |
| README | `ea66808389ff4d5bbf391cd6433d3e14` | Guides |
| Human wiki | `b13637492e3e47ec89fb050c9961c071` | Guides and topic browser |
| Guides | `97e67751d209481abc187be513a215d8` | Current implementation and README inventory |
| Topic browser | `84569030b35940d6b81fea170d98964d` | Guide headings and shared command inventory |
| Manual | `b1e312730e5d4981b903a384ba6ee6d7` | Generation and managed installation |
| Manual generation | `2b9bca6b7d934a91aad73ea786644fc8` | Static metadata |
| Manual installation | `cb95a46c304945f5887de8bc064ed93f` | Generated manual |

## Integration decisions

Wiki ownership: `dots-wiki-maintenance`, with command maintenance, menu authoring and presentation. Menu assessment: **update** Browse and add Search inside the existing Wiki family. Configuration assessment: **no configuration integration change needed**; use existing semantic colors, CLI/menu row formatting and popup settings. Installation ownership: `dots-files-maintenance`. No additional menu/configuration integration is needed for the manual because existing core selection and review expose it. Both shell frontends share the Python controller and static completion metadata. No new command family is added.

Preserve unrelated working-tree changes and separate Neovim ownership. No live installation, activation, submodule initialization, commit, push or hosted publication is included. Follow the [presentation gate](../docs/presentation.md#acceptance-gate).

## Acceptance and verification

- [x] Compact README and verified canonical guides; each old README topic has a documented destination.
- [x] Top-three relevant results for `config precedence`, `environment variables`, `nvim themes`, `files rollback`, and `wiki search`.
- [x] Offline source search, duplicate headings, Unicode, empty/no-match behavior, and exact legacy literal/raw/JSON contracts.
- [x] CLI and private popup views at 40/80/120 columns; cancellation, fallback and exact-client handoff.
- [x] Complete deterministic manual, safe roff escaping, lint/rendering, and CI freshness check.
- [x] Isolated platform destinations, core selection, collisions, rollback, idempotence, uninstall and drift refusal.
- [x] Affected wiki/Git, metadata/completion, native controller, menus/pager and installation suites, documentation links and whitespace.
- [x] Inspect both Git states, preview/build the local wiki through its transaction workflow and verify freshness.

Native Linux/WSL manual discovery, native Windows PowerShell 5.1/7 interactions and hosted GitHub light/dark rendering require separate evidence; record unavailable checks as pending, not as fixture-proven acceptance.

## README information destinations

The pre-edit README was retained outside the repository for comparison. Unique details move to their topic owners; existing authoritative coverage is linked instead of duplicated. Older README claims about unsupported Windows package operations, fixed palette counts and the old Anodize manual path are superseded by their current owner docs.

| Previous README material | Canonical destination |
| --- | --- |
| Overview, directory ownership, principles and contributor/worktree entry points | [Core](../docs/core.md), [architecture](../docs/architecture.md), [principles](../docs/principles.md), [worktrees](../agents/guides/worktrees.md) |
| Blastoff/pkgs, shortcuts, Go/npm/pip progress and application migration | [Packages](../docs/packages.md), [bundled applications](../docs/bundled-applications.md), [plugins](../docs/plugins.md) |
| Command framework, help, completion, logo preference and workflow menu | [Commands](../docs/commands.md), [presentation](../docs/presentation.md), [shell startup](../docs/shell-init.md) |
| Install/update/uninstall, component wizard, source and recovery behavior | [Installation](../docs/installation.md), [safety](../docs/safety.md) |
| Fonts, defaults and directory retention | [Fonts](../docs/fonts.md) |
| Keybindings, tmux keys/status/sessions and attention | [Keys](../docs/keys.md), [tmux](../docs/tmux.md), [theme attention](../docs/themes.md#codex-attention-notifications) |
| Shell initialization, utility commands, Zsh/mkcd and local completions | [Shell startup](../docs/shell-init.md), [shared shells](../docs/shared-shells.md), [utilities](../docs/shell-utils.md) |
| Shared themes, Yazi previews, mdcat, FSH/Vivid, app connectors and wallpapers | [Themes](../docs/themes.md), [Yazi configuration](../config/yazi/README.md), [file colors](../docs/file-colors.md) |
| Anodize authoring, previews, engine and logo behavior | [Anodize](../docs/anodize.md) |
| Files layout, registration, pickers, repair, stash and retained backups | [Managed files](../docs/files.md) |
| Git, submodules, publication, discovery and verbose operations | [Git](../docs/git.md), [files](../docs/files.md), [presentation](../docs/presentation.md) |
| Optional Neovim and local Anodize plugin ownership | [Neovim](../docs/neovim.md) |
| Local theme plugins, Starship/Blastoff and Git/Delta integration | [Theme plugins](../docs/theme-plugins.md), [file colors](../docs/file-colors.md), [environment](../docs/shell-environment.md) |
| Weather, clock and Termux location lookup | [Weather](../docs/wttr.md) |
| Profiles, generated namespaces, configuration/formatting and environment | [Configuration](../docs/configuration.md), [profiles](../docs/profiles.md), [environment](../docs/shell-environment.md) |
| Wiki, Todo, planning and goal lifecycle | [Wiki](../docs/wiki.md), [Todo](../docs/todo.md) |

## Verification results

Termux local verification completed with isolated roots and private tmux clients:

| Check | Result |
| --- | --- |
| Manual generation, lint/rendering, owned-path man discovery and lifecycle | 9 passed |
| Source topics, ranking, data contracts, both completion paths and 40/80/120-column CLI views | 7 passed |
| Wiki generation/read interfaces | 18 passed |
| Wiki Git publication safeguards | 11 passed |
| Bash dispatch and metadata | 28 passed |
| Native shared controller | 23 tests successful, including 2 unavailable-PowerShell skips |
| Shared menus / pager | 24 / 15 passed |
| New Wiki query handoff and private two-client reader at 40/80/120 columns | 2 passed |
| File platform safety / checkout installation / selective components | 5 / 28 / 5 passed |
| Installation adapters | 10 tests successful, including 5 native-platform skips |
| Markdown checker regressions | 4 passed |
| Metadata validation / manual freshness / Markdown links / whitespace | Passed |
| Local generated wiki | Healthy; retained build transaction `1beec98e0d93428184b60c9ef8cf3a81` |

The full launcher suite ran 23 tests with two pre-existing failures: `test_action_map_uses_existing_safe_routes` and `test_navigation_preserves_queries_context_help_and_workflow_return` still expect the old Files menu without Install/Uninstall. Both failures reproduce using the saved pre-task `menu_cli.py`; the existing installer/package edits are preserved. The new Wiki tests pass, including leading-dash literal queries and source-reader CRLF normalization.

The manual test discovers the installed artifact through an explicit test-owned MANPATH; it does not install a live manual or establish default viewer discovery on native Linux/WSL. Native PowerShell 5.1/7 interaction, native Linux/WSL manual discovery and hosted GitHub light/dark rendering remain named pending checks. No commits, pushes, live installation or activation occurred. All eight scoped Todo records are completed after verification; existing identities, aliases, titles, priorities, tags and relationships are retained.
