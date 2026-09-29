# Yazi remote host and repository ownership

Status: implemented and verified on native Termux, 2026-09-29.

Extend the existing Git-head refresh with one local, read-only `git-it info
--json` call. Retain only a validated icon and ownership boolean, and save or
clear them with the repository/status request generation. Rendering must never
spawn commands. Missing helpers, failed commands, or invalid metadata retain
the existing repository label and normal color. No Git configuration is changed.

Expose `show_remote_icon` (default true), `repo_color` (default blue), and
`repo_owned_color` (defaults to the normal color). The personal configuration
uses green for owned repositories. The host icon precedes the existing literal
prefix/symbol/name and shares its color; branch and status styling stays intact.
Both `repo_name` and `githead` use the same label. Ownership follows git-it's
configured host/namespace match, not authentication or write access.

Verify rendering, color fallback, malformed/failed/missing helper responses,
single-line icons, and stale requests with Lua fixtures. Exercise installed
git-it and Yazi in the native PTY runner with test-owned configuration and local
Git remote fixtures for GitHub, GitLab, Bitbucket, unknown hosts, and no remote.
No network access is needed. Preserve plain Git labels without the optional
helper, readable spacing, and independent branch/status colors as the applicable
presentation acceptance gate. Native evidence is limited to Termux; the Bash
helper is optional and no native Windows claim is made.

Synchronize the plugin and configuration READMEs, repository overview,
architecture ownership, and testing instructions. Run focused Lua/native
checks, documentation validation, and whitespace checks. Leave changes
uncommitted and preserve unrelated work.

## Verification

- Lua dispatcher, Git-head metadata, symlink, and LS_COLORS fixtures passed.
  Metadata fixtures cover missing/failed helpers, invalid JSON/types, single-line
  icon cleanup, omitted ownership-color fallback, hidden icons, unchanged status
  colors, command-free rendering, and outdated request/directory rejection.
- Native Yazi 26.9.1 plus installed git-it passed host/ownership cases, SSH host
  aliases and nested namespaces with isolated local remote/config fixtures. The
  existing project, pane, folder-rule, style, and resize checks passed too.
- 350 GNU ls comparisons passed. Native hard-link creation remains unavailable
  on this filesystem; Lua fixtures cover its matching behavior.
- In five isolated native local refresh samples, the existing four Git commands
  took a median 37.0 ms, versus 150.4 ms including the metadata command. The
  added cost is asynchronous and incurred only on existing refresh events;
  redraws run no commands. These small-fixture timings are not a large-repository
  benchmark. No additional cache was introduced.
- Lua syntax, relative documentation links, and whitespace checks passed.
  Native Windows and visual glyph/font appearance remain unverified.
