// The normal recipe uses actual sampled coverage. Other recipes retain their
// original, chroma-boosted median-cut input.
package anodize

import (
	"math"
	"strings"

	"github.com/5nik7/dots/anodize/color"
)

type colorMass struct {
	sum   color.OKLab
	count int
}

func (m *colorMass) add(other colorMass) {
	m.count += other.count
	m.sum.L += other.sum.L
	m.sum.A += other.sum.A
	m.sum.B += other.sum.B
}

func (m colorMass) tone() color.OKLCH {
	n := float64(max(1, m.count))
	return color.OKLabToOKLCH(color.OKLab{L: m.sum.L / n, A: m.sum.A / n, B: m.sum.B / n})
}

var namedHues = [...]struct {
	name        string
	hue, radius float64
}{
	{"red", 23, 22}, {"green", 147, 30}, {"yellow", 96, 18},
	{"blue", 258, 28}, {"magenta", 326, 27}, {"cyan", 200, 23},
	{"orange", 58, 18}, {"brown", 55, 23},
}

func hueGap(a, b float64) float64 { return math.Abs(math.Mod(a-b+540, 360) - 180) }

func normalHex(t color.OKLCH) string {
	rgb := color.GamutMappedRGB(color.OKLCHToOKLab(t))
	return strings.ToLower(color.RGBToHex(math.Round(rgb.R), math.Round(rgb.G), math.Round(rgb.B)))
}

// Move just far enough along the same hue to give readable text or background.
func readableTone(t color.OKLCH, against string, ratio float64, lighter bool) string {
	step := -.008
	if lighter {
		step = .008
	}
	for {
		hex := normalHex(t)
		if color.ContrastRatio(hex, against) >= ratio || (lighter && t.L >= 1) || (!lighter && t.L <= 0) {
			return hex
		}
		t.L = max(0, min(1, t.L+step))
	}
}

const hueSectors = 24

type normalSamples struct {
	field    [hueSectors + 1][16]colorMass
	families [hueSectors + 1]colorMass
	matches  [len(namedHues)]colorMass
}

func measureNormal(pixels []color.RGB) normalSamples {
	var e normalSamples
	// Neighboring 15-degree sectors vote together. Neutrals have their own
	// sector, so noise in the hue of gray pixels cannot determine the tint.
	for _, px := range pixels {
		lab := color.SRGBToOKLab(px)
		t := color.OKLabToOKLCH(lab)
		sample := colorMass{sum: lab, count: 1}
		h := hueSectors
		if t.C >= .022 {
			h = int(t.H/15+.5) % hueSectors
		}
		e.field[h][min(15, int(t.L*16))].add(sample)
		e.families[h].add(sample)
		if t.C < .035 {
			continue
		}
		for i, role := range namedHues {
			if hueGap(t.H, role.hue) > role.radius {
				continue
			}
			if role.name == "brown" && (t.L > .68 || t.C > .16) {
				continue
			}
			e.matches[i].add(sample)
		}
	}
	return e
}

func (e *normalSamples) background(light bool) color.OKLCH {
	var tones [16]colorMass
	highest := 0
	for h := range e.field {
		var bands [16]colorMass
		for l, bin := range e.field[h] {
			bands[l] = bin
			if h < hueSectors {
				bands[l].add(e.field[(h+1)%hueSectors][l])
				bands[l].add(e.field[(h+hueSectors-1)%hueSectors][l])
			}
		}
		var mass int
		for _, band := range bands {
			mass += band.count
		}
		if mass > highest {
			tones, highest = bands, mass
		}
	}
	// Average neighboring shades around the family's lower/upper quartile.
	threshold := (highest + 3) / 4
	if light {
		threshold = highest - threshold + 1
	}
	for l, band := range tones {
		threshold -= band.count
		if threshold > 0 {
			continue
		}
		if l > 0 {
			band.add(tones[l-1])
		}
		if l < 15 {
			band.add(tones[l+1])
		}
		return band.tone()
	}
	return color.OKLCH{}
}

func (e *normalSamples) namedTone(i int, chroma float64) color.OKLCH {
	if e.matches[i].count > 0 {
		return e.matches[i].tone()
	}
	role := namedHues[i]
	t := color.OKLCH{L: .65, C: max(.075, min(.16, chroma)), H: role.hue}
	best := 0.
	for _, family := range e.families[:hueSectors] {
		if family.count == 0 {
			continue
		}
		f := family.tone()
		for _, angle := range [...]float64{0, 30, -30, 120, -120, 150, -150, 180} {
			h := math.Mod(f.H+angle+360, 360)
			gap := hueGap(h, role.hue)
			score := float64(family.count) * (1 - gap/role.radius)
			if score > best {
				best, t.H, t.C = score, h, max(.075, min(.16, f.C))
			}
		}
	}
	return t
}

func normalPalette(pixels []color.RGB, light bool) map[string]string {
	samples := measureNormal(pixels)
	base := samples.background(light)
	white := normalHex(color.OKLCH{L: .957, C: min(.016, base.C*.18), H: base.H})
	black := normalHex(color.OKLCH{L: .16, C: min(.014, base.C*.18), H: base.H})
	fg := white
	if light {
		fg = black
		base.L = max(.82, base.L)
	}
	bg := readableTone(base, fg, 7, light)
	backgroundTone := color.OKLabToOKLCH(color.SRGBToOKLab(color.HexToRGB(bg)))
	out := map[string]string{"foreground": fg, "background": bg, "white": white, "black": black}
	mutedL := backgroundTone.L + .15
	brightL := .985
	if light {
		mutedL, brightL = backgroundTone.L-.15, .105
	}
	out["muted"] = normalHex(color.OKLCH{L: mutedL, C: base.C * .7, H: base.H})
	out["bright_foreground"] = normalHex(color.OKLCH{L: brightL, C: min(.01, base.C*.12), H: base.H})
	for i, role := range namedHues {
		t := samples.namedTone(i, base.C)
		if light {
			t.L = min(t.L, .55)
		} else {
			t.L = max(t.L, .60)
		}
		minContrast := 4.5
		if role.name == "brown" {
			// Brown is a lower-lightness orange swatch. Treating this optional
			// color as status text would turn it into a second pale orange.
			t.L, t.C = .51, min(.11, t.C)
			minContrast = 2
		}
		if role.name == "orange" && !light {
			t.L = max(t.L, .74)
		}
		out[role.name] = readableTone(t, bg, minContrast, !light)
		if i < 6 {
			regular := color.OKLabToOKLCH(color.SRGBToOKLab(color.HexToRGB(out[role.name])))
			t.L = min(.93, regular.L+.10)
			if light {
				t.L = max(.23, regular.L-.08)
			}
			out["bright_"+role.name] = readableTone(t, bg, 4.5, !light)
		}
	}
	return out
}
