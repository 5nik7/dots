# Anodize next steps

**Status: Proposed.** Recommended follow-up to the [implemented slice](anodize.md), not authorization to build a frontend or activate live configuration. General Go migration remains paused; Anodize is a scoped exception.

## Recommendation

Finish foundation hardening before adding another consumer. The core, authoring CLI, shell completions, manual and local editor integration exist. The remaining uncertainty is the complete workflow across their boundaries and the recorded verification limits, not whether these components need implementing again. No additional runtime defect is asserted by this planning review.

The immediate concrete issue is the two existing Zsh alias failures recorded in [Zsh startup](zsh-startup.md#current-regression-checkpoint-2026-09-25). Resolve that small shell issue separately within the follow-up, preserving the current eza presentation, so later Anodize changes have a useful shell baseline.

## Bounded implementation sequence

1. Inspect current Git state, local instructions and existing tests. Preserve unrelated changes and distinguish the parent checkout from nested Neovim and the separate Anodize.nvim repository. Reproduce reported failures in disposable roots before fixing them.
2. Correct the Zsh alias fallback and fixture assumptions as supported by reproduction. Cover eza present and absent without depending on the developer's PATH. Preserve the existing eza flags and listing layout; do not merely weaken failing assertions.
3. Review the authoring recipe, private engine JSON and published palette contracts against their consumers. Document ownership, supported versions, validation and compatibility in [Anodize reference](../docs/anodize.md) and [architecture](../docs/architecture.md) where needed. The private executable protocol is not automatically a supported public frontend API. Preserve schema-1 role authority and additive normalized colors.
4. Exercise the existing image/seed/import → edit → preview/export → save → publish → editor reload → undo/recovery workflow in isolated fixtures. Reuse the existing suites and add only meaningful missing boundary cases. Cover malformed inputs, missing engine/files, collisions, no-op saves, interrupted operations and post-apply drift where the relevant contract requires them. Correct reproducible defects with the smallest coherent changes.
5. Keep engine-free help/completion and generated manual/metadata synchronized. Verify no persistent state is created by read-only inspection. Apply the shared [presentation acceptance gate](../docs/presentation.md#acceptance-gate) to changed human views, including narrow/plain output and clean data modes.
6. Record the resulting acceptance evidence and remaining limits. Prepare a concrete optional visual-check procedure for the owner if useful; do not launch the normal editor, publish a live theme or call a real wallpaper API automatically.

## Ownership and non-goals

Dots owns the core/CLI, publisher and its editor configuration. The finished plugin handoff is in `~/repos/Anodize.nvim/docs/dots-integration.md`; inspect it read-only for this scope. A necessary plugin change needs a clearly identified separate scope and its repository's instructions. Preserve personal editor highlights, transparency, lualine layout and dashboard animation behavior.

Do not resume general Go migration, create another transaction engine, introduce arbitrary hooks, build an APK/TUI, fetch online theme sources, install packages or publish releases in this task. `man/anodize.1` is available for local viewing; that does not mean it is installed in the system manual path. Source provenance remains in [PROVENANCE.md](../anodize/PROVENANCE.md). The recorded absence of a standalone upstream license file is a release question, not permission to invent notices or a claim of legal clearance.

## Verification and acceptance

Use the existing entry points documented in [testing](../docs/testing.md); inspect their current behavior before running them. All runtime checks must own their home/config/state/cache/repository roots.

- `python3 -B tools/verify_anodize.py check` builds a temporary engine and runs Go tests/vet plus CLI acceptance.
- `python3 -B tools/test_anodize_integration.py` and `python3 -B tools/test_anodize_nvim.py` cover shell/manual and editor boundaries.
- `python3 -B tools/test_zsh.py` and `python3 -B tools/zsh_interactive.py --samples 3` verify the shell repair and real Zsh/FZF-tab behavior.
- Run the relevant existing theme, workflow, file and dispatcher suites when those boundaries change; do not expand unrelated testing without a reason.
- `python3 -B tools/generate_anodize_integration.py --check`, `mandoc -T lint man/anodize.1`, `python3 -B tools/verify_core.py docs` and `git diff --check` verify generated artifacts and documentation.

Acceptance requires corrected or explicitly explained reproduced failures, consistent consumer contracts, successful relevant isolated workflows, preserved human/data output boundaries and truthful documentation. Report native Termux, simulated platform, fixture/editor and unverified live behavior separately. Measure affected startup paths before adding caches or complexity. Do not turn unavailable optional tools into claims of successful coverage.

## Later frontend sequence

After this foundation is accepted, choose a separately scoped frontend task. The owner's intended destination is an Android APK; a TUI is optional, not a prerequisite for Android.

- An Android feasibility slice should establish how the pure core is packaged, how Android-owned storage and lifecycle work, and which actions can operate inside an app sandbox. Native APK integration must not assume a Termux Bash/Python publisher is available. Begin with an isolated palette extraction/preview prototype before promising managed desktop publication.
- If the owner chooses a TUI first, scope a palette browser and extraction/edit preview prototype that uses the established core/consumer boundary. Route saving and publication through the existing safety contract rather than inventing frontend-specific mutations.
- Installation, distribution, source-license review and releases remain separately scoped work. Neither frontend is described as implemented or supported today.

The [next-agent prompt](prompts/anodize-hardening.md) carries the immediate task and recorded working preferences.
