---
name: dots-config-audit
description: Audit Dots configuration coverage across shared/profile files, shells, commands, popups, core libraries and templates. Use for requested discovery of missing color, icon, formatting or application controls and evidence-backed integration work.
---

# Dots Configuration Coverage Audit

Read the checkout's agent contract, [config integration](../dots-config/SKILL.md), [family owners](../../README.md#command-family-owners) and the requested goal tree. Establish whether the task authorizes an audit, saving goals, implementation or activation. Findings are evidence to review, not permission to expand the task or reopen completed work.

Run `python3 -B tools/audit_config.py --root PATH` from the owning checkout; optional repeated `--profile ID` limits profile directories. The helper emits deterministic JSON to stdout and writes nothing. It scans first-party source text, including initialized nested configuration, without executing or importing it. Its candidates and declarations do not establish whether a control is missing. Respect reported exclusions; do not initialize private/optional repositories or follow arbitrary links to broaden coverage. Review declared active application files separately through their owning adapter, without crawling the user's home or printing secrets.

Trace candidates through declarations, defaults, inheritance, the supported-control catalog, native adapters and actual consumers. Review foreground/background, icon and adjacent text styles, spacing/indentation/tab width, alignment/padding, native bar sections, options and refresh behavior. Check dynamic/default-generated values and intentional exceptions that static matching cannot establish. Separate test constants, authored artwork, literal data formats, palette algorithms and third-party defaults from useful user preferences.

Record source/line evidence, owner, current behavior, existing control or missing binding, proposed setting/type/default, activation, useful consumer checks and disposition. Summarize coverage and exclusions per source area. Keep supported controls in existing catalogs and canonical docs; an audit report is evidence/backlog, not a competing runtime registry. Preserve explicit no-change reasons and unknown coverage. Reruns reconcile findings rather than duplicating goals.

Use the owning maintenance skill and [dots-config](../dots-config/SKILL.md) for approved integrations, [presentation](../dots-cli-presentation/SKILL.md) for shared styles and data boundaries, and [menu authoring](../dots-menu-authoring/SKILL.md) for config/popup workflows. Preserve native file ownership, nullable inheritance and existing customized defaults. Verify a setting reaches its consumer before advertising it. Add or update future formatting controls only with typed validation and real consumer support.

Use [Todo](../dots-todo/SKILL.md) for requested goal tracking and [Todo planning](../dots-todo-planning/SKILL.md) for an interview or agreed linked plan. Keep extra findings outside the authorized implementation clearly identified in the report. Finish through [documentation maintenance](../dots-documentation-maintenance/SKILL.md), with isolated scanner/consumer checks and honest native evidence. Do not run a repository audit during help, completion, shell startup or ordinary config reads.
