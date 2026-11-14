# Shell completion colors

**Status: Implemented; local acceptance verified.** Selected Todo goal: `17884af1fdce49cea103b7546b5d64f8`.

## Agreed behavior

Zsh/fzf-tab and native Zsh listings distinguish commands, options, values, Git
branches/tags/remotes, descriptions and headings. Unknown types stay neutral;
files retain LS_COLORS. Selected rows retain their semantic colors. Raw
completion records, literal insertion, sorting, group switching and previews
retain their contracts. A guarded Dots adapter leaves installed plugins intact
and falls back when their interface is incompatible.

`apps.completion.enabled` defaults true. The
`colors.apps.completion.{candidate,command,option,value,branch,tag,remote,description,heading,separator}`
roles expose foreground/background and supported attributes through existing
shared/profile preferences and Config. Literal settings and bounded input guards
refresh existing shells at the next prompt/Tab; no extra steady-state process,
per-candidate configuration read, theme publication or alternate preference store.

## Work packages and dependencies

1. `bfc4a098880e4fe8903095a81376b9a7`: preferences and next-prompt refresh;
   prove inheritance, consumer output, plain modes and last-good failure behavior.
2. `7eace0850d454a14bae5cacda8e5e0f3`: semantic rendering; depends on 1.
   Preserve insertion and interaction, adapter lifecycle and native fallback.
3. `cb80fdc47c2f4af78726636fc97e2762`: isolated rendering, compatibility and
   performance evidence; depends on 1 and 2.
4. `b9396276de8e4984a227068842d5368d`: docs, skills and delivery; depends on 1–3.

## Delivery assessments

- Owner: dots-shell-integration, supported by Config, command maintenance and
  presentation workflows. Configuration: add the consumer-backed controls above.
- Menu: update the existing Config browser through its shared catalog; no new
  launcher because Tab already owns selection. Retain existing previews/layout.
- Icons, spacing and placement: no new controls; this changes text styles only.
- Installer/bootstrap: existing shell and default-preference components deliver
  the changes; no dependency installation, plugin fork or new destination.
- Both frontends expose Config controls. Bash/Fish/Nushell/Xonsh/PowerShell
  completion records and aliases remain compatible; coloring is Zsh-specific.
  Native Windows has no new display consumer or application destination.
- Preserve pre-existing dirty work. No live reload, theme activation, commit or
  push. Update canonical docs/README/skills, then rebuild/check the local Wiki.

## Acceptance and evidence

Require owned Termux PTYs at 40/80/120 columns with Git/Dots/options/values/files,
Unicode, spaces, leading dashes, symlinks, long descriptions, mixed groups,
control-character display safety, selected colors and exact editor buffers.
Cover cancellation, multi-selection, group cycling, prefixes, previews, native
fallback, optional binary module, incompatible plugin interfaces and repeated
reload. Exercise shared/profile/reset preferences, no-color/forced modes,
missing/old snapshots and failed refresh. Measure startup and completion before
and after, and verify unchanged prompts invoke no extra process. Run affected
shell/config/completion suites, documentation links and diff checks.

Native desktop Linux/WSL rendering and Windows PowerShell 5.1/7 regression
acceptance remain named pending environments, separate from Termux evidence.
All Todo changes use the explicit project CLI scope; complete children before
the parent only after their criteria are verified.

## Implementation and local evidence

The implementation uses a private optional fourth completion field for Dots
candidate types and native Zsh completion tags for other providers. Git uses
`heads`/`local-heads` as well as branch tags. The guarded FZF-tab adapter preserves
its internal group markers and original captured word/arguments, with a separate
display span and inert lookup IDs for control-bearing labels. It overrides the
inherited `fg+:strip` behavior only for this completion view. Native Zsh keeps
LS_COLORS for files and group-aware semantic styles for other matches.

The preference reader shares Config's profile/default style resolution and
portable appearance import. Missing startup inputs use exact existence guards;
unchanged prompts and Tab calls use Zsh metadata builtins. Preference reads happen
only after a change, retain last-good values on failure, and retry after another
change. Literal hex rows handle control-bearing watch paths without evaluation.

Local environment: Termux aarch64, Zsh 5.9.2, FZF 0.75 (devel), tmux 3.8;
public FZF-tab `24105b15714bfec37989ed5c5b6e60f572253019`. The installed plugin remains
unmodified. The optional binary module is absent and retains a named pending
acceptance check. No native Windows or desktop Linux/WSL evidence is claimed.

