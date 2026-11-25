# Shell startup and Config views

**Implemented and verified on Termux.** The Dots Todo parents are `0f3fffa3266f423e9ab74844c53d85db` (startup) and `0a5f0e26ecb94d1ca50f5e15e7509838` (Config and previews). The pre-change performance baseline is commit `df9ac576`.

- Measure application-cache cold and warm input-ready prompts and first interaction in isolated native shells. Termux Zsh must improve repeatedly. Preserve the configured prompt, first command, first Tab, keys and directory hooks. Report unsupported native checks separately.
- Install independent rc entries and retain journaled backups. All six shells acquire a missing checkout only on interactive startup. A relocated checkout, missing Git, an occupied path, interruption, and concurrent first starts need isolated checks. The backend owns shared environment and tool setup. Native syntax and personal preferences remain in shared or profile shell directories.
- The Config family owns the existing browser, discovery and both CLI entry points. Add both app-first and type-first views over current stores. Keep structural files, environment exports and native preferences under their established owners.
- The FZF integration adds ordered preview preferences consumed on demand by native shell pickers and fzf-tab. Keep typed completion previews, stable insertion identity, local FZF settings and protected action previews.
- Shell integration and file maintenance own init and installer delivery. Update static bootstrap choices for all six shells. Setup is already in the installation menu. Ordinary init remains a code generator. Config controls belong in its existing browser. Document first-run setup in the installation guide and linked Wiki. The root README already links there.

## Delivery and compatibility decisions

| Surface | Implementation and acceptance |
|---|---|
| Interactive rc and checkout setup | The Files component copies the rc and cold helper in its existing transaction. Installed entries and stdout-only snippets select all six native adapters. Public local Git fixtures cover no-Git, first clone, interruption, simultaneous shells, Unicode paths, an occupied target and relocation. Recovery records keep the existing version-1 JSON journal fields. |
| Login and noninteractive startup | Bash forwards login to its interactive rc and loads an existing user profile. Standalone `.profile` still exposes shared helpers to independent callers. Zsh still needs `.zshenv` for noninteractive environment setup. |
| Backend and profiles | Shared tool path policy and startup preparation live in `lib/dots`. Shell configuration is layered through `$PROFILE/shells/init.<ext>` and `local.<ext>`. Bash/Zsh sourceable compatibility paths continue to work. Fish, Nushell and Xonsh offer newly supported generators through a profile-local list and retain their existing prompts and directory jump commands. |
| Config and previews | Config’s existing browser offers both app and type navigation. Existing keys, native and Dots field owners, inheritance, env redaction and file mappings continue to apply. Preview settings update the next preview. Typed action previews, editor insertion and local widget configuration retain their contracts. |
| Menus, completion and docs | Update the Config browser and its existing shell completions. The existing Files installer menu previews RC changes. Ordinary stdout-only init needs no new menu entry. Both init dispatchers expose the six bootstrap targets through metadata. The root README already links to installation and the Wiki. |
| Native acceptance | Termux provides Bash, Zsh, Fish, Nu and Xonsh. Native Windows PowerShell 5.1/7 acquisition, startup, file destinations, graphics and keyboard interactions, plus desktop Linux/WSL timing, require those platforms. The Windows suite includes process-tree timeout, UTF-8 output, ACLs and concurrent acquisition. |

## Verification

The PTY benchmark starts a real shell in a temporary home and waits for its first command to print the resolved Dots bin directory. It then presses Tab on a partial directory name, executes `cd`, and checks the resulting path. Bash and Zsh also complete and execute `uv --version` when uv is installed. The first startup uses empty application caches. Warm values are medians of five alternating pairs against the pre-change checkout. These measurements include the editor, prompt and command execution.

The Config browser, CLI, profile storage and lifecycle fixtures exercise the same value through both alias directions, including field-level resets, conflicting owners, inherited values, literal map keys, file identities and redacted environment values. The completion catalog covered 1,158 contexts across the main run and focused reruns. FZF tests exercise inherited option strings and files, explicitly empty previews, theme refresh, and literal selections in real fzf-tab sessions at 40, 80 and 120 columns.

The fresh Termux installation passed install, unchanged repeat, and uninstall with complete restoration of the checkout and original files. The synthetic WSL lifecycle and durable Fish directory migration passed. Combined Termux Files and Blastoff setup records their shared Starship link under `dots:dots-toml`. Separate regression cases cover an existing saved theme, a conflicting mapping and restoration of the previous file. All four profile manifests validated. The manual and generated Wiki were checked.

