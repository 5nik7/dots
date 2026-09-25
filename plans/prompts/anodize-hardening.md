# Next-agent prompt: finish the Anodize foundation

Copy the prompt below into an agent working in `~/repos/dots`.

---

Implement the bounded foundation-hardening task in `plans/anodize-next.md`. Review the current state first, then complete the work; do not stop at another proposal or repeatedly ask whether to begin. This instruction authorizes relevant repository source and documentation edits, not live theme activation, package installation, commits or publication.

## Context and destination

I am building **Anodize**, my adaptation of Aether, as a core part of Dots' theme system. Core and CLI come first. I eventually want an Android APK and possibly a TUI with a workflow inspired by Aether's desktop app. The TUI is optional and is not a required step before Android. Do not start either frontend in this task.

The implemented foundation includes the pure Go core, Python authoring adapter, existing journaled publisher, standalone `anodize` and `dots anodize`, local Neovim integration, Bash/Zsh/Fish completions and a generated manual. Do not recreate completed functionality. General Dots Go migration remains paused; focused Anodize work is the authorized exception.

Paths:

- Dots: `/data/data/com.termux/files/home/repos/dots` (it may resolve to `/data/data/com.termux/files/home/dots`).
- Separate plugin: `/data/data/com.termux/files/home/repos/Anodize.nvim`. This is the final path, not `~/repos/nvim/Anodize.nvim`.
- Read-only Aether reference: `/data/data/com.termux/files/home/src/go/aether`.
- Read-only hook-manager reference: `/data/data/com.termux/files/home/src/shellscript/theme-hook-plugin-manager`.

The other plugin agent finished its handoff. Read `~/repos/Anodize.nvim/docs/dots-integration.md` for consumer requirements. That repository has its own instructions and Git history; this task does not authorize changing it. Dots-owned nested Neovim changes are allowed when necessary, following its local instructions and preserving unrelated work.

## Read and establish the baseline

Read the current `AGENTS.md`, relevant guides under `agents/guides/` (worktrees, commands, testing, documentation, managed files and platforms as applicable), `plans/anodize-next.md`, `plans/anodize.md`, and `docs/anodize.md`. Read `docs/safety.md` before any mutating-path change, and use `docs/presentation.md`, `docs/architecture.md` and `docs/testing.md` as the relevant contracts. Inspect `anodize/PROVENANCE.md` before adapting upstream code.

Inspect Git state before editing. There is substantial in-progress work across the parent and nested repositories; treat recorded test counts and paths as a baseline to verify, not guaranteed current facts. Do not reset, clean, stash, revert, rewrite history, initialize submodules or overwrite unrelated staged, unstaged or untracked files. Use the existing main checkout by default; ordinary maintenance needs no new worktree.

## Implement this scope

1. Reproduce the two recorded Zsh failures in disposable fixtures: `test_shellmod_uses_running_shell_and_corrected_alias` and `test_startup_without_optional_tools_or_plugins`. They previously failed with Anodize completion removed. Fix the actual alias fallback and fixture assumptions supported by reproduction. Preserve my existing eza flags/layout, cover eza present and absent, and avoid reliance on my installed tools. Do not merely weaken assertions to get a green result.
2. Review the core/CLI/publisher/editor boundaries for reproducible correctness gaps. Make recipe, engine-protocol and published-palette ownership/versioning clear. Preserve schema-1 role authority and additive normalized colors. Do not declare a private engine protocol public without a deliberate separately justified contract.
3. Exercise image/seed/import, edit, preview/export, save, publication, editor reload and undo/recovery in isolated workflows. Reuse existing tests. Add focused coverage only for meaningful missing boundary behavior, such as malformed inputs, missing files/engine, collisions, interrupted operations, idempotence and drift refusal. Fix defects found without broad refactoring.
4. Keep help and completion engine-free. Keep CLI parser, static metadata, all three completion adapters, generated manual and examples synchronized. Completion must not execute extensions or create persistent state.
5. Update affected source-of-truth documentation and plan status with actual results, limitations and any narrowly deferred issue. Prepare concrete optional visual checks for me if useful, but do not run normal live Neovim, publish a live theme or call a real wallpaper API.

