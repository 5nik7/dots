---
name: dots-wiki-maintenance
description: Maintain the Dots wiki export, sidebar, page mappings and associated Git workflow. Use for wiki changes or refreshing wiki output after source documentation changes.
---

# Dots Wiki Maintenance

Read [the wiki guide](../../../agents/guides/wiki.md) and [wiki commands](../../../docs/wiki.md). Resolve the source checkout and wiki with `dots wiki path --source` and `dots wiki path`; inspect both Git states. The manifest owns page IDs, sections and source mappings. Edit canonical source documents or command metadata, never generated pages directly.

Keep navigation shallow, task-oriented and complete. Preview `dots wiki build --dry-run`, build, then run `dots wiki check`. Reconcile edited generated content into its source before rebuilding; preserve unknown files and existing work. Use `check --source-only` when no wiki checkout exists and report the missing export instead of silently acquiring it.

For publication explicitly requested by the user, preview `dots git wiki publish` or the requested combined Git scope. The default is staged-only; never quietly add --all. Source publication must precede dependent wiki publication, and selected generated content must match the source tree being published. Keep branch/upstream and ownership checks, report partial completion, and do not describe local generation as a live wiki update. Creating or updating documentation does not itself authorize commits or pushes.

Use the isolated suites named in the guide for changes to generation, links, navigation, transaction safety or Git integration. Validate readable narrow-terminal output and exact raw/JSON output separately from GitHub rendering.