## Termux startup measurements

Milliseconds before → after. Each cold value is a single observation. The first-Tab columns measure the additional time after the preceding interaction.

### With FZF, direnv, Starship and zoxide installed

| Shell | Cold first input | Warm first input | First Tab and cd, cold | First Tab and cd, warm | First uv Tab, cold | First uv Tab, warm |
|---|---:|---:|---:|---:|---:|---:|
| Bash | 3,671 → 2,300 | 2,482 → 1,002 | 598 → 286 | 483 → 314 | 309 → 570 | 260 → 349 |
| Zsh | 5,074 → 2,808 | 1,874 → 529 | 469 → 311 | 313 → 308 | 223 → 474 | 150 → 257 |
| Fish | 1,052 → 795 | 225 → 200 | 99 → 36 | 32 → 33 | — | — |
| Nushell | 713 → 546 | 721 → 582 | 120 → 120 | 117 → 118 | — | — |
| Xonsh | 1,460 → 1,263 | 1,467 → 1,237 | 28 → 77 | 32 → 32 | — | — |

All five warm Zsh runs with these tools finished between 523 and 599 ms. The five baseline runs ranged from 1,703 to 1,929 ms. The minimal fixture below also has disjoint Zsh ranges of 252–270 ms after the change and 1,549–2,030 ms before it.

### Minimal tool fixture

| Shell | Cold first input | Warm first input | First Tab and cd, cold | First Tab and cd, warm | First uv Tab, cold | First uv Tab, warm |
|---|---:|---:|---:|---:|---:|---:|
| Bash | 2,387 → 2,483 | 1,484 → 356 | 120 → 23 | 48 → 26 | 58 → 441 | 73 → 233 |
| Zsh | 4,663 → 2,941 | 1,633 → 262 | 26 → 26 | 35 → 29 | 48 → 344 | 47 → 134 |
| Fish | 880 → 901 | 206 → 183 | 24 → 178 | 33 → 33 | — | — |
| Nushell | 686 → 561 | 704 → 517 | 120 → 119 | 118 → 118 | — | — |
| Xonsh | 1,733 → 1,167 | 1,547 → 1,264 | 19 → 24 | 36 → 27 | — | — |

### Cost of enabling all available native hooks

The representative fixture includes Starship, zoxide, direnv and FZF. Enabling all optional native integrations in the early profile runs the selected prompt and directory hooks from the first input. The resulting warm first-input and first Tab-plus-cd medians were 420 and 209 ms in Fish, 841 and 236 ms in Nushell, and 1,915 and 465 ms in Xonsh. The Fish opt-in sample preceded its final settings and platform-probe optimization. The default measurements above use the previous profile behavior in both checkouts.

Bash and Zsh defer the native uv completion generator. In the tool-present fixture, the first uv Tab added 89 ms in Bash and 107 ms in Zsh compared with the old checkout. Even including both first interactions, the median component times total about 1.66 s in Bash and 1.09 s in Zsh, down from 3.23 s and 2.34 s. In the minimal fixture, the single cold Bash launch was 96 ms slower, and the single cold Fish directory completion was 154 ms slower. Median warm first-input time improved for every shell in both fixtures.

## Audit follow-up and starting measurements

Todo goal `61b26c0888e546959e504467ae108ebe` addresses Config, profile and Zsh defects found after the measurements above. The new baseline captures the working checkout on top of `df9ac57`, before the follow-up edits. The input manifest has SHA-256 `153f1952be13455c009d908f606685e622bfc93fdd30bfa724b0ede5c4416b95`.

Each of the five available native shells ran in both a linked and a standalone installation in disposable Termux homes. Each shell/layout/tool combination used three fresh application caches and seven warm launches. The table reports standalone medians in milliseconds. First input ends at a marker emitted by an executed command. The directory measurement then requires a real Tab insertion and a successful `cd`. The tools fixture exposes FZF, direnv, Starship and zoxide to shells that select them. Public Zinit plugins have a separate fixture.

| Shell | Minimal warm first input | Tools cold first input | Tools warm first input | Tools warm first Tab and cd |
|---|---:|---:|---:|---:|
| Bash | 278 | 1,612 | 759 | 216 |
| Zsh | 204 | 2,645 | 364 | 222 |
| Fish | 126 | 840 | 128 | 21 |
| Nushell | 445 | 898 | 489 | 112 |
| Xonsh | 963 | 3,055 | 1,087 | 32 |

