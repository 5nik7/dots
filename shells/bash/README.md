# Bash configuration

Bash uses the [shared interactive configuration](../../docs/shared-shells.md): shared functions/aliases, portable public settings, Readline vi mode, native completion, Starship with a fallback prompt, FZF bindings and automatic palette/Gum refresh.

The startup wrapper resolves file and parent-directory symlinks and loads its adjacent native loader. Checkout-derived paths replace inherited Dots path values. Keep the complete checkout layout when relocating it. `~/.bash_aliases` loads after shared aliases; set personal overrides there. `rl` reloads Bash even when `$SHELL` names Zsh. Zsh-specific private modules are not loaded.

Optional integrations activate once after successful generation and can retry on reload. Start a fresh shell after changing activation code for an already active tool. Zsh syntax highlighting, autosuggestions and FZF-tab remain Zsh-only; Bash uses installed native completion and FZF bindings without a new editor plugin.

See [initialization](../../docs/shell-init.md), [shared commands](../../docs/shared-shells.md#commands-and-compatibility), and [isolated verification](../../docs/testing.md#shell-initialization). No live startup or real user state is used by the tests.