### Verification results

- Fifteen focused completion cases pass, including 40/80/120-column PTYs,
  private tmux selected-row checks with inherited strip styling and light/dark
  colors, real Git references, previews, exact insertion, groups, native fallback,
  reload, plain modes, invalid preferences and literal watch paths. The final
  private-client case was rerun after synchronizing its test input cancellation.
- Twelve affected regression suites pass: profile config (10), preference files
  (8), style config (9), live Config (12), Config completion (5), Config values
  (18), shell environment (11), shell init (31), Bash dispatcher (32), backup shell
  completion (6), local completion (6), FZF configuration (2). These counts include
  four explicitly skipped PowerShell cases. Style-cache regressions were rerun
  successfully after narrowing missing-input guards.
- The broad Zsh suite passes 26/29. The same three failures reproduce in an owned
  HEAD archive: retired MSYS platform expectations, the minimal-tools startup
  assertion, and the old theme fixture missing `shells/zsh/fzf.zsh` and
  `default/file-colors.toml`. They are not introduced by this work.
- Existing Bash/Zsh/Fish/Nu/Xonsh provider records match the saved pre-change
  dispatcher byte-for-byte under identical owned metadata. The private typed
  projection strips back to the original three-field records.
- Changed Python and shell syntax, `git diff --check`, static command validation
  (291 external commands), and relative Markdown links (1,420) pass. Canonical
  documentation is rebuilt into the available Wiki and checked; no publication
  or live shell/theme activation is performed.

### Performance evidence

Matched owned full-startup fixtures included shared color/icon preferences and
public plugins. Runs were sequential; five warm samples followed each cold run.

| Measurement | Before | After |
| --- | ---: | ---: |
| Cold interactive startup | 11.159 s | 10.762 s |
| Warm interactive median | 4.178 s | 4.115 s |
| Noninteractive median, 15 interleaved samples | 0.426 s | 0.466 s |
| Warm `git <Tab>` menu median, 5 alternating samples | 1.154 s | 1.204 s |

Warm interactive startup shows no regression in this sample. The completion
projection adds about 50 ms (4.3%) to the measured Git menu. The noninteractive
reader also receives the additional literal preferences; its measured difference
is about 40 ms (9.3%), without another process. Initial one-order noninteractive
samples were 0.393/0.448 s, so the interleaved figures are retained above rather
than interpreting device/load variation as a speed improvement. Unchanged prompt
refresh and compiled warm preference loading pass an executable-counter check
with Python replaced by a failing sentinel. No per-candidate configuration query,
cache service or extra steady-state process was added.

The original pre-edit fixture, without the additional shared color/icon fixture
copy, measured 9.501 s cold, 3.065 s warm and 0.294 s noninteractive. It is retained
as context; the matched fixtures above are the comparison used for acceptance.

Local run logs: `/data/data/com.termux/files/usr/tmp/dots-completion-regressions-_wkuvfqy`.
Startup comparison fixtures: `dots-zsh-t3ex9d03` and `dots-zsh-2lfvnqg1` under the
Termux temporary directory. Logs/fixtures are disposable evidence, not repository
artifacts. Native desktop Linux/WSL, native PowerShell 5.1/7, and the optional
compiled FZF-tab module remain pending environment-specific acceptance.


## Delegated completion follow-up

The initial implementation left first-party delegated providers without the
private semantic field, so Todo/Fonts/Bak/Clipboard/Cleanup/pkgs/Blastoff and Git
submodule candidates rendered as neutral. Extend these trusted providers using
their existing parser context: command, option and value are explicit at emission.
Keep three-field output by default and native Python/PowerShell calls unchanged;
only the private Zsh request opts in. No third-party text heuristics, backend
execution, startup work or per-candidate process is needed.

Owner: command maintenance with shell integration. No configuration integration
change is needed because the existing completion roles cover these candidates.
No menu or installer change is needed: the existing Tab renderer and Config
browser consume the added metadata. Verify delegated root/nested commands,
options and values, standalone aliases, unchanged literal records and actual
Zsh/fzf-tab insertion, then synchronize documentation and the Wiki. Preserve
completed Todo statuses and append follow-up verification to the selected goal.

### Expanded project coverage and durable acceptance

