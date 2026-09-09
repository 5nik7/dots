# 0001: Evaluate Go in an Isolated Termux Experiment

Status: Accepted (experiment only; implementation-language adoption remains undecided)
Date: 2026-09-09

## Context

The project needs evidence about native Termux startup, filesystem behavior, and executable dependencies before committing to the proposed compiled core. The existing Bash command and dotfile setup remain live. Phase 0 also contains manifest and migration decisions that are not prerequisites for this isolated experiment.

## Decision

The owner authorized a standalone experimental Go module under `experiments/go-portability/`, using the installed Go toolchain and standard library. Its executable provides help with the existing optional public logo, version output, and read-only platform diagnostics. A development harness isolates build settings, caches, and filesystem fixtures in temporary roots. No installed command or live source is replaced.

This accepts evaluating Go, not adopting it as the production core language. The experiment may proceed before unrelated manifest, module, and repository-size choices. The production command registry and metadata carrier remain undecided; the spike's private built-in table does not establish an extension protocol.

## Consequences

Go can be rejected without changing the existing setup or higher-level design. The experiment uses Go 1.27.0 as its module minimum and records the actual installed toolchain; no project-wide supported Go version is selected. The harness supports native Android/ARM64 and Linux/AMD64 Go hosts. The later authorized Linux follow-up built and executed the experiment in Ubuntu CI, with owned roots, offline verification, and telemetry isolation. Cross-compilation still supplies compilation evidence only. Native Windows execution, release distribution, controlled cold-cache measurements, and final language approval remain separate gates; Linux CI timings do not establish representative desktop-hardware performance.

## Alternatives Considered

- Starting in the proposed permanent `cmd/dots` and `internal/` layout would prematurely make the experiment the root project.
- Replacing the Bash prototype would create compatibility risk without improving portability evidence.
- Implementing manifests or transactions first would add dependencies and scope before the executable foundation is evaluated.

## Validation

See the [experiment plan and results](../../plans/phase-1-portability.md), [platform evidence](../platforms.md), and [testing instructions](../testing.md). No real-home installation, Termux package changes, proot, secret reads, or submodule initialization are part of the experiment. The bounded Linux follow-up authorizes development prerequisite provisioning in CI and feature-branch commits/pushes only; it does not change the language decision.

## Supersedes or Superseded By

None. A later accepted language/distribution decision must record its own evidence.
