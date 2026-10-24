# 0011: Platform profiles and native startup bundles

**Status: Accepted and implemented. Native desktop acceptance is tracked separately.**

Universal repository trees remain universal. Platform overrides live beneath
`profiles`, with explicit distro layers and WSL inheritance from Linux.
Definitions are data; profile inspection does not execute initialization code.
Configuration replacements reuse catalog ownership and transaction semantics.

A shared environment registry supplies diagnostics and native initialization.
Explicit values take precedence over defaults. Runtime hook evidence records
names and provenance without persisting private values. Python prepares native
Bash/Zsh startup bundles; ordinary warm startup loads native code. Personal
interactive setup remains distinct from lightweight `dots init` integration.

Missing-checkout bootstrap may acquire public source after an installed startup
snippet requests it. It must not update an existing checkout, install packages,
initialize private/optional submodules, or install application configurations.

Androidots and Windots become bundled platform source snapshots with stable
catalog identities, temporary compatibility paths and externally archived Git
history. The nested Rainmeter source remains an optional pinned submodule.

See [profiles](../profiles.md) for the data and startup behavior and the
[implementation plan](../../plans/platform-profiles.md) for acceptance evidence.

## Follow-up: platform file identities

The subsequent [platform identity cleanup](../../plans/platform-file-identities.md) replaces the original stable-ID choice at the CLI/catalog surface with `termux` and `windows`. Legacy identities remain readable internally for ownership and recovery; persisted history is not rewritten by inspection.