The Config baseline records effective values for all four base profiles through the owning resolvers. Each profile contributes 283 layered control records, 4,367 style fields and 17 declared environment values. The active Termux fixture adds 578 Weather, pkgs and Codex native records. The mapping comparison uses qualified IDs and checks 71 Termux, 59 Linux, 59 WSL and 51 Windows entries.

The Config and Files families own the corrected options, grouping and inspection behavior. Their existing menus and the six-shell completion adapters use the same sources. The shell integration owns native startup and the installer continues to own rc placement. The root README already links the relevant guides. Native desktop Linux, WSL and Windows PowerShell 5.1/7 have separate acceptance checks.

The first follow-up milestone fixed the clipboard default, dynamic map types and empty-map queries, redundant shipped styles, WSL mapping inheritance, Termux file grouping and the reported source of `CLICOLOR`. The ordered file arrays matched after the four deliberate Termux label changes. All 59 WSL rows kept their values and positions, and the 57 inherited rows now report Linux as their declaring layer. Config discovery and clipboard suites passed 49 tests with two native PowerShell skips. Another 18 checks exercised Config aliases through the native CLI controller. File, profile, browser and environment regressions passed 41 isolated tests.

Fresh and migrated Termux and WSL Zsh profiles now select the profile defaults before the FZF and final widget setup. Existing home links run once and an independent personal hook retains its override point. The Zsh tests covered failed-provider retries, shared history, caller option scope, repeated initialization and a PTY with seven real public plugins. The full Zsh suite passed 34 of 36 cases. Both failures also reproduced on the pre-edit source. The final startup milestone updated the obsolete `msys` platform expectation and restored the historical `shells/zsh/fzf.zsh` relative source link. Both regression cases then passed.

## Optional Zsh plugins on first use

The shared Zsh plugin list and the selected Termux profile's vi-mode and clipboard declarations remain authoritative. The existing `DOTS_ZSH_SUGGESTIONS` selector chooses Deja, autosuggestions or native editing. Installed plugins retain their order, user completion paths, and Tab, history, clipboard and vi bindings. A missing completion or history plugin gets its first acquisition request from the corresponding key. The first accepted command can request the remaining configured editor plugins. The initial prompt and noninteractive sessions do no acquisition. Bash, Fish, Nushell, Xonsh and native PowerShell keep their native integrations.

