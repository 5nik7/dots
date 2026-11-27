# Dots wiki

Status: implemented and locally verified. Native Windows runtime and hosted rendering acceptance remain pending.

Canonical documentation stays in Dots. A portable `.dots/wiki.json` manifest owns page IDs, source mappings, sections, repository URLs and the default `~/repos/dots.wiki` checkout; `DOTS_WIKI_DIR` overrides its location. Generate Home, pages, a first-party metadata command reference and a global sidebar. Explicit builds use guarded transactions, preserve unknown files and refuse generated-file drift. Inspection never rebuilds or fetches.

Add overview/list/show/search/browse/open/edit/path/check/build/init commands and `dots git wiki info|status|sync|publish`. Ordinary Dots Git operations include the associated wiki unless `--no-wiki`; submodule-only routes retain their scopes. Source publication precedes wiki publication. Compare selected wiki content to selected/published source inputs without automatic staging. Preserve ownership, refspec, lock, fingerprint and incremental-operation semantics.

Add documentation and wiki maintenance skills, source-only CI generation checks, local drift checks and an initial local export. No commits or pushes are authorized. Preserve existing Dots work and the wiki branch/remotes.

Acceptance: isolated generator/navigation/link/CLI/data tests, transaction recovery, local-remote Git tests including selected-index freshness and partial failure, Bash/native parity, 40/80/120-column views, existing Git regressions, docs and whitespace checks. Follow the [presentation gate](README.md#presentation-gate-for-every-plan). Native Windows PowerShell 5.1/7 evidence is pending when unavailable.

## Verification

### Windows Git line endings

The wiki generator now compares UTF-8 content across the worktree, index and published source using LF for line endings. Rebuilding an older Windows export refreshes its inventory. Transaction preflight still checks exact file bytes. The regression fixture covers CRLF checkout, LF Git blobs, stale generator and page refusal, and an edit that changes only line endings after preview. The associated Git fixture checks both remote commits after a combined publication.

The Git and wiki commands share this generator across Bash and native PowerShell. The existing menus and configuration already select the same workflows. No configuration integration change needed. Existing completion, installer assets and Windows destinations apply. No README change needed because setup and first commands are unaffected.

PowerShell 5.1 and 7 each completed a combined `--all` publication to two test-owned bare remotes with a CRLF generator checkout. Both remote branch tips matched the local source and wiki commits. The 13 associated Git tests passed on WSL using LF shell scripts. On Windows, 16 generator tests passed, including the new provenance and byte-guard regression. Two POSIX cases were skipped and two interactive wiki browsing tests also failed on the original revision when run without a terminal. The installed Windows `dots git publish --all --update-packages --dry-run` selected the manifest and planned the wiki with no blockers.

### Earlier acceptance

Termux verification passed: 17 wiki tests and 10 associated-Git tests, including interrupted-build recovery, retained-backup undo, drift refusal, missing checkouts, explicit acquisition, selector cancellation, exact redirected bytes, source-branch restrictions and association changes during sync. Plain PTY views pass at 40/80/120 columns. Both command metadata controllers validate 132 external routes; the new skills pass skill validation.

Existing regressions passed: Git operations (27), native Git controller (24), submodules across both controllers (32), Bash framework (24), native CLI (13 passed, one PowerShell-runtime check skipped), profiles/bootstrap (13), and documentation checker (4). Relative Markdown links and whitespace checks pass. These are local fixtures, not native Windows or hosted CI evidence.

The local wiki export contains 27 pages, seven navigation sections, the sidebar, maintenance instructions and deterministic inventory. The initial export uses a retained transaction; a second build is unchanged and freshness checks pass. Its existing branch and remotes are retained. Neither repository was committed or pushed.

Warm status timing on this Termux device used isolated source/wiki repositories, one warm-up and seven alternating samples per configuration. Median source-only versus associated-wiki times were 423/885 ms through Bash and 381/693 ms through the native controller. Observed ranges were 391–941/846–1092 ms and 338–427/549–814 ms respectively. The added cost includes inspecting a second repository and, for Bash, delegating to the shared controller. No startup scan or cache was added; `--no-wiki` retains the original scope. These measurements are a local observation, not a cross-platform performance budget.

Pending acceptance: actual PowerShell 5.1/7 execution on Windows, the hosted Linux/Windows workflow, and GitHub rendering after separately authorized publication.
