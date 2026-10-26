# Wiki commands and maintenance

Dots keeps canonical documentation in its main repository and exports a navigable wiki to a separate Git checkout. The default path is `~/repos/dots.wiki`; `DOTS_WIKI_DIR` overrides it. The manifest declares pages, titles, sections, source mappings and repository URLs. Neither inspection nor shell startup downloads or updates the wiki.

## Reading and navigation

`dots wiki` shows grouped navigation, checkout/branch and freshness. `list --section NAME` filters pages. `show PAGE` reads a generated page; `show PAGE --source` reads its canonical source. Terminal text can use optional Bat highlighting; redirected text and `--raw` remain exact bytes. `search QUERY` performs literal, case-insensitive content search with page/line references; `--titles` restricts it to page titles. `browse` uses optional Gum or a numbered terminal picker, then opens the selected document in the shared scrollable reader: arrows/Page Up/Down or mouse, `/` to search and `q` to return. Without less it uses a read-only FZF line browser (Enter/Escape returns). When launched from `dots menu` in tmux, the document-selection host closes first, then a fitted reader opens on the same client. Short documents use compact popups; long pages reach the 90% height cap and remain scrollable. Direct `show`, `--raw` and redirected output are unchanged.

`open [PAGE]` opens the GitHub page (Home by default); `--print-url` prints its URL without opening anything. `path [PAGE]` prints the exact local checkout/page path; `--source` selects its canonical source. `edit PAGE` opens the source through VISUAL, EDITOR or an installed editor, without shell evaluation. The generated command reference has multiple metadata sources and cannot be edited as one document.

Overview, list, search, check, build and init support `--json`. No-match searches exit 1. Invalid or unavailable pages return a diagnostic; use `list` to discover exact, case-sensitive IDs. Help and completion read static metadata and page definitions without executing extensions.

## Updating the wiki

```sh
dots wiki edit Wiki
dots wiki build --dry-run
dots wiki build --yes
dots wiki check
dots git wiki status
```

Build is explicit and never stages or publishes changes. It regenerates pages and the sidebar together, records source/output hashes, and uses the shared transaction engine with retained backups. A second identical build changes nothing. Unknown files are preserved; edited generated pages must be reconciled into the canonical source before rebuilding. Obsolete unchanged generated pages are removed only through the same guarded transaction. The initial clean starter Home page is adopted with a backup. Transaction IDs can be inspected and undone through `dots files history` and `dots files undo ID`.

`check` verifies source mappings, internal links and anchors, navigation coverage, generated content and freshness. `check --source-only` validates generation without a wiki checkout and is suitable for CI. These checks establish consistency, not automatic proof that every prose statement is correct: maintainers must verify examples and claims against the implementation and its tests.

`init --dry-run` previews acquiring a missing wiki. `init --yes` clones only that repository into a staged directory, retains an acquisition journal and exposes the completed checkout without replacing an occupied destination. Existing checkout remotes and branches remain untouched.

## Git integration

Ordinary `dots git info|status|sync|publish` includes the associated wiki by default; `--no-wiki` excludes it. `dots git wiki` defaults to info, and `dots git wiki info|status|sync|publish` selects only the wiki. These commands share ordinary Git options and safety checks. Selecting an unrelated repository with `-C` does not attach the Dots wiki. Actual submodule routes still traverse only gitlinks; this association is not a submodule.

Sync updates the source tree/submodules first, then fast-forwards the wiki using its own upstream. Publish processes submodule dependencies, the source repository, then the wiki. A source failure blocks dependent wiki publication; already completed operations remain retained. Missing associated checkouts are visibly skipped during ordinary operations; explicit wiki actions require `init`. `sync --init` continues to mean submodule initialization only.

Direct CLI publication remains staged-only unless `--all` is explicit. The Git → Publish and Git → Wiki → Publish choices in `dots menu` supply `--all` and retain the existing review and confirmation. Wiki freshness is checked against the selected index/worktree content and the selected source publication. Wiki publication requires the manifest’s configured source branch, so feature-branch documentation cannot claim to describe the default branch. Wiki-only publishing checks the published source tracking tree, refreshing that evidence before a real push. A stale selected page or inventory blocks wiki publication with a build/staging hint. Nothing silently builds or stages documentation. Existing ownership rules, explicit refspecs, locks and fingerprint rechecks continue to apply.

## Contributor workflow

Use the `dots-documentation-maintenance` skill when behavior changes affect documentation and `dots-wiki-maintenance` for navigation, generation or wiki Git work. Update source docs in the same change as implementation, preserve proposed/native-evidence labels, and rebuild/check when the wiki checkout is available. If unavailable, run source-only checks and report wiki synchronization pending. Do not claim that an unpushed local export is live on GitHub.

The source checkout's [agent guide](../AGENTS.md), [documentation guide](../agents/guides/documentation.md) and [wiki guide](../agents/guides/wiki.md) define the workflow. Automatic commits, pushes and background synchronization are not installed. Native Windows PowerShell acceptance is separate from portable controller fixtures.