The user can run `dots-zsh-plugins setup` or `dots-zsh-plugins retry` in the personal Zsh shell. Zsh completes both actions. The shell-local function has no independent launcher entry or additional Config controls. It shares the plugin declarations, selection and activation state of the current editor session. Checkout bootstrap and package installation retain their own lifecycles. The [Zsh guide](../shells/zsh/README.md#startup-order) documents timing, receipts, retries and platform-specific Deja handling.

The [isolated regression suite](../tools/test_zsh_plugins.py) exercises first Tab and history keys, native fallback, newly registered providers, preserved widgets, safe-prompt activation, repeat/reload, concurrent requests, interrupted receipts, transport deadlines, explicit retry, occupied destinations and the Linux/WSL release boundary. The [Zsh configuration suite](../tools/test_zsh.py) also checks real cached Zinit and Deja staging compatibility, engine choice and offline startup. Provider fixtures use temporary homes and local fake transports. Native WSL/Linux keyboards and real release downloads are outside this Termux acceptance.

## Unified preferences and lookup verification

The checkout now ships three preference files in place of fifteen. Shared defaults live in `default/config.json`; Linux and Termux keep only their overrides. The four structural manifests still own identity, inheritance, environment and file mappings. The configuration browser and the CLI retain edit provenance across mixed schema-1 and schema-2 installations. A user with split files can preview `dots config migrate --layout unified`, apply it in one reviewed transaction, and restore the original bytes with Files undo.

The frozen post-audit values and schema-2 readback matched byte for byte. A second check compared all 23,541 audited spellings across their visible profiles. The 82,746 spelling/profile combinations produced zero owner differences. The audit also covers quoted keys and extensible maps. Scalar reads now skip unrelated native stores and full discovery. Composite views retain their participating owners.

Eight FZF renderer cases passed on Termux. One case requires native Windows cmd.exe. Native FZF and fzf-tab PTYs verified literal selection and completion at 40, 80 and 120 columns. An unavailable Markdown provider yielded to the configured next renderer. Explicit plain and empty preview policies retained their meanings.

Current-format Bash and Zsh bundles retain the current and previous publications. The open-reader test paused the shell inside a bundle, published two replacements, then resumed the original body. A simulated interruption left the previous pointer usable and a retry completed publication. Old-format candidates are shown with sizes in Cleanup. The private fixture covered drift, a held build lock, a protected previous generation and an unrecognized file in a generation directory.

## Final audit dispositions

Four follow-up Todo milestones cover audit repairs, unified Config storage, startup and cache changes, and verification. The configuration migration and the fresh-install tests used temporary homes. The local Wiki was rebuilt and checked against its canonical sources.

| Finding | Delivered behavior |
|---|---|
| Clipboard default and native map types | Clipboard recording defaults to off. Empty maps return objects. Glyphs and binding actions preserve their string types, including keys containing punctuation. |
| Duplicate preferences and mappings | The style catalog owns the app list for the reader and publisher. Unbound menu defaults, the shadowed Codex glyph and duplicate CLI and WSL styles were removed. WSL inherits 57 unchanged mappings from Linux and retains its two explicit disables. Four ambiguous Termux mappings now identify their applications. |
| Startup variables and PATH | One backend owns profile path generation and tool path policy. Bash and Zsh skip redundant PATH work. Config environment inspection reports the actual source of `CLICOLOR`. The plural `PROFILECONFIGS` and platform aliases remain public compatibility names generated from the same path. BAT's config directory and file remain independently configurable. |
| Zsh history, completion and hooks | Shared history uses a valid option, helper-local option changes stay scoped, the profile default runs once, and home overrides keep their position. Repeated startup reuses successful plugin registration, checks the completion directory before creating it and avoids a duplicate completion path or dump read. Interactive aliases remain available to their users. |
| Startup files and installed state | Four Fish forwarding files and three empty Zsh platform files were removed. One relative link preserves the old FZF source path. Bash's login entry, POSIX `.profile` and Zsh's `.zshenv` each have independent callers. The structural profile manifests continue to describe paths, file ownership and inheritance. |
| Storage | Shipped preference inputs fell from 15 files (21,461 bytes) to 3 (26,737 bytes). Nested JSON accounts for the larger byte count. Bash and Zsh now keep two current-format generations. Historical bundles remain available for reviewed removal through Cleanup. |
| Unexpected project file | The earliest checkout status in this session already listed an untracked file named `1`. Its creator is unknown. A regression test launches Zsh in an empty project, uses Tab, changes directory and reloads the profile, then checks both directories for unexpected files. |

Termux tests exercised fresh and repeat installation, uninstall, old Fish directory-link migration and restoration, checkout relocation, independent personal links, offline and concurrent bootstrap, a read-only cache, profile changes, first-use completion, editor keys, FZF and published theme reload. A WSL fixture exercised install and uninstall. Native desktop Linux, WSL, and Windows PowerShell 5.1 and 7 still require their own startup, keyboard and installation runs. The Windows-specific tests cover the PowerShell entry, ACLs, acquisition and timeouts. Image protocols depend on the terminal. The local renderer tests cover command choice and literal selection.

## Final paired measurements

All times are Termux medians in milliseconds. Each row compares the frozen pre-audit source with the follow-up checkout in disposable homes using the same installed entry and native executable. Cold columns use three independent application caches. Warm rechecks use seven alternating pairs per shell. The command column times a second accepted command. Tab and cd waits for the directory change. The uv column waits for the completed command to print its version. Samples overlapped other local tests, and some initial trials overlapped compilation. Compare the two sides of each row within its own run.

### With FZF, direnv, Starship and zoxide available

| Shell | Cold first input | Warm first input | Next command | First Tab and cd | First uv Tab |
|---|---:|---:|---:|---:|---:|
| Bash | 2,963 → 2,276 | 3,709 → 3,256 | 553 → 415 | 1,197 → 1,009 | 1,332 → 1,131 |
| Zsh | 4,622 → 4,431 | 753 → 706 | 163 → 139 | 382 → 417 | 399 → 316 |
| Fish | 915 → 1,059 | 640 → 649 | 59 → 49 | 75 → 139 | — |
| Nushell | 731 → 677 | 4,219 → 4,107 | 96 → 98 | 334 → 337 | — |
| Xonsh | 1,543 → 1,593 | 6,687 → 7,712 | 17 → 48 | 146 → 169 | — |

### Minimal tool set

| Shell | Cold first input | Warm first input | Next command | First Tab and cd | First uv Tab |
|---|---:|---:|---:|---:|---:|
| Bash | 5,725 → 5,316 | 358 → 343 | 1 → 1 | 25 → 25 | 236 → 220 |
| Zsh | 9,603 → 8,747 | 618 → 599 | 8 → 13 | 76 → 72 | 287 → 389 |
| Fish | 3,609 → 2,634 | 267 → 225 | 22 → 31 | 43 → 42 | — |
| Nushell | 2,692 → 3,518 | 751 → 644 | 16 → 20 | 119 → 119 | — |
| Xonsh | 9,011 → 8,103 | 1,497 → 1,377 | 8 → 7 | 31 → 35 | — |

### Public Zsh plugins and early environment

| Public-plugin login measurement | Before → after (ms) |
|---|---:|
| Cold first input | 37,944 → 30,426 |
| Warm first input, first run | 7,106 → 4,821 |
| Warm first input, repeat | 4,674 → 2,063 |
| Next command | 223 → 264 |
| First Tab and cd | 444 → 477 |
| First uv Tab | 402 → 433 |
| Backspace and accept | 354 → 208 |
| Reload | 896 → 669 |

The warm plugin-login improvement repeated in two sets of seven pairs. The repeated Tab and first uv completion took slightly longer, while backspace and reload improved. The fixture activated seven real, already-installed public plugins using an offline transport. Published Zsh source maps shrank from 354,857 bytes and 1,582 records to 22,925 bytes and 24 contiguous mappings. Trace records retain the original paths and line numbers.

An independent Zsh script benchmark measured warm noninteractive startup at 2,063 → 238 ms and warm noninteractive login at 2,256 → 231 ms. The first noninteractive script with an empty cache took 2,330 → 2,772 ms across five pairs. It pays for validating and durably publishing the early environment. Subsequent scripts use native validation.

### Variability and first-use costs

With tools present, two seven-pair Xonsh checks measured 6,687 → 7,712 ms and 1,534 → 1,401 ms. Instrumenting four native Xonsh sessions found zero rc subprocesses. The warm preference reader opened one file, down from three. The profiler measured this read at 354 → 98 ms.

Fish’s first tool-present trial was 189 → 233 ms at first input. Its repeat was 640 → 649 ms, while directory completion was 75 → 139 ms. Minimal Nushell’s first warm comparison was 2,110 → 2,839 ms and its repeat was 751 → 644 ms. Minimal Zsh first uv completion was slower in both sets (406 → 636 ms and 287 → 389 ms). Warm startup and the first deferred action are reported separately.

The final offline acquisition check also repeated seven warm pairs after the queue began checking its transport prerequisites. With minimal tools, Zsh first input was 345 → 278 ms and first uv completion was 162 → 148 ms. With optional tools and no vendor plugin checkouts, Zsh first input was 612 → 711 ms. Fish first input in the same batch was 170 → 182 ms and its first directory completion was 29 → 34 ms. The no-Git/no-timeout PTY confirmed zero Python launches or acquisition receipts on the first accepted command.

### Config lookup and browser

Each route used seven alternating fresh processes with isolated HOME and XDG paths. The Bash rows invoke the public executable. The other rows measure the shared frontend/controller or the Python provider that supplies the completion and browser. The browser probe builds the inventory and looks up an FZF field.

| Entry and request | Median before → after (ms) |
|---|---:|
| Bash CLI · Scalar color field | 5,880 → 3,128 |
| Bash CLI · FZF color group | 4,405 → 2,085 |
| Shared · Scalar color field | 1,673 → 783 |
| Shared · FZF color group | 2,411 → 1,143 |
| Shared · Complete `fzf.colors.` | 2,066 → 739 |
| Shared · Browser inventory and find | 7,338 → 2,108 |

A native Config browser fixture with 4,645 rows also exposed a 4,635,645-byte preview request beyond the 4 MiB transport limit. Limiting each field to its actual preview data and encoding the JSON once reduced the request to 2,608,954 bytes. Six native Config interaction tests passed, including editing, cancellation and previews at 40, 80 and 120 columns.

The final Config completion suite passed all 10 tests. It exercised real Bash, Zsh and Fish editing, 12 real fzf-tab picker cases, and the data records consumed by Nushell, Xonsh and PowerShell. The manual matched its sources, 1,540 relative links passed, and the generated local Wiki reported zero differences.
