# 0004: Preserve active configuration file links

Accepted and implemented 2026-10-21 for 0.1.12, owner approved.

Starship discovers `~/.config/starship.toml` without an environment override.
Dotfile checkouts commonly link that file to a regular repository file. Normal
Blastoff writes now preserve the file-link chain and update its pinned target.
This supersedes the blanket active-link refusal in decision 0001.

Resolve only active leaf links, reject loops/dangling links and special objects,
and retain strict parent-directory write checks. Recheck link identity after
locking and before publication. Fingerprints detect target edits; library themes
and modules cannot become normal active-write targets. Explicit `--replace-link`
retains conversion, backup metadata and the untouched old target.

Locks and provenance use the resolved path. Read-only lookups consult only the
canonical record and configured-alias record, never scan history. Conflicts or
pending markers cannot authorize an implicit overwrite. Explicit mutations archive
legacy alias records before completing canonical tracking. Backups record both
paths and link text; restoration updates the existing target, not link topology.
The `config` JSON field retains the user's configured path; `resolved_config` is
additive in current/doctor. Human output labels the two paths.

Shared Python owns both Bash and PowerShell behavior. Termux tests exercise real
file links and races; Windows path-spelling fixtures are not native Windows proof.
Native Windows file-link, privilege and reparse checks remain pending in
[WINDOWS-CHECKS.md](../WINDOWS-CHECKS.md). Cooperating locks and final drift checks
do not provide a sandbox against concurrent hostile filesystem replacement.
