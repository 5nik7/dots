---
name: dots-shell-integration
description: Maintain Dots shell initialization, settings and palette refresh across native adapters. Use for dots init, startup variables or shell reload changes.
---

# Dots Shell Integration

Read [shell environment](../../../docs/shell-environment.md) and [shell initialization](../../../docs/shell-init.md).

Dots integration lives in lib/dots/shell; personal prompts/plugins stay in shells. Resolve settings from the shared schema and literal config parser, preserving explicit environment precedence and failed-reload atomicity. Avoid exporting defaults back into the override namespace. Keep scalar PATH variables separate from shell-specific maps.

Check every affected native adapter and old published snapshot fallback. Use tools/test_shell_environment.py plus focused tools/test_shell_init.py or tools/test_zsh.py cases, with owned roots and no private modules. Test repeated initialization, prompt exit status and hook duplication. Measure startup sequentially if its work changes; do not introduce scans or theme publication into startup.

Report absent PowerShell/Xonsh native verification explicitly. Do not replace launchers or install interpreters merely to make a check pass.

Maintain Bash (Termux/Linux/WSL) and native Windows PowerShell 5.1/7 together. Cover matching flags, completion, data output, progress and picker behavior; use native adapters and shared transactions. Follow [PowerShell parity](../../../docs/powershell.md), and distinguish fixture tests from native terminal/desktop evidence.
