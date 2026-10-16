# 0013: Dots environment and theme collection ownership

**Status: Accepted, 2026-10-16.**

The owner requested library-owned shell integration, data-only customization,
useful runtime variables, and a distinction between the current theme and the
theme collection. This supersedes decision 0012's prohibition on plural routes;
its shared palette engine, full selectable IDs and publication contracts remain.

`dots init` initializes only Dots integration. Personal configuration stays in
`shells/`. `config.env` is parsed as data using a common settings definition;
runtime defaults are not exported as user overrides. Published theme state stays
separate from user preferences. Diagnostic queries are limited to Dots values.

`theme` and `dots theme` inspect or change the current theme. `dots themes` owns
collection listing, picking, source management and plugin management. Existing
singular collection routes remain aliases of the same implementation. Bare
`theme` shows a summary; `theme current` stays a scalar query. No standalone
`themes` executable is added.

Retiring repository files requires the owner's requested deletion review.
Migration does not authorize private-module edits, removal of `$HOME/.theme`,
or unrelated cleanup. See [the environment contract](../shell-environment.md)
and [implementation plan](../../plans/shell-environment.md).
