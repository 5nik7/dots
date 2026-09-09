# Desired-State Specification

**Status: Draft**

This document defines the proposed declarative model for repository modules, platforms, profiles, hosts, and local machine selection. TOML is the current recommendation but is not final until the parser and Termux core direction are accepted.

## Goals

The specification should:

- Keep ordinary dotfile layout intuitive.
- Compose universal files with platform-, profile-, and host-specific resources.
- Make destination ownership and overrides explainable.
- Support links by default and explicit copies when required.
- Express dependencies, capability requirements, packages, and limited hooks.
- Resolve deterministically into a platform-neutral desired state.
- Carry schema versions from the beginning.
- Avoid requiring templates for differences that modules can express cleanly.

## Configuration Layers

| Layer | Purpose | Versioned in repository |
| --- | --- | --- |
| Built-in defaults | Stable fallback behavior | Core source |
| Repository `dots.toml` | Repository identity, supported schema, module roots, and defaults | Yes |
| Platform selection | Automatically detected execution context and capabilities | Runtime evidence |
| Base/profile files | Selected module composition | Yes |
| Host file | Optional device-specific composition | Usually yes when non-secret |
| Machine config | Repository path, selected profile/host, and local policy | No |
| CLI overrides | One-invocation test or deliberate override | No |

Proposed precedence from general to specific:

```text
built-in defaults
→ repository configuration
→ base profile
→ detected platform contribution
→ selected profile
→ selected host
→ machine-local override
→ command-line override
```

Precedence decides which policy value applies. It does not silently resolve two resources claiming the same destination; resource collision rules still apply.

## Terminology

- **Platform**: detected execution context such as `termux`, `linux`, `wsl`, or `windows`.
- **Profile**: user-selected collection such as `personal`, `minimal`, or `work`.
- **Host**: optional device-specific layer such as `phone` or `desktop`.
- **Module**: cohesive versioned desired-state unit such as `git`, `zsh`, `scripts`, or `termux`.
- **Resource**: one managed file, directory, package, environment entry, generated file, or controlled hook.
- **Resolved specification**: fully composed desired state with no unresolved variables or ambiguous destinations.

## Proposed Repository Configuration

Conceptual `dots.toml`:

```toml
schema = 1
name = "njen-dots"

[requirements]
dots = ">=0.1.0"

[layout]
modules = "modules"
profiles = "profiles"
commands = "commands"
```

Version requirements and field syntax remain draft. Unknown schema versions must fail with an actionable error rather than being interpreted partially.

## Module Layout

Convention should handle the common case:

```text
modules/zsh/
├── module.toml
└── home/
    ├── .zshrc
    └── .config/
        └── zsh/
            └── options.zsh
```

Files under `home/` map relative to the platform adapter's user-home root. Walking should produce file-level resources by default. Empty directories require explicit representation because Git does not track them.

Conceptual `module.toml`:

```toml
schema = 1
name = "zsh"
description = "Shared Zsh configuration"
platforms = ["termux", "linux", "wsl"]
depends = ["shell-common", "scripts"]
strategy = "link"
```

The manifest may add exceptional mappings:

```toml
[[files]]
id = "zsh-history-config"
source = "files/history.zsh"
target = "${CONFIG}/zsh/history.zsh"
strategy = "link"
```

The exact token syntax is draft. Variables are resolved by the core, not through arbitrary shell evaluation.

## Resource Identity

Every resolved resource needs a stable identifier and provenance.

Recommended identity properties:

- Module name plus resource-local ID.
- Canonical normalized destination.
- Source repository and relative path when file-backed.
- Layer that selected or replaced it.
- Required platform capabilities.

Renaming a resource ID may affect history and adoption tracking even if its destination remains unchanged. Treat identifiers as part of the state schema once implemented.

## File Strategies

| Strategy | Meaning | Initial priority |
| --- | --- | --- |
| `link` | Create a symbolic link to the repository source | Default and Termux MVP |
| `copy` | Copy content and track the applied checksum | Termux MVP |
| `directory-link` | Link a complete owned directory | Explicit only |
| `template` | Render a generated target from data | Later |
| `hardlink` | Link a file where platform and volume permit | Later or Windows policy |
| `junction` | Native Windows directory junction | Later or Windows policy |

A requested strategy that is unavailable becomes a blocked plan unless the manifest or machine policy explicitly names an acceptable fallback. Fallback behavior must appear in the plan.

## Destination Variables

The core should expose a small normalized set rather than arbitrary environment interpolation:

- `${HOME}`
- `${CONFIG}`
- `${DATA}`
- `${STATE}`
- `${CACHE}`
- `${TEMP}`
- `${REPO}` for source-side references only unless specifically permitted
- Platform-specific known folders through explicit normalized names when needed

