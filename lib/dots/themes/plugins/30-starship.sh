#!/usr/bin/env bash
# Palette-only adapter; no prompt or module commands are executed.
exec "$DOTS_THEME_PLUGIN_PYTHON" -B "$DOTS_THEME_PLUGIN_MANAGER" __app starship
