# Shared preferences and complete command delivery

Status: Implemented; final verification and native limits are recorded below. Scope: requested Bak completion, preference separation,
portable appearance import, Termux promotion and durable delivery requirements.

## Decisions

- `default/config.json` and `profiles/NAME/config.json` hold Dots behavior,
  formatting and shell settings. Adjacent `colors.toml` and `icons.toml` hold
  appearance declarations. `profile.json` retains identity, inheritance, aliases,
  environment, paths, command replacements and managed file mappings.
- Reads retain profile > parent > defaults precedence. Unqualified preference
  writes and the Config browser target shared defaults; `--profile NAME` targets
  that profile. Native pkgs, Weather and Codex-alert files remain authoritative.
- Legacy inline preferences remain readable. Migration is guarded, journaled,
  reversible and idempotent; it preserves effective values and structural data.
- `dots config import SOURCE --profile TARGET` merges portable appearance;
  imported declarations win and unrelated target values survive. Omitting a
  target imports into shared defaults. File mappings, environment, paths,
  package choices, backup locations and native application files are excluded.
- Promote Termux appearance to shared defaults and remove corresponding Termux
  overrides so later default edits take effect. Do not publish themes or reload
  applications as part of this repository migration.
- Bak completion uses the trusted metadata and bounded catalog reads, never
  payload inspection, extensions, prompts or writes. Cover standalone `bak`,
  `dots-bak` and `dots bak` through Bash, Zsh, Fish, PowerShell, Nushell and Xonsh.

## Work packages and acceptance

1. Bak completion: commands/options, literal paths, choices and backup IDs;
   all six adapters registered; malformed catalog safely yields no IDs.
2. Preference storage: separated readers/writers, correct provenance, guarded
   migration, shell settings and cache invalidation; native files retain ownership.
3. Shared saves/import: explicit target handling, source-wins appearance merge,
   Config review integration, Termux promotion and unchanged structural manifests.
   Depends on 2.
4. Delivery requirements/docs: command and script checklists require completion,
   presentation, useful popup/config integration, README/wiki and bootstrap review.
   Bootstrap becomes discoverable in the main README. Depends on 1–3.

Owner: Config/profile maintenance for preferences; command maintenance and shell
integration for completion. Configuration integration: update existing Config
scope/storage/import controls; Bak completion adds no preference. Menu integration:
update Config scope/review for imports; Bak keeps its existing browser. Bootstrap
integration: verify existing core publication carries the changed adapters and
preferences; add assets only if that audit identifies a missing dependency.

## Verification and completion

Use owned home/config/state/cache/repository roots. Cover migration equivalence,
inheritance, missing files, stale guards, rollback, import exclusions, repeated
no-op, native ownership, exact JSON/scalar/completion output and literal paths.
Run focused Config/profile/shell/completion suites, metadata checks, syntax,
relative Markdown links and wiki preview/build/check. Measure startup-sensitive
input changes. Record unavailable native PowerShell 5.1/7, Linux/WSL and optional
shell runtimes as pending, distinct from adapter/fixture evidence.

Save goals with the Todo CLI, rereading before writes. Start each package as work
begins; append evidence and complete verified children before the parent. Preserve
unrelated work. No commits, pushes, host installation or live reload is included.

## Implementation evidence and ownership audit

Todo parent and all four children are **done**. Parent:
`6327b1e6c1f44135a312aef14a3987cb`; children, in work-package order:
`3d564a6f6ff149bd964522a915e10af2`, `2437c4f5220045ebbf933a972435c737`,
`0bd3ae7fd7de4d20a3ed5bb1a28ad10f`, `13da988d253149c0b8a43fa12d64138b`.

The static audit covered nine source areas, including 24 default files and 108
profile files. Candidates are not missing-control claims. The migration addresses
inline settings/apps/formatting and typed popup/menu/FZF/Neovim appearance;
`config.json` is now recognized as a declaration by the audit helper. Specialized
file-style catalogs, Git configuration, palette/templates, and native application
files retain their owners and formats. No unrelated controls were added.

Shared typed appearance is in reserved `[controls]` TOML tables, retaining public
key names and Python 3.9-compatible literal parsing. Imports include declared
parent/profile customizations; `defaults` is an explicit source option. Import
review uses the shared Config selector with Cancel first. Native applications stay
accessible through their existing CLI and active-profile browser scope.

Bootstrap review: no new bootstrap acquisition step is needed. Core installation
already publishes Bak and the checkout dispatcher; initialized shells read the
checkout's shared completion adapters. The new Config route and preference files
travel with that checkout. Fresh-machine bootstrap is now in README's Get started
section, and the bootstrap guide records the delivery audit requirement.

