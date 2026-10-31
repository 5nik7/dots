# Dots command skills and configuration review

Status: implemented and verified. Parent goal `1b5eb9b806a843b0b992d92c889d29c3` (`dots-skills`), normal priority.

Create repository-local maintenance skills and make configuration integration a required development assessment. Sources live in `.codex/skills`, with relative discovery links in `.agents/skills`; user-wide installation and command behavior changes are outside this work.

## Work packages

1. `d80ff6f5bd7e4a8f9f46f670da9dbb1d`: create `dots-config` for integration ownership, defaults, precedence, supported consumers, CLI/menu exposure, refresh, recovery and verification. Reuse existing catalogs and canonical documentation. Completed config goal `ad4dd159482a4810a29d808ac20dbafb` is context, not reopened work.
2. `deb574032fb140b4a7497c58f0c32c0f`: add dedicated Anodize, Blastoff, debug, env, fonts, Git, keys, pkgs and wttr skills. Depends on package 1. Retain existing family owners and link shared procedures rather than duplicating them.
3. `37536ef5e7c149d2a4cdcee28c4f651e`: require recorded add/update/no configuration integration assessments, audit existing skills, maintain the authoritative family-to-skill index, validate discovery and synchronize documentation/wiki. Depends on packages 1 and 2.

Every current first-party family must have one primary skill. Built-in help, command discovery and completion use command maintenance; initialization uses shell integration. Existing files/profile/theme/Todo/wiki/menu skills remain primary for their families. Shared plugin, configuration, presentation and documentation skills supply related procedures.

## Acceptance and verification

Validate all new/changed skills with the skill-creator validator. Check every skill reference and discovery link, and compare family coverage against static command metadata without executing extensions. Run command metadata, Markdown-link, whitespace and local wiki checks. Review skill instructions against actual controllers, source documentation and test entry points, including Bash/native PowerShell boundaries.

Configuration assessment for this change: no runtime integration change needed; this work changes contributor guidance and discovery only. Menu assessment: no menu change needed. No command or consumer is activated as a validation step. Native runtime claims are unchanged.

Start goals as work begins, append progress through Todo CLI, and complete verified children before the parent. Preserve unrelated working-tree changes; no commit or push.

## Implementation and evidence

Added ten skills with relative repository discovery links. Audited and updated all fifteen existing skills to route configuration work appropriately, preserving ordinary Todo operations, read-only planning and documentation-only maintenance. The [family index](../.codex/README.md#command-family-owners) owns the complete mapping. [AGENTS.md](../AGENTS.md), the [command guide](../agents/guides/commands.md#configuration-integration-review), the documentation guide and the menu-plan template carry the required review into future work. Configuration catalogs, route metadata and runtime behavior are unchanged.

Verified on Termux on 2026-10-30:

- All 25 skill definitions passed the skill-creator validator; all 25 relative discovery links resolve to their intended sources.
- All 169 skill Markdown references resolve. The 20 top-level mappings exactly cover four built-ins plus the families of all 234 first-party external metadata routes, with no duplicate or missing owner. `dots commands --check` validated all 234 external commands without executing them.
- Checked 47 explicit implementation/test paths in new skills and confirmed configuration routing in all 15 existing skills. Checked 154 local anchors across the affected source documents and skill definitions.
- `python3 -B tools/verify_docs.py` passed; `git diff --check` passed. Reviewed family guidance against current controllers and documented test entry points.
- Previewed and rebuilt the available local wiki, changing only its generated Commands/Profiles pages and manifest. `dots wiki check` reports healthy. Retained transaction: `ca186a805a0d40c78d102c22810e3df4`.

This is contributor-workflow and discovery work. Bash/PowerShell command behavior, Windows application destinations and platform support claims did not change, so no new native runtime acceptance is claimed. Existing native acceptance limits remain with each owning component. No user-wide skills were installed and no application activation, commit or push occurred.
