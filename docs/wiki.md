# Wiki commands and maintenance

Dots keeps canonical documentation in its main repository and exports a navigable wiki to a separate Git checkout. The default path is `~/repos/dots.wiki`; `DOTS_WIKI_DIR` overrides it. The manifest declares pages, titles, sections, source mappings and repository URLs. Neither inspection nor shell startup downloads or updates the wiki.

## Reading and navigation

`dots wiki` shows grouped navigation, checkout/branch and freshness. `list --section NAME` filters pages. `show PAGE` reads a generated page; `show PAGE --source` reads its canonical source. Terminal text can use optional Bat highlighting; redirected text and `--raw` remain exact bytes. `search QUERY` performs literal, case-insensitive content search with page/line references; `--titles` restricts it to page titles. `browse` reads current source guides offline and offers pages, their heading sections, and a Whole page choice. `browse --query QUERY` selects ranked source topics. It uses optional Gum/FZF or a numbered terminal picker, then opens the chosen content in the shared scrollable reader: arrows/Page Up/Down or mouse, `/` to search and `q` to return. Without less it uses a read-only FZF line browser (Enter/Escape returns). When launched from `dots menu` in tmux, the document-selection host closes first, then a fitted reader opens on the same client. Short documents use compact popups; long pages reach the 90% height cap and remain scrollable. Direct `show`, `--raw` and redirected output are unchanged.

`open [PAGE]` opens the GitHub page (Home by default); `--print-url` prints its URL without opening anything. `path [PAGE]` prints the exact local checkout/page path; `--source` selects its canonical source. `edit PAGE` opens the source through VISUAL, EDITOR or an installed editor, without shell evaluation. The generated command reference has multiple metadata sources and cannot be edited as one document.

Overview, list, search, check, build and init support `--json`. No-match searches exit 1. Invalid or unavailable pages return a diagnostic; use `list` to discover exact, case-sensitive IDs. Help and completion read static metadata and page definitions without executing extensions.

## Wiki search and topic browsing

```sh
dots wiki search 'config precedence' --topics
dots wiki search 'environment variables' --topics --json
dots wiki browse --query 'nvim themes'
dots wiki search 'DOTS_WIKI_DIR'
```

Topic mode searches current canonical source documents and the generated first-party command reference in memory. It works without the separate wiki checkout and ignores stale exported content; it does not clone, build, write an index, or access the network. Every whitespace-separated query term must match, case-insensitively, within the page title, heading ancestry or that section's own body. Title/heading phrase matches rank before title/heading term matches, then body matches; ties retain manifest/document order. Sections do not inherit their children's body matches.

Results show a page, heading context, snippet and GitHub heading URL. Those URLs identify the corresponding exported headings; unpublished source changes become available on GitHub only after explicit build and publication. The popup opens a focused section with its page context. Browse without a query to choose a whole page or an individual heading. Wiki → Search in `dots menu` prompts for the same topic query; the selector closes before its fitted reader opens on the originating client.

`search --topics --json` returns schema 1 with `mode: "topics"`, `query`, and `items` containing `page`, `title`, `section`, `heading`, `breadcrumb`, `anchor`, `line`, `url` and `text`. Line numbers refer to canonical Markdown or the in-memory command reference. No matches return status 1 and an empty list; empty topic queries are errors. `--titles` and `--topics` are mutually exclusive. Ordinary literal search keeps its existing schema-1 `page`/`line`/`text` results and exported-file line numbers. Raw/source reading, scalar paths and URL printing retain their contracts.

The Wiki family is owned by `dots-wiki-maintenance`. Menu assessment: **update** the existing Wiki launcher and source selectors, including Configuration. Configuration assessment: **add** the consumer-backed display controls below, while retaining shared layout and popup preferences. Bash and native PowerShell share topic behavior and static flag completion. Without optional selectors, numbered selection remains available; without less or FZF, the selected source text prints directly.

## Output preferences

Every Wiki report uses shared color/icon policy and CLI spacing, with semantic status text, page counts and explicit empty results. `show` and the browser share optional Bat highlighting. The Wiki submenu's **wiki configuration** entry opens the existing Config browser filtered to Wiki; `dots config browse --query wiki` does the same from either shell frontend.

| Key | Default | Human view |
| --- | --- | --- |
| `apps.wiki.list_details` | `summary` | `full` adds canonical source paths or generated-source explanations to page listings. |
| `apps.wiki.search_snippets` | `true` | Show matching text in literal/topic reports and topic picker descriptions. |
| `apps.wiki.search_urls` | `true` | Show GitHub heading URLs in topic reports. |
| `apps.wiki.menu_descriptions` | `true` | Show page categories and topic snippets in selectors. |
| `apps.wiki.section_breadcrumbs` | `true` | Show heading ancestry in section selectors; false shows the individual heading. |
| `apps.wiki.reader` | `auto` | `auto` tries Bat; `plain` displays sanitized Markdown without an external highlighter. |
| `formatting.apps.wiki.row_gap` | `1` | Integer `0..4` blank lines between report records. |

```sh
dots config set apps.wiki.list_details full
dots config set apps.wiki.search_urls false
dots config set apps.wiki.reader plain
dots config set formatting.apps.wiki.row_gap 0
dots config explain apps.wiki.reader
dots config unset apps.wiki.reader
```

These typed settings follow profile/parent/default inheritance, support null/unset reset, and apply on the next invocation or reopened popup without theme publication. Config exposes their types, finite choices and provenance. They affect human views only: JSON records, raw/redirected documents, scalar paths/URLs, completion and ordinary redirected reports retain their complete established output. Search matching and ordering do not depend on display preferences.

Wiki-specific color/icon changes also apply on the next invocation or popup without publishing a theme. CLI styles are `colors.wiki.heading`, `label`, `page`, `section`, `snippet` and `url`, each with `fg`, `bg`, `bold`, `dim`, `italic`, `underline`, `reverse` and `strikethrough` fields. Unset fields inherit their enclosing semantic role; `colors.apps.cli.wiki.*` provides the normal per-app override. Status colors retain shared success/warning/error meanings, and real paths use shared file-type styles. `icons.menu.wiki` sets the heading/page glyph; an empty string hides it. `colors.icons.menu.wiki.*` styles that icon independently. Disabled colors/icons and `NO_COLOR` retain readable plain output.

Reuse `formatting.apps.cli` for indentation, tab stops, label width/gap and alignment, and `formatting.apps.menu` for selector rows. FZF and the numbered fallback use shared `colors.menu.*` field styles; Gum retains its native widget colors and plain selection values. Stable per-entry overrides use keys such as `formatting.apps.menu.entries["wiki:pages:Core"].label.fg` and `formatting.apps.menu.entries["wiki:sections:Core:whole"].label.fg`. Shared `apps.menu.popup` owns popup placement, sizing, frame and colors; no live tmux reload is needed. External editor/browser output and Git/Wiki reports retain their own owners.

Build and clone progress uses the shared delayed progress policy after approval. JSON, dry runs and redirected execution do not animate; failure diagnostics remain on stderr and retained transaction/journal paths stay available.

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