The user expanded the follow-up to all Dots commands/subcommands, bundled plugin
names and associated projects in `~/repos`, explicitly including codex-termux.
The read-only inventory identifies ten CLI owners, twelve non-CLI projects and
two historical source copies. `~/repos/dots` resolves to this checkout; active
pkgs/Blastoff sources are the bundled plugins. Command inventories remain in
each owner's static metadata/parser, not in a second handwritten command list.

The FZF-tab adapter now retains group identity before the plugin hides labels.
Native Zsh `_arguments` choice tags use the value role. Standalone plugin
providers, codex-termux, git-it command positions and Paint token groups receive
explicit semantic types while preserving literal insertion. Core completion also
exposes registered descendants under intermediate namespaces without their own
executables; finite argument enums that repeat child names retain command type.

Acceptance adds catalog-derived checks for every Dots route, intermediate prefix
and static finite choice, a bounded project ownership/gap audit, owner grammar
tests and actual source-based menus for associated CLI projects. Missing future
owners or semantic tags must fail explicit audit checks. The new CI workflow
runs portable catalog/provider checks; installed freshness and actual menus are
separate checks. No repository scans or caches are added to shell startup.

Configuration integration: no new keys/store; command/option/value and existing
description/separator roles cover all added consumers, with real-menu checks for
custom colors and hidden headings. Menu integration: existing Tab menus are
updated; no extra launcher is needed. Installer/bootstrap: existing completion
delivery paths remain authoritative. Repository source edits do not install
copied external releases or reload live shells. Documentation and owner skills
record these requirements. Other shells retain literal records; no new native
Windows display consumer/destination is introduced. Native desktop/PowerShell
and optional binary FZF-tab acceptance remain pending as recorded above.

### Follow-up verification

- Catalog: 295 routes (291 external plus four builtins), 298 catalog prefixes
  and 1,028 contexts including explicit setup options. The full run exercised
  1,027 contexts; three init cases needed the grammar's `--setup` context added.
  All seven corrected init contexts and all 75 Files contexts then passed,
  including intermediate namespaces and child commands alongside finite values.
  Filtered runs are explicitly labeled; the default CI audit remains complete.
- Real FZF-tab menus: reported Dots/Todo/pkgs/Blastoff/Git/Debug contexts,
  eight standalone plugin contexts and fourteen associated-project contexts
  passed exact insertion and semantic-color checks. The project sources were
  battery, git-it, gitsub, leaf, Paint and codex-termux. Custom command colors,
  brief/hidden/full headings, native Zsh fallback, file/control handling, group
  selection and Git preview identity pass. Readiness markers cannot match
  terminal input echo; native output waits for actual rendering.
- Owner checks: 21 bundled-plugin completion tests, four git-it checks and three
  Paint checks pass. Paint's old dangling `_describe -V` exposed option-parser
  internals as candidates; the corrected flag placement has a regression.
  codex-termux's parser audit checks 37 command contexts and 150 queries against
  Bash's literal candidates. Its full offline verifier passes all 134 tests
  (runtime, wrapper, managed server, runit, presentation, package and release),
  generated freshness/checksums and 90 local documentation targets. `groff` is
  unavailable, so native manual rendering is the one named tool skip.
- Project inventory: seven fixture regressions pass; all 24 records reconcile
  with ten CLI owners, twelve non-CLI projects and two historical copies, with
  zero structural coverage issues. This is source coverage, not proof that
  installed copies are current. Shared rendering uses standard native argument
  tags; unknown custom tags remain reviewable instead of being guessed from text.
- The command/choice merge uses a per-query set of command names, avoiding a
  scan of previous candidates for each value. No startup scan, persistent cache,
  backend action or extra per-candidate process is introduced.
  Five interleaved, sequential 500-value emission samples measured medians of
  0.087 s before and 0.102 s after (15 ms). This is an emission microcheck,
  not a new whole-startup or whole-menu benchmark; the earlier measurements above
  remain their separately scoped evidence.
- Static command validation passes for 291 external commands; 1,425 relative
  Markdown links, six updated skill validators, YAML/syntax and whitespace checks
  pass. Wiki transaction `f720600a36734aefb7f94dd6f6821deb` updates the canonical
  projections; the following Wiki check reports healthy. CI is configured, not
  represented as a hosted run. Existing unrelated work and completed Todo states
  remain preserved; no live installation, reload, commit or push was performed.

