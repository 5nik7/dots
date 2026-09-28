# dots-symlink.yazi

A local Yatline component showing `tab_path/hovered_name  link` for symlinks and `tab_path/hovered_name` for other files. With nothing hovered, it shows only the current directory.

Load the plugin in `init.lua` after setting up Yatline:

```lua
require("dots-symlink"):setup({
  auto_fit = true,
  path_color = "blue",
  path_max_length = 0,
  path_shorten = true,
  path_rtl = true,
  name_color = "white",
  name_max_length = 0, -- 0 means unlimited.
  name_shorten = true,
  name_rtl = false,
  arrow = "  ",
  arrow_color = "darkgray",
  link_color = "cyan",
  link_max_length = 0,
  link_shorten = true,
  link_rtl = true,
})
```

Add the component to any Yatline header or status section, just like `repo_name`:

```lua
{ type = "coloreds", custom = false, name = "symlink" },
```

The Dots configuration uses this single entry in the left header section, replacing the separate `tab_path` and `hovered_name` entries. Move it to change its position.

With `auto_fit = true` (the default), the plugin measures the current header/status width on every redraw, including window resizing. It reserves space for the other components, padding, and separators, then fits into what remains. Multiple instances in one line share that remaining space equally. Load it after Yatline setup, since it wraps Yatline's header/status redraw functions. Each affected line is rendered twice: first to measure surrounding content, then with the fitted text. Rendering performs no filesystem lookups.

Long paths lose whole leading directories, keeping as many trailing directories as fit:

```text
../dir/hovered_name  ../dir/link
```

`../` is a display abbreviation for omitted directories, not a rewritten filesystem path. When space gets tighter, directory context is removed before filenames are truncated. At extremely narrow widths, even the arrow may be shortened or the component hidden. Other components can still overflow if they alone exceed the window width.

Each part has independent settings:

| Part | Color | Maximum width | Shortening | Keep end when shortened |
| --- | --- | --- | --- | --- |
| Current directory | `path_color = "blue"` | `path_max_length = 0` | `path_shorten = true` | `path_rtl = true` |
| Hovered filename | `name_color = "white"` | `name_max_length = 0` | `name_shorten = true` | `name_rtl = false` |
| Link target | `link_color = "cyan"` | `link_max_length = 0` | `link_shorten = true` | `link_rtl = true` |

Widths are non-negative integers measured in terminal columns. `0` means no fixed cap; automatic fitting still applies. The path width includes its trailing separator when a filename is present. Name and link limits exclude the arrow. Set a part's `*_shorten` to `false` to ignore its fixed cap. Automatic fitting may still shorten any part to prevent overlap; use `auto_fit = false` to use only the fixed caps. Directory removal always retains trailing directories. `*_rtl` controls which end survives the final character truncation if directory removal is insufficient.

`arrow = "  "` controls the literal separator, including spaces; use `" -> "` for ASCII or `""` to hide it. `arrow_color = "darkgray"` sets its color. An optional `theme` table can override `path_color`, `name_color`, `link_color`, and `arrow_color`.

For older configurations, `max_length` and `rtl` remain fallbacks for `link_max_length` and `link_rtl`. The old `shorten` option remains a fallback for `name_shorten` and `link_shorten`. Explicit part options take precedence; path options are independent.

The directory uses Yazi's readable path, including home abbreviation. This displays the directory itself without Yatline's appended search/filter/finder labels. The separator uses `/` on Unix and for non-local URLs, and `\` for local Windows paths; an existing trailing separator is not duplicated. Character truncation uses Yazi's [native text truncation](https://yazi-rs.github.io/docs/plugins/utils/#truncatetext-opts), and widths use its native terminal-cell measurement. Control characters in paths, filenames, and targets are replaced with spaces. Requires Yatline; native Windows behavior has not been verified.

Run the isolated layout checks from this plugin directory:

```sh
lua test.lua
```

The standalone test adapter approximates terminal widths and simulates Windows paths; it does not establish native rendering or Windows support.

Native Termux verification with Yazi 26.9.1 also passed the layout assertions using real text APIs across 0–200 column budgets, including Unicode, plus an isolated installed-Yatline header fixture across widths 24–160. These are fixture redraw checks, not an owner-run interactive session.
