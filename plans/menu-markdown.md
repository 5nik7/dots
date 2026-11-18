# Menu navigation and Markdown viewing

**Status: Implemented and verified on Termux.** Approved scope: cyclic menu navigation,
home-relative project labels, shared Wiki browsing with return-to-submenu, and a
shared CLI Markdown renderer. Owners: menu, Wiki, configuration and Todo maintenance.

- Enable shared FZF cycling by default; retain explicit FZF preference overrides.
- Shorten project home paths only in terminal displays; retain exact data and cwd.
- Move Wiki pages/sections/topics to shared selectors and exact-client popup
  ownership. Restore query/focus after reading; retain numbered fallback.
- Add `apps.cli.markdown_viewer`: auto, leaf, mdcat, glow, rich-cli, mdterm, bat,
  cat, builtin. Auto order is leaf > mdcat > glow > rich-cli > mdterm > bat >
  builtin. Explicit failure reports a notice and uses that order without retrying
  the failed renderer. Termux selects leaf; shared defaults select auto.
- Render Wiki show/browse and Todo document/brief displays inside existing Dots
  readers. Keep raw/export/copy/handoff bytes and native application previews.
- Retain Wiki reader plain override; auto delegates to the shared setting.

Configuration assessment: **add** shared renderer with finite choices, existing
profile inheritance, next-view activation, no publication/reload. Menu assessment:
**update** Wiki navigation and add direct Markdown viewer configuration editor.
Existing menu layout/color controls suffice; no additional presentation settings.
README: **no change**, because essential setup and first commands are unchanged.
Installer: **no change**, because renderers are optional PATH capabilities; no
new native Windows app destinations or package installation. Both Bash and native
PowerShell use shared controllers and completion; no new public route or option.

Acceptance: isolated selector/launcher/project/Wiki/pager/Todo/Config tests;
40/80/120-column private terminals, exact-client ownership, renderer priority and
failure cases, plain/color/control safety, inheritance/reset and exact data bytes.
Update canonical docs and generated Wiki, check links and diff whitespace. Native
Linux/WSL and Windows PowerShell 5.1/7 acceptance remains pending local availability.

Planning probes: installed Leaf, mdcat, Rich CLI and Bat rendered an owned stdin
document successfully with captured output. Implementation acceptance follows.


## Verification (2026-11-18)

- Shared Markdown suite: 9 tests passed, including all choices/order, explicit
  failure notices in popups, deadlines/output bounds, literal/control safety,
  inheritance/reset and next-invocation saves without theme publication. Installed
  Leaf, mdcat, Rich CLI, Bat and cat rendered owned samples at 40/80/120 columns.
- Shared menus (26), pager (15), projects (41), Wiki topics (7), Wiki presentation
  (7), and Todo menu (10) suites passed. Focused post-edit selector/project checks
  also passed. Private clients verified wrap directions, filtered/single matches,
  home-path display boundaries, Wiki topic/section return and query/focus, and
  the Markdown Config editor's literal handoff and cancellation.
- Launcher contract regressions and both Wiki reader variants passed (17 tests);
  four additional private Wiki/Config checks passed at 40/80/120 columns. Updated
  stale fixture expectations for the existing Projects entry and existing shared
  Config save destinations; no related production behavior was changed.
- Focused Config editor tests passed, including the native terminal exercise of
  both frontend adapters. The new viewer choice completed through actual Bash,
  Zsh and Fish Tab input. Other ordinary Config completion checks passed.
- The broader real Zsh/FZF-tab glyph-preview test remains failing in its final
  icon selection case. An isolated archive of unmodified HEAD also failed that
  glyph case (zero matches/timeout); this is outside the Markdown/menu change.
- Command metadata validated 292 external routes. Relative Markdown links (1481
  links in 177 files), whitespace and local Wiki freshness checks passed. Nine
  local Wiki files were rebuilt with retained transaction
  `271fade5be7847b184a9cb1fa04b8f36`; nothing was committed or published.

Native Linux/WSL and Windows PowerShell 5.1/7 remain pending. Glow and mdterm are
not installed here: their literal adapters/fallback behavior have fixture coverage,
not native rendering evidence. No Windows app destinations changed. No package
installation, theme publication or live shell/tmux reload was performed. Direct
dispatch and startup behavior are unchanged; renderer probes are limited to
explicit document views and Config details, with no new persistent cache.

## Reader Escape follow-up (2026-11-18)

**Implemented; verified on Termux.** Add single Escape dismissal alongside `q` to the shared less
reader. Preserve arrow/Page keys, mouse events, search, terminal size and cleanup,
captured command exit status and all existing secure-reader restrictions. POSIX
uses a temporary PTY to distinguish a lone Escape from a terminal key sequence;
native Windows uses an owned key source for its console input. Ordinary `less`
commands retain their existing native configuration.

Menu assessment: **update** shared output/Wiki reader controls and hint.
Configuration: **no configuration integration change needed**; this is a reader
navigation binding, with no additional appearance setting. Menu maintenance owns
the adapter. Bash and native PowerShell continue through the shared controller;
native Windows runtime acceptance remains pending. No new routes, flags,
completions, installer resources or Windows app destinations. README remains
unchanged because essential setup and first commands are unchanged. Verify both
exit keys and navigation in owned terminals, including 40/80/120-column popups,
then update canonical docs and rebuild/check the local Wiki.


Follow-up verification: 17 pager tests passed, including restored terminal modes
and main screen, preserved command status, separate Ctrl-C cancellation, private
Windows key-source cleanup, resize forwarding and complete/split key sequences.
Actual less light/dark terminals passed at 40/80/120 columns with Page/arrow/Home
and mouse navigation, search text and Escape dismissal during search. Two Wiki
popup checks passed at all three widths, preserving exact-client ownership,
submenu/query/focus after both q and Escape. Native Windows console behavior and
native Linux/WSL remain pending; Windows key-source fixtures are not native
runtime evidence. The ordinary less configuration and all shell startup paths
remain unchanged. Canonical docs and local Wiki were synchronized; no commit,
push, package installation or live shell/tmux reload was performed.
