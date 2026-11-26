# Claude Code theme

Implemented the [Claude Code template and connector](../docs/themes.md#claude-code)
for Termux, Linux, WSL and Windows. Theme publication renews the watched link
after switching the active generation. Claude Code owns theme selection.

## Verification

- WSL Bash rendered every selectable palette, including a fixture Pywal export,
  and exercised missing and custom directories, template precedence, repeat
  publication and restoration of the original file.
- Windows PowerShell 5.1 and PowerShell 7 published through the native entry
  point in a disposable home. Claude Code 2.1.332 listed **Dots** and saved
  `custom:dots` when selected. With the picker open, switching Latte to Nord
  redrew the preview with the expected Nord accent and added-line background.
- Native Linux and Termux interactive Claude Code acceptance remains pending.

The existing theme commands, palette controls and menu handle this connector.
The theme guide covers setup. Root README navigation and first commands suffice.
