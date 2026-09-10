# 0005: Static Zsh Completion

Status: Accepted
Date: 2026-09-10

## Authorization and Contract

The owner approved stdout-only `dots completion zsh` for the permanent development executable, with Zsh first. `completion -h` and `completion --help` render registry help without inspecting roots. Missing shell, other shells, extra arguments and invalid prefix syntax return 2 with fixed stderr and empty stdout. Generation validates all selected definitions through ordinary discovery before rendering; validation/access/collision/limit and output failures return 1. Success returns script only, without logo or diagnostics. A writer failure may leave incomplete stdout.

Share an in-memory schema-1 catalog builder with `commands --json` over existing registry/external projections and `Resolver.Discover(false)`. JSON schema, sorting, availability, hidden-record inclusion and discovery semantics remain unchanged. Completion filters hidden and unavailable records only after complete validation.

## Candidates and Context

Generate canonical routes, represented aliases, intermediate route prefixes and represented global spellings. Version remains global-only. Complete one token at a time; after a completed token leaves the route tree, or after `--`, return no candidates. At a terminal route, suggest only known deeper routes. Do not infer flags, option values, positional values, filenames or shell choices from synopsis, examples or output descriptors. Prefix `--command-dir` is recognized structurally but is not suggested because it is not represented as a registry global spelling.

An external snapshot is bound to the exact ordered list of root argument strings supplied at generation, before resolver canonicalization. Compare count and each decoded shell word literally, case-sensitively, with no normalization, filesystem access, symlink resolution, expansion or sorting. Alternate spellings, trailing separators and reordered roots mismatch even if they denote the same objects. A mismatch uses built-in candidates only. The dispatcher still validates real invocation roots independently. While entering a root value, or after malformed/more-than-eight prefix pairs, return no candidates. No roots generates built-ins only.

Generated root literals are present in the script as explicit user-selected context; the public JSON catalog still exports no root paths. Safely single-quote all embedded data. Do not embed descriptive strings or interpret any metadata as code. A snapshot can become stale: explicit regeneration refreshes it, and execution revalidates the current filesystem.

## Shell and Safety Boundary

The complete script defines `_dots` and registers it for `dots` when sourced after Zsh's completion system is initialized. It does not initialize completion itself, install files or edit startup. A development executable with another invocation name may be explicitly bound with `compdef _dots <name>` in a disposable shell.

Generation, loading and tab completion never execute extensions. The function uses embedded arrays and shell builtins only, with no call to dots, Git, JSON tools or filesystem discovery. No persistent core cache is introduced and ordinary direct dispatch does not build a catalog.

## Verification and Deferred Work

Require isolated real Zsh candidate and completion-system checks on Termux and Linux, safe quoting/hostile metadata, argument/root boundaries, nonexecution and unchanged owned roots. Zsh is a check-time development prerequisite on those hosts; missing prerequisites fail without installation. CI may provision it. Native Windows checks cover generation/CLI behavior, not Zsh runtime. Preserve existing core/experiment, console and performance gates. Record actual outcomes in the Phase 2 plan.

Bash, Fish, PowerShell, richer argument metadata, installation, WSL runtime support and production release support remain deferred. This extends decision 0004 with a renderer without changing its catalog contract.
