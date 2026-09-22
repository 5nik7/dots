# 0006: Modular Bash Command Framework

Status: Accepted
Date: 2026-09-22

## Context and Decision

The owner approved developing the live Bash command while Go work is paused:
repository/local discovery, optional comment metadata, colored Nerd Font output,
and on-demand Bash/Zsh/Fish completion. This implements the command framework,
not actual theme, package, installation, or transaction features.

`bin/dots` uses a Bash 4.4+ dispatcher and narrowly loaded modules under
`lib/dots`. Normal dispatch probes exact longest-prefix filenames and uses
`exec`; only help, listing, validation, and Tab requests enumerate command files.
Adding an executable registers it immediately without editing a registry.

The [Bash command contract](../commands.md#implemented-bash-command-framework)
owns roots, metadata, presentation, and completion semantics. Default roots are
`$DOTS/bin` and `$DOTS/local/bin`; explicit additional roots are permitted.
Duplicates fail. Optional static comment headers supply descriptions and argument
hints without executing commands. The shared catalog supplies help and all three
completion adapters. There is no persistent catalog cache or startup scan.

Terminal output defaults to ANSI colors and Nerd Font icons; explicit flags and
environment variables select auto/always/never modes. Extensions opt into shared
Bash helpers. The dispatcher does not intercept their output or claim to enforce
an extension's behavior. There is no automatic elevation or installer.

## Relationship to Earlier Decisions

This is the authoritative protocol for the live Bash executable. It supersedes
applying decisions 0003–0005's explicit-roots-only, mandatory-JSON, no-symlink,
and static-Zsh-only restrictions to this Bash surface. Those decisions remain
unchanged for the separate Go development executable. The Go language decision,
existing source, tests, and CI are preserved; further Go development stays paused.
The reserved core namespaces remain protected in Bash.

## Alternatives

PATH-wide discovery was rejected in favor of repository/local roots and explicit
extras. Required sidecars were rejected for the Bash authoring workflow. Runtime
metadata handshakes were rejected because help and completion should not execute
extensions. Explicit completion regeneration was rejected in favor of seeing
changes on the next Tab. Color filters around arbitrary command output were
rejected in favor of opt-in shared rendering and unchanged streams.

## Validation

Isolated dispatcher tests, native Bash/Zsh/Fish Tab tests, existing Zsh/FZF-tab
acceptance, and sequential scaling measurements are recorded in the
[focused plan](../../plans/bash-dispatcher.md). Termux native evidence does not
establish native Linux, WSL, or MSYS acceptance. No PowerShell implementation or
new Windows-native support is included.