Repository migration/promotion recovery transactions (chronological):
`e83f74d8b2bf4160b4d3a4e9ec9d642f`, `b277bef581bd4011bc690c8e9d80349d`,
`7b4a34f07dc24617aef83bd0de6ea932`, `2f03c94c80bd40a8b8e4a6dd402383f7`.
The latter pair includes bracketed FZF keys and removal of empty override objects.
Termux consumer projections and typed values were compared before/after; structural
profile fields were preserved. Repeating layout migration plans no operations.
No host install, theme publication, application reload, commit or push occurred.

## Verification evidence

All writable fixtures own their checkout/home/config/state/cache roots; popup
checks use private tmux clients. The following checks passed on Termux:

| Area | Evidence |
| --- | --- |
| Bak completion | Provider/CLI 10 cases; actual Bash, Zsh, Fish, Nushell and Xonsh adapters pass; PowerShell runtime unavailable. |
| Separated preferences/import | 8 cases, including layout equivalence, source-wins exclusions, nullable shared reset, failed publication rollback, stale guards, retained undo, repeat no-op, and invalid separated settings rejected by `config check`. |
| Config/profile integration | Typed Config 14; profile Config 10; profile backend 14; styles 7; existing key migration safety cases 3. |
| Config browser and refresh | 17 unit/browser cases and 12 live-refresh cases verified, including focused reruns after fixtures were updated for shared scope and promoted indicator labels. |
| Popup and installer | Three private Config popup cases at 40/80/120 columns, including simultaneous Cancel/Save and shared saves; setup wizard 7 cases. |
| Startup cache | Creation, edit and removal of profile `config.json` invalidate Bash/Zsh bundles; warm reads after regeneration do not invoke Python. |
| Completion integration | Config completion 5 cases, including real Zsh/FZF-tab branch/value/glyph previews; command suite 28 cases verified, including a focused rerun after its compadd stub was corrected to find `-S` after `-U`. Bash and native-controller import-source candidates agree. |
| Repository contracts | Four profile checks and Config check pass; repeat layout preview has no operations. All current manifests have no preference groups; typed appearance is stored in the matching TOML files. Metadata validates 284 external commands; generated manual is current; eight maintenance skills validate. |

Current startup baseline, measured sequentially in owned public fixtures with
optional theme/completion initialization disabled: Bash cold 1639.470 ms, warm
median 92.941 ms; Zsh cold 1311.988 ms, warm median 82.391 ms (five warm samples
each, including process startup). These are current measurements, not a claim of
before/after improvement or native Linux/Windows equivalence.

Native Windows PowerShell 5.1/7, native Linux and WSL startup/terminal acceptance
remain pending. Native-controller and platform fixtures are separate evidence;
no host packages, shell activation, theme publication or application reloads were
performed. The available local wiki is rebuilt and checked from canonical sources;
this does not publish the wiki remotely.

## Remaining verification limits

The broader Zsh unit suite passed 26/29. Its three failures also reproduce from
an owned `git archive HEAD` snapshot: `test_platform_context_and_distribution_are_separate`
expects the retired MSYS identity; `test_startup_without_optional_tools_or_plugins`
fails its minimal-startup assertion; `test_theme_switch_and_repeat_preserve_palette_and_fzf_options`
references the absent `shells/zsh/fzf.zsh` and omits `default/file-colors.toml`.
These baseline failures remain unchanged. The broader `zsh_interactive.py` runner
reaches first prompt, bindings and reload, then stops because its fixture omits
`plugins/anodize/cli.py`; its Anodize wrapper is identical to HEAD. The dedicated
Config/FZF-tab and Bak native-shell completion checks above pass.

Bash/Zsh/Fish syntax and Python compilation pass. Standalone ShellCheck passes the
three Config wrappers and shell settings module; catalog/completion/integration
standalone analysis reports external-source or externally used-variable warnings.
Whole-input lint exceeded three minutes and 1 GB; disabling extended analysis did
not bound it. Per-file analysis isolates the timeout to `complete.bash`, which also
exceeds 15 seconds at HEAD. Full ShellCheck dataflow acceptance is pending; these
limits are not reported as passes.

Relative Markdown path checks include the maintenance skills (1648 references,
zero missing paths). Wiki preview/build/check is performed after canonical edits;
local generation does not authorize a remote publication. Final local build
transaction: `45d9e686838140f482cd6532b60f32fa`; `wiki check` reports
`healthy=true`, with no remaining generated-page differences.
