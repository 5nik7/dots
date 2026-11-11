# Dots FIGlet fonts

`dots.flf` uses five-row logo capitals for uppercase and lowercase input.
`dots-mixed.flf` adds distinct lowercase on a six-row grid with descenders.
Both preserve the revised Dots logo lettering and contain 113 glyphs: printable ASCII, the required German characters, a missing-character fallback, and `° ± × ÷ ← ↑ → ↓ ✓ ∞`.
Uppercase R, K and X use stepped box-drawing strokes with capped outer ends; R follows the user's supplied five-row design with the requested bottom-height correction.
The mixed font's lowercase k and x use smaller stepped shapes with the same capped ends; k retains its ascender and x stays within the lowercase body height.

The Termux profile manages individual links in `${PREFIX}/share/figlet`; FIGlet's other fonts remain package-owned. After linking:

```sh
figlet -C utf8 -f dots 'Dots 25°C'
figlet -C utf8 -f dots-mixed 'Hello, Dots!'
```

Before installation, use `-f ./config/figlet/dots.flf` or `-f ./config/figlet/dots-mixed.flf` from the checkout. Use `-C utf8` for Unicode input. Artwork requires a Unicode-capable FIGlet build and terminal; Termux FIGlet 2.2.5 was verified. Default layout preserves one column between glyphs.

The font files are the editable source. Preserve row padding, endmarks, required character order and code tags. Legacy `chkfont` measures bytes and reports width errors for UTF-8 artwork; validate Unicode cell widths and render with FIGlet. Full glyph rendering and wrapping at 40/80/120 columns passed on Termux. Native Linux/WSL/Windows rendering remains unverified.

See [Fonts](../../docs/fonts.md#figlet-lettering) for catalog ownership and usage.
