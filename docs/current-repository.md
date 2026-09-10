# Current Repository Baseline

**Status: Observed baseline for migration planning**

This inventory was captured from public `main` commit `d2eeef9c204efe9f24dbe7f907072d7a40e58e8e` on 2026-09-09. It documents constraints; it is not authorization to remove or reorganize files.

## Top-Level Shape

The current repository includes:

```text
bin/
configs/
fonts/
functions/
local/
ruby/
scripts/
shells/
themes/
walls/
androidots     submodule
secrets        submodule
windots        submodule
dot.env
README.md
```

There is also a Catppuccin PowerShell submodule under `shells/powershell/Modules/catppuccin`.

## Tracked Tree Size

Approximate current checked-in blob sizes measured from the commit tree:

| Area | Files | Size |
| --- | ---: | ---: |
| `walls/` | 62 | 161.7 MiB |
| `shells/` | 378 | 57.1 MiB |
| `fonts/` | 16 | 39.3 MiB |
| `configs/` | 692 | 19.7 MiB |
| `local/` | 55 | 0.3 MiB |
| `scripts/` | 71 | 0.3 MiB |
| `bin/` | 34 | 0.2 MiB |
| Remaining tracked blobs | — | Less than 0.5 MiB |
| Total current tree | — | Approximately 278.8 MiB |

The largest groups include wallpapers, font files, PowerShell DLLs, and demo media. A shallow checkout therefore still transfers a substantial current payload.

## Existing Command and Environment

`bin/dots` currently provides a prototype help display and a repository-directory option. The owner's commits through `c1be6eb` added the public `logo.txt`, dynamic optional logo loading, a `help` spelling, and repaired error output. The Phase 1 change preserves that command, logo, and shell configuration. It does not implement the command discovery, specification, planning, or transaction model described in the new design docs.

The additive `experiments/go-portability/` module now contains a separate Go executable with help, version, and read-only diagnostics, plus isolated filesystem tests and a development harness. The `.github/workflows/phase-1-linux.yml` workflow and CI evidence collector provide bounded native Linux and Windows validation jobs. Both jobs have executed successfully with retained source, binary, test, dependency, and timing evidence. The shared verifier now also has a bounded distribution mode and archive failure regressions; artifacts remain outside the checkout. They own no live dotfiles. Build artifacts and caches stay outside the checkout. See the [focused plan](../plans/phase-1-portability.md) for evidence. The historical inventory and size measurements above have not been recomputed or replaced by this addition.

`dot.env` currently:

- Uses Zsh-specific associative arrays.
- Defaults the repository to `$HOME/dots`.
- Exposes repository subdirectories through environment variables.
- Adds several repository directories to `PATH` and `fpath` through surrounding shell helpers.

This behavior is useful migration input but should not become the portable core interface directly. Future environment generation should produce shell-specific cached output from portable data.

## Submodules

The repository declares:

| Path | Purpose inferred from name/source | Anonymous bootstrap observation |
| --- | --- | --- |
| `androidots` | Android/Termux-specific personal repository | Could not be initialized anonymously during inspection |
| `secrets` | Private or sensitive material | Could not be initialized anonymously during inspection |
| `windots` | Windows-specific personal repository | Optional platform source; not required for public base inspection |
| `shells/powershell/Modules/catppuccin` | Third-party PowerShell module | Public third-party dependency |

Bootstrap must clone the main repository without `--recurse-submodules`. Selected sources can be authenticated and synchronized later.

## Generated and Vendored Material

The tracked tree includes generated/cache-style files, compiled libraries, media demonstrations, fonts, and large assets. A focused audit should classify each as:

- Source configuration that belongs in the core repository.
- Generated state that should be ignored.
- Third-party dependency better expressed by a package/source manifest.
- Optional asset better fetched lazily.
- Historical material to archive.
- Required binary that needs provenance, checksum, update, and licensing documentation.

Do not delete these categories as general cleanup. Each migration should identify current consumers and a recovery path.

## Migration Consequences

- Preserve the existing layout while the new core is built beside it.
- Migrate one module at a time and verify equivalent behavior.
- Start with a small Termux set rather than all 1,300-plus entries.
- Keep the minimum bootstrap independent of private submodules.
- Move optional assets out of the minimum checkout path before calling bootstrap fast.
- Decide whether long-term size reduction uses a clean repository, optional source repositories, partial checkout, or an explicitly approved history operation.
- Keep compatibility wrappers only where an existing command is actively used.

Update this document when a migration materially changes the baseline. Preserve prior measurements in a decision or completed plan when they are needed to explain history.
