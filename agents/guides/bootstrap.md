# Bootstrap Work Guide

Read this guide before changing a remote installer, first-run workflow, release download, executable installation, repository clone, profile selection, package bootstrap, or private-source setup.

## Purpose

Bootstrap gets from a minimally prepared platform to a verified `dots` installation. It must stay small enough to inspect and must hand control to versioned, tested core behavior as early as possible.

## Required Properties

- Provide a POSIX-shell entry point for Termux, Linux, and WSL.
- Provide a PowerShell entry point for native Windows.
- Detect platform and architecture before selecting an artifact.
- Download over HTTPS and verify an expected checksum before execution or installation.
- Support an explicitly pinned version as well as a documented moving channel.
- Install into a user-owned location unless the user explicitly selects a system-wide mode.
- Clone the public repository without recursively initializing submodules.
- Run diagnostics and a plan before applying managed machine state.
- Be idempotent and recover clearly from partial prior runs.
- Keep CLI installation, repository cloning, package installation, and dotfile apply as distinct observable stages.

## Safety

- Do not silently overwrite an existing `dots` executable or repository with unrelated ownership.
- Do not force-reset, clean, stash, or discard an existing repository.
- Do not request GitHub credentials during the public bootstrap stage.
- Do not fetch `secrets`, platform repositories, large assets, or other optional sources until the selected profile needs them and authentication has been checked.
- Do not advertise a pipe-to-shell command until the hosted content, checksum flow, version policy, and failure behavior are implemented and tested.
- An unattended `--apply` mode must still emit or persist the resolved plan and transaction record.

## Termux

The first portability spike must prove:

- Platform and architecture detection on the supported Android device architecture.
- The proposed core binary starts without an undeclared runtime dependency.
- Repository, config, state, and cache paths resolve correctly under Termux.
- File and directory link behavior matches the planner's capability report.
- A fresh environment can obtain the minimum required download and Git tooling.

Do not assume `sudo`, systemd, `/usr/local/bin`, GNU userland, or a Linux distribution package manager in Termux.

## Windows

- Use PowerShell-native download, checksum, path, and error handling.
- Do not assume Developer Mode, elevation, Git Bash, WSL, or Unix utilities.
- Capability-test symbolic links, junctions, and hardlinks before selecting a strategy.
- Never silently fall back to copying when a requested link cannot be created.

## Verification

Test bootstrap in disposable environments with:

- No previous installation.
- An identical existing installation.
- An older managed installation.
- An unrelated executable at the destination.
- An existing clean repository.
- An existing dirty repository.
- Network interruption and checksum mismatch.
- Private sources unavailable.
- Paths containing spaces.

Update `docs/platforms.md`, `docs/safety.md`, `README.md`, and the applicable plan whenever bootstrap capabilities change.

