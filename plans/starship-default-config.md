# Starship default configuration and Blastoff 0.1.12

Status: implemented and verified on Termux, 2026-10-21.

Stop exporting STARSHIP_CONFIG; clear recognized old Dots values during native
startup/reload and preserve explicit unrelated overrides. Use the home-relative
Starship default in the managed catalog, retaining the existing repository link.
Include Windots Clink and all native startup adapters. Preserve Anodize work.

Blastoff resolves active-file aliases to a pinned regular target for normal
operations, with link drift guards, physical-target locks, backup/recovery and
canonical provenance. Explicit --replace-link retains its conversion behavior.
Parent-directory, library-target and special-object protections remain strict.
Update both shell frontends through the shared Python core and document Windows
native acceptance separately from Termux fixtures.

Verify isolated shell/default-path, palette adapter, link/alias races, mutations,
editing, provenance and installer upgrades. Build and verify 0.1.12, inspect the
live installer dry-run, then perform the authorized Termux upgrade. Preserve
the installed configuration, themes and recovery data; perform only read-only
live smoke checks. No Git publication, theme activation or custom prompt execution.

Verification on native Termux:

- Default cleanup/catalog/Clink fixture runner passes; Bash, Zsh, Fish and
  Nushell each cover unset, stale, custom and repeated initialization. Native
  PowerShell is absent; Xonsh's installed launcher has a missing interpreter.
  Windows Clink behavior has only Lua-fixture evidence.
- Eight affected native startup/reload checks and all eight shell-environment
  checks pass. Two managed-file observation/ownership checks pass.
- Palette suite: eight pass, including the new default-link/custom-XDG case;
  existing saved-theme module coverage fails for missing `jj_bookmark.style`.
  Re-running its original test confirms the same failure. Original-source
  comparisons also reproduce the broader Bash optional-activation and Zsh
  private-hook/reload failures. Those unrelated issues remain unchanged.
- Blastoff full suite: 287 run, seven skips, no failures (215.296 seconds).
  Final guard refinement: 99 affected tests run, one Windows-only skip, no
  failures (67.888 seconds); includes twelve active-link/default-path tests.
- Bash/Zsh/Fish syntax, Python compilation without bytecode, manual lint and
  changed Markdown link targets checked. Native Windows/PowerShell acceptance
  remains pending and is documented in Blastoff's Windows checklist.

Package and upgrade completed:

- Verified 176-file ZIP and tar.gz inventories. The isolated archive rehearsal
  uses actual checksum-verified 0.1.11 source and passes upgrade, relocated
  execution, default link/history, completions, uninstall and data-retention checks.
- Twenty paired startup samples after five warmups show similar 0.1.11/0.1.12
  version/help/current latency; full values are in Blastoff's docs/STATUS.md.
- Reviewed the live public installer dry-run, then upgraded the existing Termux
  prefix to 0.1.12. It installed the 41-file runtime and refreshed launcher/manual;
  no profile changes were planned or performed.
- Installed version/doctor/current pass with STARSHIP_CONFIG absent. The default
  link resolves to the existing repository file. Both link/content hashes and
  all 135 saved Blastoff data-file hashes match the pre-upgrade snapshot.
- No live theme activation, prompt execution, Git commit or publication. Existing
  Anodize work and the user's modified provenance file remain untouched.
