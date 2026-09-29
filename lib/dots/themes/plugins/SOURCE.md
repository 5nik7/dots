# Theme plugin provenance

Design reference: [OldJobobo/theme-hook-plugin-manager](https://github.com/OldJobobo/theme-hook-plugin-manager), locally inspected at `d244119418cc8bc02c04abc803f0c6d346bfa0ed`.

Inspected README.md, docs/plugins.md, thpm, lib/theme-env.sh, theme-set.d (including GTK, Qt6ct, Cava and Zellij), install.sh, uninstall.sh and tests/run.sh. The checkout was read-only; neither installer was executed.

No LICENSE/COPYING file or applicable source license grant was found in the inspected checkout. No substantial code or template text was copied. Dots independently implements selection, execution, semantic environment mapping, and the GTK 3/Qt6ct adapters. The source's background/foreground, cursor, selection, ANSI and RGB variable names are documented compatibility interfaces.

Format references (not vendored code):

- [GTK 3 CSS syntax](https://docs.gtk.org/gtk3/css-overview.html) and [user CSS loading](https://docs.gtk.org/gtk3/class.CssProvider.html).
- [Qt QPalette roles](https://doc.qt.io/qt-6/qpalette.html).
- [Qt6ct palette reader](https://github.com/trialuser02/qt6ct/blob/master/src/qt6ct-common/qt6ct.cpp) and [Appearance settings](https://github.com/trialuser02/qt6ct/blob/master/src/qt6ct/appearancepage.cpp).

Existing Omarchy attribution for other Dots templates is unchanged. These two new templates are independent Dots material.
