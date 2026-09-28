# dots-repo.yazi

A local Yatline component showing the Git working tree's root folder name. For example, browsing `dots/config/yazi` displays `dots`.

After setting up Yatline in `init.lua`, load the plugin:

```lua
require("dots-repo"):setup({
  repo_color = "blue",
  repo_prefix = "", -- Literal text; include any desired trailing space.
  repo_symbol = "", -- Optional icon; include any desired trailing space.
})
```

Add this component to any Yatline header or status section:

```lua
{ type = "coloreds", custom = false, name = "repo_name" },
```

The Dots configuration places it immediately before `githead`. `theme = { repo_color = "cyan" }` can supply the color instead of the top-level option. The default has no font-dependent icon.

The name comes from `git rev-parse --show-toplevel`, not the remote URL. Nested repositories and submodules display their own root folder; linked worktrees display the worktree folder. No commit or remote is required. Outside a working tree, inside Git metadata directories, for non-local URLs, or when Git is unavailable or fails, the component is hidden.

Refreshes run asynchronously on directory events (including the initial directory load), tab, rename, bulk rename, move, trash, and delete events. Older results cannot replace a newer request. Rendering does not launch Git. External repository changes become visible on the next refresh event.

Requires Git, Yatline, and the current Yazi URL-property API. Uses Yazi's native URL parsing and process API without a shell. Native Windows behavior has not been verified.
