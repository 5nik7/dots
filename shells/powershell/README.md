# Powershell Notes

Set WSLENV from pwsh

```powershell
[Environment]::SetEnvironmentVariable("WSLENV", $env:WSLENV + "USERPROFILE/p:", [System.EnvironmentVariableTarget]::User)
```

SymLink bat

```powershell
New-Item -ItemType SymbolicLink -Path "$(bat --config-dir)" -Target "C:\projects\dots\configs\bat" -ErrorAction Stop
```

Set pyenv environment variable

```powershell
[System.Environment]::SetEnvironmentVariable('PYENV',$env:USERPROFILE + "\\.pyenv\\pyenv-win\\","User")

[System.Environment]::SetEnvironmentVariable('PYENV_ROOT',$env:USERPROFILE + "\\.pyenv\\pyenv-win\\","User")

[System.Environment]::SetEnvironmentVariable('PYENV_HOME',$env:USERPROFILE + "\\.pyenv\\pyenv-win\\","User")

[System.Environment]::SetEnvironmentVariable('path', $env:USERPROFILE + "\\.pyenv\\pyenv-win\\bin;" + $env:USERPROFILE + "\\.pyenv\\pyenv-win\\shims;" + [System.Environment]::GetEnvironmentVariable('path', "User"),"User")

[System.Environment]::SetEnvironmentVariable('path', $env:DOCUMENTS + "\\PowerShell\\Scripts;" + [System.Environment]::GetEnvironmentVariable('path', "User"),"User")

```

## Completion regeneration (dots)

This repository includes a completion regeneration helper and profile support that cache shell completions under `%LOCALAPPDATA%\\dots\\ps-completions` and write logs to `%LOCALAPPDATA%\\dots\\logs\\regen.log`.

Environment variables supported:

### Prompt status integration

If you want a small status indicator for background regeneration in your prompt, set:

```powershell
$env:DOTS_REGEN_PROMPT_INTEGRATE = '1'
```

When enabled, the prompt will include `regen:idle|running|completed|failed` (simple text). If you want a more advanced prompt integration (colors, icons), tell me which prompt framework you use and I can integrate it.

Manual regeneration command (blocking):

```powershell
pwsh -NoProfile -File 'c:\Users\njen\dots\shells\powershell\regenerate_completions.ps1' -Force
```

View logs:

```powershell
Get-Content -Path "$env:LOCALAPPDATA\\dots\\logs\\regen.log" -Tail 200
```

If you'd like a scheduled task to run this regularly or only when the machine is idle, I can add a `Register-ScheduledTask` helper next.

### Lazy-loading cached completions

By default the profile registers tiny lazy wrappers for common CLI tools (for example `gh`, `bat`, `starship`) so completions are loaded on first use instead of during startup.

Environment variables that control this behavior:

- Default: `0` (lazy-only).
- Set to `1` to dot-source all cached completion files at startup.

- Set to `1` to print a short host-visible message each time a cached completion file is lazy-loaded.

Logging:

To test lazy behavior run `test_force_lazy_log.ps1` which forces lazy-only mode, sources the profile, invokes the `gh` lazy wrapper, and prints recent logs.

## Argument completer inspection

The profile provides a convenience wrapper `Get-ArgumentCompleter` that unifies:

- the native `Get-ArgumentCompleter` (when available),
- cached completers generated under `%LOCALAPPDATA%\\dots\\ps-completions` (variables like `__ghCompleterBlock`), and
- the lightweight lazy-wrapper scriptblocks (`__lazy_gh`) registered by the profile.

Usage:

```powershell
Get-ArgumentCompleter -CommandName gh
Get-ArgumentCompleter -CommandName gh -IncludeLazy   # include lazy-wrapper entries
Get-ArgumentCompleter -CommandName gh -ListAll       # return native + cached + lazy entries
```

Returned object shape (PSCustomObject):

- `CommandName` — the command name
- `ParameterName` — parameter target (if available)
- `ScriptBlock` — the scriptblock to execute for completions
- `ScriptBlockType` — textual type (usually `ScriptBlock`)
- `Source` — `native`, `dots:cached`, or `dots:lazy-wrapper`
- `HelpMessage` — optional help text when available

This makes it easy to inspect what completers are available in your session and to see whether the cached completions or lazy wrappers are registered.
