# Wiki output and configuration

**Status: Implemented and locally verified.** Scope: every `dots wiki` route and its existing launcher, page, section and topic selectors. Owner: `dots-wiki-maintenance`, with configuration, presentation and menu maintenance.

## Decisions and route audit

| Surface | Finding and disposition |
| --- | --- |
| Overview, list | Existing shared details lack a concise collection count and page-specific styles. Update human reports; retain ordinary redirected layout. |
| Search, titles, topics | Preserve matching/ranking and data. Add styled page/section/snippet/URL spans and configurable human snippets/URLs. |
| Check, build, init | Use semantic status, meaningful empty results, shared filesystem resources and wrapped journal/transaction details. Preserve preflight, approval and recovery. |
| Show, browser reader | Share bounded rendering; configurable auto/plain reader. Raw/redirected document bytes remain exact. |
| Browse pages, sections, topics | Reuse shared menu rows, icons, spacing and popup styling; preserve numeric selection, optional Gum/FZF/plain fallbacks and deferred exact-client reader. |
| Launcher Wiki submenu | Update Wiki icon binding; reuse existing generic entry styles and action identities. |
| Path, open --print-url, completion, JSON | Intentional data interfaces; no decoration or display preference filtering. |
| Open, edit | Preserve external browser/editor output and invocation; style owned diagnostics only. |
| Help and usage | Shared metadata help already consumes global presentation settings. Keep metadata/completion and dependency-free basic help. |
| Git / Wiki submenu | Uses existing Git renderer and shared menu controls; no duplicated Wiki styles for Git operations. |

Configuration assessment: **add** `apps.wiki` controls for list detail (`summary|full`, summary), search snippets/URLs (true), menu descriptions (true), section breadcrumbs (true), and reader (`auto|plain`, auto). Add `formatting.apps.wiki.row_gap` (integer 0..4, 1); reuse CLI indent/tab/label width/gap/alignment and menu formatting/popup controls. Add nullable CLI `colors.wiki.{heading,label,page,section,snippet,url}` fg/bg/attributes, falling back to semantic roles; add `icons.menu.wiki` and its independently styled icon role. Preserve explicit false/empty icons and parent/profile inheritance. Typed saves and Wiki-specific color/icon saves apply on the next invocation or popup without theme publication.

Menu assessment: **update** existing Wiki views; retain actions, ordering, literal argv and native backend ownership. Add a Configuration entry that opens the existing guarded Config browser filtered to Wiki; no setting is saved just by opening it. Canonical configuration catalogs remain authoritative; this table records the audit and implementation decisions.

## Static audit evidence

The read-only configuration audit found eight Wiki candidates in the pre-edit source: `wiki.py:35` JSON indentation and `wiki.py:299` clone timeout are serialization/safety policy, not output preferences; `wiki.py:402` and `wiki_browser.py:22,73` are actual presentation paths now bound to shared styles/layout and the reader setting. `wiki_topics.py:11-13` are Markdown fence markers, not icons. Manual inspection also traced every route, selector, diagnostic, data mode and supported control above. Other scanner findings are outside this requested family; optional/nested repositories were not initialized. No extra goals were created or completed goals reopened.

## Verification evidence

The first focused run passed all seven new consumer tests, including saved settings, parent inheritance and reset, both completion frontends, all picker backends, plain reader literal/control safety and 27 owned terminal report captures at 40/80/120 columns. A separate comparison against the retained pre-task Wiki controller passed 37 exact stdout/stderr/exit-status comparisons, including forced-decoration data modes. All fourteen related suites passed. Four focused launcher checks passed, including actual Gum and FZF (Gum absent from the owned PATH) section-reader handoff on private clients at 40/80/120 columns. Four final config/style/selection checks and all fifteen pager tests also passed; native platforms remain unclaimed.

## Acceptance

- [x] All listed human surfaces honor global color/icons, NO_COLOR, shared layout, semantic status and resource styles; plain views retain meaning.
- [x] Each new setting is validated, discoverable in Config/completion/explain, reaches a real consumer, inherits/resets correctly and reports activation.
- [x] Exact JSON, raw, paths, URLs, completion and ordinary redirected reports are preserved under changed preferences and forced decoration where applicable.
- [x] Isolated populated/empty/error checks; owned 40/80/120-column terminals and private two-client popup/reader checks; cancellation and missing tools.
- [x] Focused Wiki/config/menu/style checks, both frontend paths, manual freshness, docs links, whitespace and local wiki preview/build/check.

Both Bash and native PowerShell dispatch share the Python controller. Native Windows PowerShell 5.1/7, Linux/WSL visual evidence and hosted GitHub rendering remain named pending checks when unavailable. No Windows app destinations change. Follow the [presentation acceptance gate](../docs/presentation.md#acceptance-gate). Do not change live preferences, install, publish, commit or reopen completed Todo goals.

## Completed checks

| Suite | Result |
| --- | --- |
| `test_wiki_presentation.py` | 7 tests successful |
| `test_wiki.py` | 18 tests successful |
| `test_wiki_topics.py` | 7 tests successful |
| `test_wiki_git.py` | 11 tests successful |
| `test_config_values.py` | 13 tests successful |
| `test_style_config.py` | 7 tests successful |
| `test_config_live.py` | 11 tests successful |
| `test_config_alignment.py` | 9 tests successful |
| `test_config_menu.py` | 20 tests successful |
| `test_menus.py` | 24 tests successful |
| `test_menu_popup_config.py` | 6 tests successful |
| `test_resources.py` | 17 tests successful |
| `test_bash_dots.py` | 28 tests successful |
| `test_native_cli.py` | 23 tests successful; 2 unavailable native PowerShell skips |

Metadata validation passed for 244 external commands; manual freshness, Markdown links and whitespace checks pass. The local wiki already matched the canonical sources at the final preview/build, so the retained build workflow reported unchanged; the full wiki check is healthy. No commit, push, live preference edit, activation or installation was performed. The full launcher suite was not rerun: its previously documented unrelated Files-menu expectations remain outside these focused Wiki checks. Native PowerShell 5.1/7 terminal interactions, Linux/WSL visual checks and hosted GitHub rendering remain pending.
