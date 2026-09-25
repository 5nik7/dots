# Source provenance

Color math and palette generation in `color/` and `internal/extraction/` are adapted from [Aether](https://github.com/omacom/aether), revision `c6c24029c39689993e72fd06c051d492875d84db`, by Bjarne Overli. The pinned source README declares “MIT - Created by Bjarne Overli”; that checkout contains no separate LICENSE file. This document preserves that declaration without inventing an upstream copyright notice.

Only color algorithms are reused. Desktop/Wails integration, caches, platform paths, downloads, hooks and app writers are excluded. Anodize supplies a bounded image decoder and deterministic grid sampler using the Go standard library (PNG, JPEG and GIF); it does not reproduce Aether's Catmull-Rom resampling. Results may therefore differ from Aether for the same image. The generation and adjustment algorithms retain their upstream behavior.
