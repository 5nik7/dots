# Leaf external syntax build

Dots' Leaf theme uses an external Syntect `.tmTheme` file. Upstream Leaf 1.28.2 accepts only bundled syntax names and falls back to its base syntax theme for file paths. The local `1.28.2+dots.1` build adds explicit file loading. It is a local patch, not an upstream release.

The [source patch](../tools/patches/leaf-1.28.2-dots-syntax.patch) applies to RivoLink/leaf tag `1.28.2`, peeled commit `140e55858c98df50ba52fc4ab7bad277a31ab73f`. It includes the dependency lockfile, implementation, documentation and Rust tests. Keep Leaf in a separate checkout, outside Dots. In a clean checkout of that commit, apply the patch and use a native Rust toolchain:

```sh
git apply /absolute/path/to/dots/tools/patches/leaf-1.28.2-dots-syntax.patch
cargo test --locked --bin leaf
cargo clippy --locked --all-targets --all-features -- -D warnings
cargo build --locked --release
```

For test isolation, set HOME/USERPROFILE, XDG_CONFIG_HOME, XDG_STATE_HOME, XDG_CACHE_HOME, XDG_DATA_HOME, APPDATA and LOCALAPPDATA to disposable roots. On Unix, also set CARGO_HOME and CARGO_TARGET_DIR to owned build roots and GIT_CONFIG_GLOBAL to `/dev/null`. On Windows use native paths and PowerShell environment assignments. Tests must not read or write the developer's real configuration. Rust prerequisites are those of the upstream project; this patch enables Syntect's `plist-load` feature.

An explicit external syntax selection is loaded once during startup before either inline or TUI rendering. File paths are recognized by `.tmTheme` (case insensitive) or path separators. Relative paths resolve beside the selected external theme TOML, including its lexical symlink location; embedded named themes resolve beside Leaf's config. Absolute paths are supported. A unique internal ThemeSet key keeps existing built-ins intact and preserves the selected syntax across picker cancel, resize and document reload. Missing, unreadable or malformed selected files fail with their path instead of silently falling back. Unselected custom files are not read. Built-in syntax names retain their existing behavior.

Use the [Leaf setup](themes.md#leaf) to publish both files before selecting `theme = "themes/dots.toml"`. Restart Leaf after publication to read changed colors. Leaf's document watcher does not watch theme files.

Replacing an installed executable is a separate, explicit action. Verify the candidate first with `LEAF_TEST_BIN=/absolute/path/to/build/leaf python3 -B tools/test_leaf_theme.py -v`. Retain the original executable and config in a guarded Dots file transaction before replacement; the transaction's backup and drift-checked inverse provide recovery. An upstream reinstall or Leaf self-update may replace the custom executable and remove external syntax support. Reapply/revalidate the patch for a later upstream version rather than assuming compatibility.

Native Windows PowerShell 5.1/7, Linux and WSL compilation, publication and interactive rendering remain pending; Termux verification is recorded in the [focused plan](../plans/leaf-theme.md).
