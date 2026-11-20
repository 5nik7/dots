package anodize

import (
	"image"
	stdcolor "image/color"
	"math"
	"sort"

	"github.com/5nik7/dots/anodize/color"
)

func (m *PatinaMapping) prepareTones(names map[string]string) {
	m.dark, m.light, m.accent = m.swatches[0].lab, m.swatches[0].lab, m.swatches[0].lab
	for _, s := range m.swatches {
		if s.lab.L < m.dark.L {
			m.dark = s.lab
		}
		if s.lab.L > m.light.L {
			m.light = s.lab
		}
		if math.Hypot(s.lab.A, s.lab.B) > math.Hypot(m.accent.A, m.accent.B) {
			m.accent = s.lab
		}
	}
	named := func(key string, fallback color.OKLab) color.OKLab {
		if v := names[key]; Hex(v) {
			return color.SRGBToOKLab(color.HexToRGB(v))
		}
		return fallback
	}
	m.dark, m.light = named("background", m.dark), named("foreground", m.light)
	if m.dark.L > m.light.L {
		m.dark, m.light = m.light, m.dark
	}
	m.accent = named("accent", m.accent)
	// Crossfade neighboring families on the hue wheel, including its seam.
	// Keep a common midtone lightness so a smooth sky cannot develop tone bands.
	neutral := mixLab(m.dark, m.light, .55)
	for h := range 360 {
		weight := 0.0
		var mid color.OKLab
		for _, s := range m.swatches {
			c := color.OKLabToOKLCH(s.lab)
			if c.C < .025 {
				continue
			}
			gap := arc(c.H, float64(h))
			w := math.Exp(-gap/8) * (.5 + math.Min(1, c.C/.12))
			mid.A += w * s.lab.A
			mid.B += w * s.lab.B
			weight += w
		}
		m.family[h] = neutral
		if weight > 0 {
			m.family[h] = color.OKLab{L: neutral.L, A: mid.A / weight, B: mid.B / weight}
		}
	}
	m.family[360] = m.family[0]
}

func (m *PatinaMapping) middle(c color.OKLCH) color.OKLab {
	h := min(int(c.H), 359)
	mid := mixLab(m.family[h], m.family[h+1], c.H-float64(h))
	return mixLab(mixLab(m.dark, m.light, .50), mid, smooth(.012, .065, c.C))
}

func (m *PatinaMapping) toned(l float64, mid color.OKLab) color.OKLab {
	if l < .56 {
		return mixLab(m.dark, mid, l/.56)
	}
	return mixLab(mid, m.light, (l-.56)/.44)
}

var bayer4 = [4][4]int{{0, 8, 2, 10}, {12, 4, 14, 6}, {3, 11, 1, 9}, {15, 7, 13, 5}}

func (m *PatinaMapping) paletteBlend(lab color.OKLab) color.OKLab {
	// Smoothly blend neighboring swatches in perceptual space.
	var sum color.OKLab
	total := 0.0
	for _, s := range m.swatches {
		dl, da, db := lab.L-s.lab.L, lab.A-s.lab.A, lab.B-s.lab.B
		d := .002 + dl*dl + 2*(da*da+db*db)
		w := 1 / (d * d)
		total += w
		sum.L += w * s.lab.L
		sum.A += w * s.lab.A
		sum.B += w * s.lab.B
	}
	return color.OKLab{L: sum.L / total, A: sum.A / total, B: sum.B / total}
}

// Alloy keeps palette-blend lightness. Chromatic colors interpolate in polar
// coordinates, while low-chroma colors fade into a Cartesian tint because
// their hue angles become unstable near gray.
func alloyTone(palette, harmonized color.OKLab, sourceChroma float64) color.OKLab {
	const share = 0.25
	harmonized.L = palette.L
	neutral := mixLab(palette, harmonized, share)
	p, h := color.OKLabToOKLCH(palette), color.OKLabToOKLCH(harmonized)
	chromatic := smooth(.010, .050, min(sourceChroma, p.C, h.C))
	if chromatic == 0 {
		return neutral
	}
	delta := math.Mod(h.H-p.H+540, 360) - 180
	tint := color.OKLCHToOKLab(color.OKLCH{L: palette.L, C: mix(p.C, h.C, share), H: p.H + share*delta})
	return mixLab(neutral, tint, chromatic)
}