## Normal startup and editor highlighting follow-up

The user reported plain text in both the menu and command line for
`dots git<Tab>`. Normal public startup reproduced a gap missed by direct-plugin
tests: Zinit creates defined FPATH-restoring shim functions, so `autoload +X`
leaves them intact and the adapter's interface checks decline installation.
The adapter now materializes only the recognized lazy form from FZF-tab's own
library without calling helpers. Unknown interfaces retain native behavior;
recognized wrappers are restored if compatibility checks fail.

FSH previously treated Dots route words as ordinary operands. A separate Dots
chroma callback recognizes literal executable routes using bounded path checks
and uses FSH's native `subcommand` theme style. It neither executes commands nor
changes BUFFER, and preserves user chroma callbacks, native quoting, operators
and operands. Intermediate route words receive the style when a later literal
word resolves the exact executable; unresolved prefixes keep native handling.
The explicit `files migrate-apps` dispatcher alias is covered. Registration
works with missing theme artifacts and disabled Dots
theme initialization. Exact-word Tab insertion, subsequent child menus and the
painted input ranges must pass through the actual public startup path.

Owner: shell integration. Configuration integration: no new controls or store;
the existing FSH `subcommand` role owns input and existing completion preferences
own menus. Menu integration: update existing Tab rendering only. Delivery uses
the existing linked shell/library sources; no installer change or live reload is
performed. Other shells and native Windows destinations remain unchanged; native
desktop rendering, PowerShell and optional FZF-tab binary acceptance retain the
limits above. Completed Todo goals remain complete, with appended evidence.

Durable acceptance adds the normal-startup/reload PTY case, a hermetic Zinit shim
test wired into completion CI, and `tools/test_fsh_dots.py` for input ranges,
overrides, aliases, theme-disabled startup, native fallback and literal Tab
insertion. CI uses the pinned public FSH source from the locally verified plugin
(`4672ad5dd9ad68a7effc1476d65afb7c584ce2b3`) for native editor regressions without
installing it. Review found and fixed preservation of FSH's case-statement bit;
native comparisons cover following case arms and control-flow syntax.
Documentation and the shell maintenance skill require testing plugin
load order as well as directly sourced adapters.

### Startup and input verification

- All 21 completion-color tests pass, including real public startup, exact
  `dots git<Tab>` insertion, native `git`/`status` input regions, colored child
  menus and reload into Debug completion. Existing 40/80/120-column selection,
  previews, plain modes, native fallback, preferences and literal records pass.
- All eight native FSH tests pass after preserving case-parser state, including
  nested substitutions, deferred namespaces, the migration alias and exact
  insertion. The PTY readiness marker differs from input echo so initialization
  must actually finish before typing begins.
- Six affected FSH theme cases pass: five in the initial run and the widget-load
  case on its isolated retry. The first attempt timed out after 40 seconds during
  fixture `theme set nord`, before plugin loading, and its still-finishing child
  raced temporary-directory cleanup. The unchanged case passed in 16.189 seconds
  on retry. Two suggestion-engine/plugin-reload regressions also pass.
- A matched public-startup comparison uses current owned fixtures with only the
  three affected adapters restored from the retained pre-fix snapshot for the
  baseline. Cold startup measured 14.046 s before and 11.389 s after. Three
  alternating warm samples measured medians of 4.534 s and 4.779 s (+245 ms,
  5.4%); the last pair was 4.534/4.569 s. This small device-local sample includes
  substantial variation and does not establish a speed improvement or isolate
  the adapter's cost. Fixtures: `dots-zsh-fr3rd9f6` and `dots-zsh-2cx5__d6` in the
  Termux temporary directory; results: `dots-startup-followup-benchmark.jsonl`.
- Three alternating 300-redraw samples for `dots blastoff theme list` measured
  median native FSH cost of 1.120 ms and callback cost of 1.668 ms (+0.548 ms).
  The callback uses native regions and exact path checks; it adds no processes,
  command execution, directory scans or persistent catalog cache.
- Relative Markdown links (1,425), shell/Python syntax, workflow YAML, the shell
  maintenance skill and whitespace checks pass. CI is configured with the
  locally tested FSH revision; no hosted run or new desktop/Windows evidence is
  claimed. The Wiki is regenerated and checked after canonical source updates.
