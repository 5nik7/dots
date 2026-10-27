# Anodize terminal assets

Original PNGs copied without modification from the owner-supplied `anodize-logo-pack` (brand version 1.0, 2026-09-25, concept 02). The separate `anodize-favicons` pack contains the same icon family; desktop/web wrappers and opaque app tiles are not needed for terminal output.

The [authoritative logo contract](../../../../docs/anodize.md#terminal-logo) defines the owner's exact six-row UTF-8 `logo.txt` (LOGO1) and `horizontal.txt` (LOGO2) as the only default human branding. Python and Bash retain an exact embedded LOGO1 for missing/invalid assets; regression checks compare it to `logo.txt`. Preserve all braille cells and spacing. `stacked.txt`, numbered `logo-<width>.txt` files and original PNGs remain available only through explicit alternative choices. `wordmark.txt` and `logo.png` remain source assets, not additional default layouts. Asset readers reject controls, tabs, malformed UTF-8 and unsupported characters. No runtime conversion is needed for the text logos. Keep these source assets uncolored; renderers add the bottom-left hint through midpoint info to top-right accent gradient at display time, independently for symbol and wordmark.

| Bundled file | Original pack path | SHA-256 |
| --- | --- | --- |
| `icon-color.png` | `png/icon/color/anodize-icon-color-256.png` | `852fa1b142b80741bf82d16e9a43483ecef1a2c4ed7d65c54e0991f20f0b7144` |
| `icon-white.png` | `png/icon/white/anodize-icon-white-256.png` | `c8c404f555965366096d5049c736741647a066360e916d596bab52a79a5ef851` |
| `stacked-color-white.png` | `png/stacked/color-white/anodize-stacked-color-white-512.png` | `ef5bdab3f05c0c9fbb07007b81a53ef0d2fa5e58dcf1e983629935e3feeea74b` |
| `stacked-color-black.png` | `png/stacked/color-black/anodize-stacked-color-black-512.png` | `c5454e6ba3e6bf76bf5a1bf907029c3967035f7b8f708f14f1b47fc030c65c18` |
| `stacked-white.png` | `png/stacked/white/anodize-stacked-white-512.png` | `6a45a800fd81fd484ab3ea21b9e55b7aecaff800aa989f257434aad2658228c2` |
| `horizontal-color-white.png` | `png/horizontal/color-white/anodize-horizontal-color-white-512.png` | `d1f09f4de8889ab08e23ee31be86068a11b792e474c7b288b2014e88f67ed620` |
| `horizontal-color-black.png` | `png/horizontal/color-black/anodize-horizontal-color-black-512.png` | `e01ab627c2c880935c2e44bbed59684f74e327204da7f511c3f477f93218c7dc` |
| `horizontal-white.png` | `png/horizontal/white/anodize-horizontal-white-512.png` | `a0ac5ca53c9a762cd16a709c4b9985fb5585fd8b74a9a97823014c99b41f59e5` |
