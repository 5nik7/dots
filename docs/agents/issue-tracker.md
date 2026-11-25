# GitHub Issues

Matt Pocock’s engineering skills track specs and tickets in `5nik7/dots`. Run `gh repo view --json nameWithOwner` from the Dots checkout to verify the target. Pass `--repo 5nik7/dots` on issue writes.

- Publish a spec or ticket with `gh issue create --title "…" --body-file <file>`.
- Fetch a ticket with `gh issue view <number> --json number,title,body,labels,comments`. Use `gh issue list --state open --label <label>` to find work by triage role.
- Link child tickets with `gh issue create --parent <parent>`. Record dependencies with `gh issue edit <child> --add-blocked-by <blocker>`. If native relationships are unavailable, put `Part of #<parent>` or `Blocked by: #<blocker>` in the child body.
- Apply the [triage labels](triage-labels.md) with `gh issue edit`. When closing with an explanation, post it with `gh issue comment --body-file <file>` before running `gh issue close`.

**PRs as a request surface: no.**

## Wayfinding operations

Use an issue labeled `wayfinder:map` for the map. Link each decision ticket as a child and label it `wayfinder:research`, `wayfinder:prototype`, `wayfinder:grilling`, or `wayfinder:task`. If native sub-issues are unavailable, list the children in map order in the parent body.

Claim the first open, unassigned child in map order whose blockers are all closed. Assign it with `gh issue edit <number> --add-assignee @me`. To resolve it, comment with the answer, close the child, and add the decision and ticket link to the map.