Environment-variable access should require an allowlist or explicit declaration. Secrets must not become general interpolation variables that leak into resolved-spec output.

All destinations must be normalized and checked against permitted ownership roots after expansion. A relative segment such as `..` must not escape an allowed root accidentally.

## Profiles

Conceptual base profile:

```toml
schema = 1
name = "base"
modules = ["git", "shell-common", "scripts"]
```

Conceptual personal profile:

```toml
schema = 1
name = "personal"
extends = ["base"]
modules = ["zsh", "themes"]
```

Conceptual platform contribution:

```toml
schema = 1
platform = "termux"
modules = ["termux", "termux-packages"]
```

Profiles may extend other profiles only if resolution remains acyclic and deterministic. Duplicate module selection is deduplicated by module identity, not by ignoring conflicting content.

## Hosts and Local Overrides

A host layer should be selected explicitly or initialized by bootstrap. Android hostnames and corporate Windows naming may be unstable or unsuitable as configuration identifiers, so detected hostname should be a suggestion rather than an unquestioned key.

Machine-local configuration may choose a profile, host, repository path, link policy, and optional source enablement. It must not become an undocumented second manifest capable of bypassing repository validation.

## Collisions and Replacement

Two resources resolving to the same canonical destination are a conflict unless one explicitly replaces the other by stable resource ID.

Replacement requirements:

- Name the resource being replaced.
- Preserve provenance in the resolved specification.
- Be valid only when both resources are selected.
- Reject ambiguous multiple replacements.
- Appear clearly in human and structured plans.

Order alone is not sufficient authorization to overwrite a resource declaration.

## Packages

Modules may declare normalized package requirements separately from platform-manager names.

Conceptual form:

```toml
[[packages]]
id = "ripgrep"
required = true

[packages.names]
pkg = "ripgrep"
apt = "ripgrep"
pacman = "ripgrep"
winget = "BurntSushi.ripgrep.MSVC"
```

The final representation should avoid forcing every module to repeat common mappings. A central catalog may own normalized-to-manager names while modules select normalized IDs.

Package presence, installation, explicit upgrades, and removal are separate operations. See `safety.md`.

## Environment and Shell Integration

Environment declarations should be data, not shell fragments, when practical. The core may generate shell-specific cached output for Bash, Zsh, Fish, and PowerShell.

Requirements:

- Correct quoting for the selected shell.
- No secret values in ordinary display or logs.
- Stable generated-file location.
- Regeneration after relevant configuration changes.
- No expensive profile resolution during every shell startup.

## Hooks

Hooks are an escape hatch and are not automatically transactional.

A hook must declare:

- Stage and purpose.
- Platform/capability requirements.
- Whether it is read-only or mutating.
- Whether it supports plan, apply, and undo protocols.
- Whether explicit opt-in is required.
- Which outputs may contain sensitive data.

The initial MVP should avoid general arbitrary hooks until built-in file operations are proven. A hook that cannot describe or reverse its effects must be labeled partially reversible in the plan.

## Optional and Private Sources

Optional sources may eventually provide private dotfiles, secrets, large assets, or independent third-party content. They should be selected by modules/profiles and fetched lazily rather than initialized recursively during the main clone.

The source model needs:

- Stable source ID.
- URL without embedded credentials.
- Revision or lock information.
- Public/private and optional classification.
- Destination outside conflicting module paths.
- Authentication preflight.
- Offline behavior.
- Update and dirty-worktree policy.

The existing Git submodules may remain during migration. Replacing them requires a separate approved plan.

## Resolved Specification

`dots spec` should eventually expose the exact desired state used by planning, including:

- Schema and CLI versions.
- Repository identity and revision.
- Platform detection evidence and capabilities.
- Selected profile and host.
- Module dependency order.
- Each resource's source, destination, strategy, provenance, and requirements.
- Replacements, skipped optional resources, warnings, and conflicts.
- Secret values redacted or represented only by opaque references.

The structured representation must be versioned before it is treated as an automation API.

## Open Decisions

- Confirm Go after the Termux portability spike.
- Confirm TOML and choose the parser.
- Finalize resource ID syntax.
- Finalize normalized path tokens and allowed roots.
- Decide whether platform contributions are files under `platforms/` or platform-scoped modules selected by the resolver.
- Decide metadata and manifest schema versioning policy.
- Decide optional-source locking and update behavior.
- Decide the minimum safe hook protocol.

Record each material conclusion in `docs/decisions/` and update this document rather than leaving the answer only in a plan or conversation.

