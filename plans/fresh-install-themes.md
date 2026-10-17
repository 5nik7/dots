# Fresh-install theme recovery

**Status: Implemented.** Fix the missing FSH source directory in clean clones,
and prevent setup/refresh from reusing incomplete theme generations.

- [x] Retain `config/fsh` through tracked documentation; leave its generated connector ignored.
- [x] Share completeness checks across setup and the publisher. Prepare and validate new generations before journaled publication; retain old payloads and backup baselines.
- [x] Distinguish FSH artifact, compilation and cache failures without doing publication during shell startup.
- [x] Verify tracked-source-only installation, repeat/restore, missing artifacts/pointers, failed preparation, ownership conflicts and native Zsh consumer behavior in owned roots.
- [x] Follow the [presentation gate](README.md#presentation-gate-for-every-plan), preserving JSON and nonanimated dry runs.

## Verification — 2026-10-17

- Installation: 21 tests passed, including clean public sources with simulated WSL detection, missing-output/pointer repair, failed preparation and rollback after active-pointer replacement.
- File catalog: 9 passed; missing-source check: 16 passed; installation adapters: 5 passed, 4 skipped for unavailable native runtimes/platform capabilities.
- Vivid/FSH: all 14 cases covered successfully through the full run and focused reruns. Fixed stale test dependencies on the removed personal `njen.ini` and the former Vivid template tokens; no retired personal config was restored.
- Theme publisher: 6 focused atomicity, idempotence, recovery, unsafe-state and Zsh-hook cases passed. Shell environment: 8 passed; native hook contracts: 4 focused cases passed. The default-shell test's obsolete personal-loader fixture also failed on baseline HEAD and was corrected to use library loaders.
- Resource presentation: 11 passed; progress: 11 passed. Native Zsh warning checks passed at 40/80/120 columns in automatic and disabled color modes, with one warning, complete wrapped paths and no animation. A FIFO supplied as the theme artifact was rejected without blocking.
- Warm native FSH adapter timing: baseline 17.682 ms/call, updated 17.808 ms/call (median of three sequential 30-call batches in an owned fixture). This measures the affected warm adapter, not full shell startup or WSL performance.
- Edited shell/Python syntax, focused ShellCheck, whitespace and relative Markdown links were checked. Core ShellCheck retains its pre-existing dynamic `dots_options` SC2154 notice; changed publisher/setup/shell files pass the focused check with the repository's dynamic-source exclusions.

Native Termux execution and WSL platform fixtures are separate from native WSL
verification. Native Windows theme publication remains outside this change.

## Vivid compatibility follow-up — 2026-10-17

**Status: Implemented.** The owner supplied a Vivid panic during preparation:
`Color value should be a string`. Older Vivid parsers require scalar font styles;
Dots previously emitted lists even for a single attribute.

- Emit scalar single attributes; retain combined lists with Vivid 0.10+.
- For older/unrecognized versions, select the first supported attribute in the
  existing order. Retain full JSON/Lua styles and exact final LS_COLORS core and
  explicit suffix rules. Report category/direct-Vivid limitations once through
  shared human diagnostics, including setup's captured preparation bridge.
- Preserve custom templates and failed-publication safety. Include the template
  source and Vivid version in generation failures; never silently use basic
  coverage after a present Vivid fails.
- Verify old/unknown/current/absent/failing Vivid, fresh FSH setup, no-op repeat,
  custom overrides, rollback and plain/colored/data presentation in owned roots.
- Update the file-color, theme, setup and command references and README. Do not
  install packages, publish live themes or claim native WSL validation.

### Follow-up verification

- Vivid/FSH: 16 integration tests passed, including legacy/unknown-version
  fixtures and installed Vivid 0.11.1. A separate native PTY case passed all six
  40/80/120-column automatic/plain-color scenarios, with one complete notice and
  progress cleared before diagnostics.
- Installation: all 23 tests passed. The tracked-public-source WSL-detection
  fixture now exercises legacy Vivid behavior, FSH publication, repeat setup and
  restoration. Additional cases cover colored human notices, plain JSON-mode
  stderr and custom-template failure without pointer/receipt changes.
- File colors: all 11 cases passed across the suite and focused rerun. The
  standalone Lua validator initially failed because its fixture did not preload
  the current Yazi validator's `.color-refs` dependency. The identical failure
  reproduced with unchanged HEAD publisher files; corrected only the test loader
  to load the real dependency. No Yazi runtime source was changed.
- Five existing publisher cases passed: atomic/idempotent publication, failed
  publication rollback, initial rollback/drift refusal, SIGKILL recovery and
  unsafe/concurrent state refusal.
- Edited Python/Bash syntax, whitespace and 713 relative Markdown links passed.
  Focused ShellCheck passes with the existing dynamic-source/string exclusions
  and the pre-existing render.bash SC2015 informational condition excluded.

Native WSL and an actual legacy Vivid executable were not available. Legacy
parser fixtures are separate from the installed Vivid 0.11.1 checks. No live
setup, theme refresh, package installation, commit or push was performed.