func (m *PatinaMapping) stylize(lab color.OKLab, x, y int, edge float64) color.OKLab {
	l := lab.L
	hue := color.OKLabToOKLCH(lab)
	mid := m.middle(hue)
	switch m.options.Style {
	case "color-transfer":
		best := math.Inf(1)
		target := mid
		for _, p := range m.transfer {
			if d := color.OKLabDistance(lab, p.source); d < best {
				best = d
				target = p.target
				target.L = max(0, min(1, target.L+(l-p.source.L)*.72))
			}
		}
		return target
	case "split-tone":
		return mixLab(mixLab(m.dark, m.accent, .30), mixLab(m.light, m.family[55], .24), smooth(.04, .96, l))
	case "muted":
		return mixLab(m.toned(l, mid), mixLab(m.dark, m.light, l), .62)
	case "vivid":
		t := m.toned(smooth(.04, .96, l), mid)
		t.A *= 1.40
		t.B *= 1.40
		return t
	case "pastel":
		return mixLab(m.toned(l, mid), mixLab(m.light, color.OKLab{L: .98}, .48), .44)
	case "night":
		return mixLab(m.dark, m.toned(l*l, mid), .75)
	case "accent":
		a := color.OKLabToOKLCH(m.accent)
		return mixLab(mixLab(m.dark, m.light, l), m.toned(l, m.accent), smooth(.018, .08, hue.C)*(1-smooth(24, 78, arc(a.H, hue.H))))
	case "posterize":
		return m.toned(math.Round(l*5)/5, mid)
	case "dither":
		level := math.Floor(l*4 + (float64(bayer4[y%4][x%4])+.5)/16)
		return m.toned(level/4, mid)
	case "ink":
		paper := mixLab(m.light, mid, .12)
		wash := mixLab(paper, m.dark, .5*(1-smooth(.20, .68, l)))
		return mixLab(wash, m.dark, smooth(.035, .22, edge))
	}
	return m.toned(l, mid)
}

type transferPair struct{ source, target color.OKLab }
type colorGroup struct {
	key, count int
	r, g, b    float64
}

// TransferGroups takes the same small source sample for the wallpaper, chooser,
// and comparison sheet. Transparent pixels do not claim a palette color.
func TransferGroups(src image.Image, width, height int) []color.OKLab {
	sample := sampleRaster(src, width, height, 64, 32)
	bins := map[int]*colorGroup{}
	for y := range sample.Bounds().Dy() {
		for x := range sample.Bounds().Dx() {
			p := stdcolor.NRGBAModel.Convert(sample.At(x, y)).(stdcolor.NRGBA)
			if p.A == 0 {
				continue
			}
			key := int(p.R>>5)<<6 | int(p.G>>5)<<3 | int(p.B>>5)
			g := bins[key]
			if g == nil {
				g = &colorGroup{key: key}
				bins[key] = g
			}
			g.count++
			g.r += float64(p.R)
			g.g += float64(p.G)
			g.b += float64(p.B)
		}
	}
	groups := make([]*colorGroup, 0, len(bins))
	for _, g := range bins {
		groups = append(groups, g)
	}
	sort.Slice(groups, func(i, j int) bool {
		if groups[i].count == groups[j].count {
			return groups[i].key < groups[j].key
		}
		return groups[i].count > groups[j].count
	})
	var result []color.OKLab
	for _, g := range groups {
		n := float64(g.count)
		lab := color.SRGBToOKLab(color.RGB{R: g.r / n, G: g.g / n, B: g.b / n})
		distinct := true
		for _, previous := range result {
			if color.OKLabDistance(lab, previous) < .095 {
				distinct = false
				break
			}
		}
		if distinct {
			result = append(result, lab)
			if len(result) == 12 {
				break
			}
		}
	}
	return result
}

func (m *PatinaMapping) SetTransferGroups(groups []color.OKLab) {
	m.transfer = nil
	remaining := append([]swatch(nil), m.swatches...)
	for _, lab := range groups {
		best := 0
		dist := math.Inf(1)
		for i, s := range remaining {
			d := color.OKLabDistance(lab, s.lab)
			if d < dist {
				best, dist = i, d
			}
		}
		m.transfer = append(m.transfer, transferPair{lab, remaining[best].lab})
		remaining = append(remaining[:best], remaining[best+1:]...)
		if len(remaining) == 0 {
			break
		}
	}
}
