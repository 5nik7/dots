# Fast Syntax Highlighting

This tracked directory is the source for the `${CONFIG}/fsh` catalog link.
Checkout setup creates `dots.ini` here as a machine-local link to the published
Dots theme. The generated link is ignored; colors come from
[`fsh.ini.tpl`](../../default/themed/fsh.ini.tpl).

The default template leaves path separators unstyled so `/` inherits the surrounding file or directory style, including blue and bold for directories.

Run `dots init --setup` to install the links or repair setup, and
`dots theme refresh` to rebuild missing theme outputs. Neither action requires
Fast Syntax Highlighting to be installed before rendering the theme.