## My working and product preferences

- Be autonomous within the scope: implement, verify and finish. Ask only when missing information materially affects correctness or when an actual authorization boundary blocks work. Explain the exact source of a real permission requirement. Give concise progress updates with findings and next actions.
- Protect existing data and make changes reviewable. No commits, pushes, tags, releases, installs, destructive cleanup or live activation unless I explicitly authorize them. Ordinary relevant repository edits are already authorized.
- Termux is the first target. Keep Linux, WSL and native Windows boundaries explicit; distinguish native evidence from simulation and unverified platforms. Do not assume Android APKs can use the Termux Bash/Python environment.
- Keep the core modular, fast and useful without optional interactive tools. Prefer simple shared implementations. Reuse the current transaction engine and presentation helpers; do not duplicate their policy in Go or a future frontend. No hidden downloads, startup scans or unnecessary dependencies. Measure before adding caching or complexity.
- Make human output polished, cohesive and colorful using varied semantic/theme colors. Keep ordinary discovery concise, with grouping/counts and details available explicitly; do not restore walls of repeated Source/Target lines. Use readable plain fallbacks and check representative narrow and wide terminals, including 40/80/120 columns where applicable.
- Preserve exact machine interfaces: JSON, raw paths, scalar values, completion candidates, generated shell code and explicit ANSI-value output. Respect TTY detection, `NO_COLOR`, explicit color preferences, pipes and exit status. Never let literal escaped ANSI sequences leak into human help again.
- Shell adapters should preserve argument order, unknown options, streams, working directory and exit status. Keep startup cheap. Zsh/FZF-tab descriptions should be readable while inserted values remain raw and correct.
- Managed changes need visible previews, complete preflight, durable journals, recoverable backups, reverse-order rollback, idempotence and drift-safe undo. Saving an authored theme must not silently activate it. Keep wallpaper changes explicit and hooks bounded.
- Preserve my Neovim appearance and behavior: personal highlights, selected Mocha look, transparency, inactive-window treatment, lualine layout and dashboard motion/timing/lifecycle. Keep `DotsThemeReload` working. The local Anodize.nvim repo remains separate; native colorschemes remain available for manual use.
- Never print, source, diff or log real secret values. Use metadata-only diagnostics. Tests must own disposable home/config/state/cache/repository roots and never use my live data, editor startup or package manager as fixtures.
- Preserve upstream attribution and exact provenance. A README license statement and a missing standalone license file are facts to record, not grounds to fabricate notices or claim release clearance.
- Keep documentation truthful and synchronized. Separate implemented, proposed, paused and unverified work. Preserve historical evidence as dated evidence. Do not advertise future commands or an installed manual when only a repository manual exists.
- Reach for `rg` first; if it cannot execute in this Termux environment, immediately use bounded grep/Python/Git file lists rather than repeatedly retrying or scanning all of my home.
- Keep tests proportional and meaningful. Run focused checks and then relevant safe broader suites. Do not add tests that merely mirror implementation, or repeatedly rerun successful suites without a change or unresolved concern.

## Verification and finish

Inspect current runners before using them. `python3 -B tools/verify_anodize.py check` builds a temporary engine and runs Go tests/vet plus CLI checks. Use `tools/test_anodize_integration.py` and `tools/test_anodize_nvim.py` for their boundaries, `tools/test_zsh.py` for the shell repair, and `python3 -B tools/zsh_interactive.py --samples 3` for the interactive shell checks. Run relevant existing theme/workflow/file/dispatcher suites when affected. Use Python's `-B` option to avoid bytecode artifacts.

Check generated artifacts with `python3 -B tools/generate_anodize_integration.py --check`, lint `man/anodize.1` with `mandoc -T lint`, verify Markdown links with `python3 -B tools/verify_core.py docs`, and run `git diff --check`. Report unavailable optional tools accurately; do not silently install them. Measure affected startup paths if behavior changes.

Finish with what changed and why, the actual verification results, remaining risks or unverified behavior, and the next bounded step toward the APK or optional TUI. Separate native Termux tests, simulated tests, isolated Neovim evidence and live visual checks. Leave the changes uncommitted and preserve all unrelated work.
