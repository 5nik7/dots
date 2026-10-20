# 0014: Native PowerShell parity for the live CLI

**Status: Accepted implementation direction; native Windows acceptance pending, 2026-10-20.**

The owner requested the live command families, flags, output preferences, progress and pickers on Windows PowerShell 5.1 and PowerShell 7, alongside Bash on Termux, native Linux and WSL. This extends the live framework; general Go migration remains paused.

PowerShell is a thin native adapter over shared Python controllers and static metadata. Argument arrays cross native process boundaries as inert encoded data, preserving empty strings and quoting across PowerShell versions. Windows never routes first-party commands through Bash, MSYS or WSL. Files and native theme publication use the existing guarded transaction engine; no second rollback implementation is introduced. Established Bash theme/Git frontends remain while the native controllers receive acceptance.

Windows app locations are explicit adapter data with scoped overrides. Keep the existing `%LOCALAPPDATA%/dots` state root, distinct from WSL. Preserve default linking, retained backups, refusal on drift and explicit missing-capability errors. Do not elevate, silently copy or translate paths across Windows/WSL.

All future command, completion, UI and managed-file changes must cover both shell surfaces in the same change, with explicit platform exceptions and honest native evidence. [Native PowerShell](../powershell.md) owns capability details; the [parity plan](../../plans/powershell-parity.md) owns acceptance and remaining work.
