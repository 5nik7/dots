---
name: dots-cleanup-maintenance
description: Maintain Dots cleanup rules, platform adapters, approvals, accounting and reports. Use when adding disposable file classes or platform support, not for authorizing an unrelated live cleanup.
---

# Dots Cleanup Maintenance

Read the checkout contract, [cleanup semantics](../../../docs/cleanup.md),
[safety policy](../../../docs/safety.md) and the current focused
[plan](../../../plans/cleanup.md). Inspect `lib/dots/cleanup/` and
`tools/test_cleanup.py` before extending a provider.

## Add a rule or platform

Establish the producing application's documented ownership and regeneration
behavior from current local evidence or primary documentation. Separate
download/build caches from logs, saved versions, credentials and histories.
Age or a large size alone does not make a file disposable. Keep the user's
requested scope; changing a rule does not authorize running it on live data.

Put platform paths and native helpers in a trusted Python adapter. Reuse the
shared target inventory, approval engine and receipts. Bound roots and accepted
overrides to that application's disposable location. Preserve lock/partial
files where required. Never add arbitrary path arguments, broad home globs,
runtime rule evaluation or recursive-delete fallback for a failed native tool.

Describe the group risk and consequence before approval. Sensitive or uncertain
saved data stays opt-in and cannot use `--yes`. Inventory and revalidate the
whole approved group, reject drift, links/foreign mounts/ownership, and check
process references before mutation. Native helpers need explicit cache roots,
bounded execution and an environment that cannot select another target.
Keep irreversible deletion separate from managed-file backup/undo transactions:
durable metadata is required, but payload copies defeat space reclamation.

## Preserve evidence and delivery

Credit only confirmed removals. Preserve partial subtotals, flag interrupted
native operations as uncertain, and keep filesystem free-space movement separate
from allocated/logical byte counts. Test sparse files and hardlinks; incomplete
receipts must never trigger automatic replay. Scans/help/completion/history must
not create stores, acquire deletion locks or invoke cleanup helpers.

Use owned temporary roots for scan, approval/skip/stop, changed paths, live
references, missing helpers, partial/interrupted deletion, concurrency and repeat
runs. New platforms need native evidence in addition to controller fixtures;
retain explicit unsupported behavior until an adapter is implemented.

For route changes use [command maintenance](../dots-command-maintenance/SKILL.md)
and regenerate/check `tools/generate_cleanup_commands.py`. For human views use
[CLI presentation](../dots-cli-presentation/SKILL.md); preserve data bytes and
test narrow widths. Follow [configuration](../dots-config/SKILL.md) and
[menu authoring](../dots-menu-authoring/SKILL.md) for changed integration.
Update canonical docs, the focused plan and Wiki using their owning maintenance
skills. The existing core install delivers this family; do not introduce a
service, scheduler or standalone alias without a requested use case.
