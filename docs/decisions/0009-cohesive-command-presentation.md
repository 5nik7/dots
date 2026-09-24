# 0009: Cohesive command presentation

**Status: Accepted, 2026-09-24; initial Bash, theme and file presentation implemented, broader adoption required as commands are added or changed.**

The owner requested polished, colorized and cohesive output throughout the planning, extending the existing theme and file views into a project-wide expectation. Treat human presentation as a required part of the interface and acceptance criteria, rather than optional command-specific decoration.

The [presentation contract](../presentation.md) owns visual roles, layouts, wording, stream behavior and verification. Reuse shared Bash helpers and equivalent renderers for other first-party implementations. Keep terminal output readable at narrow widths and without color or Nerd Font icons. Respect explicit preferences and terminal capabilities; preserve JSON, raw paths, scalar values, generated code, completion and existing plain pipeline formats. The dispatcher continues to forward arbitrary extension streams unchanged.

All plans inherit this requirement, including future managed-file and recovery workflows. Completed evidence remains historical, and paused Go work remains paused. This decision does not authorize new command semantics, general installation, or an immediate rewrite of every existing tool. New and changed human views must meet the contract within their authorized scope, with implementation and platform gaps reported honestly.
