---
name: dots-codex-attention
description: Maintain Dots Codex attention events, tmux indicators and Termux alerts across panes, sessions and clients. Use for this bridge, not general Codex account or server management.
---

# Dots Codex Attention

Read the [notification guide](../../../agents/guides/codex-notifications.md) and its linked preferences and behavior reference. Use the existing event bridge and session menu; maintain one source of truth for notification policy.

Use [dots-config](../dots-config/SKILL.md) when changing configurable attention colors/icons or other settings, tracing each binding to its actual consumer. Changes to Dots command behavior require configuration and menu assessments through [command maintenance](../dots-command-maintenance/SKILL.md); a visual preference must not silently alter delivery or acknowledgement policy.

Distinguish terminal focus, a client's selected pane, and the Android tab the person can see. Stock Termux does not report DECSET 1004 focus changes: an attached client's `focused` flag is not viewing evidence. Preserve conservative delivery and explicit pane acknowledgement unless the user chooses a different policy. Neither rendering nor opening a picker acknowledges an event.

Map current client TTYs to validated live tab leaders and start times. Never infer a tab from server ancestry or workspace origin. Keep socket identity, session creation time, pane/thread identity and expiring snapshots separate; linked windows and multiple clients must not duplicate device delivery. Activity can be displayed without a thread ID, but an event cannot be associated without one.

Use the isolated suites in the guide, including multi-server topology, stale identities, full-label styling and narrow panes. Confirm the final title identity is a full UUID or the supported truncated form and resolves unambiguously to a full event ID, without printing unrelated title text. Private PTYs and Android stand-ins do not prove real device delivery or hook trust.

For authorized activation, retain source/runtime recovery and change only owned settings and workers. Do not restart a shared Codex server or bypass `/hooks`. Follow the existing documentation/wiki workflow. Use the shell integration skill for changes to startup timing.
