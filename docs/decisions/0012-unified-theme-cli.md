# 0012: One theme command family

**Status: Accepted, 2026-09-29.**

## Decision

The owner requested one theme system, confirmed `dots theme` as its name, selected full theme IDs, and requested retention of native palette browsing. This supersedes the plural CLI compatibility guarantees in decisions 0007 and 0008; their data, safety, and publication contracts remain in effect.

Remove `dots themes` and `dots-themes-*` without compatibility aliases. Selection uses full IDs such as `catppuccin-mocha`; separate family/flavor arguments are removed. Keep palette discovery under `dots theme list --families` and `--flavors FAMILY`, and native palette display/query under `show --native` and `color --native`. Native queries explicitly distinguish upstream values from application semantic colors.

## Consequences

All first-party callers migrate together. External scripts using the removed routes must adopt the [unified syntax](../themes.md#migration-from-plural-commands). Existing generation paths, schemas, palette data, and shell palette helper APIs remain valid. No active theme change or state migration accompanies this CLI change. General Go development remains paused; independent protocol fixtures do not define supported live theme commands.
