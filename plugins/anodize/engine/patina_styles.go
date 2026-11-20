package anodize

import (
	"errors"
	"fmt"
	"math"
	"sort"

	"github.com/5nik7/dots/anodize/color"
)

// PatinaOptions describes a treatment independently of its input image.
// Stops are ordered names in the resolved palette.
type PatinaOptions struct {
	Style    string   `json:"style"`
	Harmony  string   `json:"harmony,omitempty"`
	Strength *int     `json:"strength,omitempty"`
	Stops    []string `json:"stops,omitempty"`
}

type PatinaMapping struct {
	options             PatinaOptions
	swatches            []swatch
	ramp                []color.OKLab
	hues                []hueMatch
	strength            float64
	dark, light, accent color.OKLab
	family              [361]color.OKLab
	transfer            []transferPair
}

// Settings returns the effective options, including automatically selected stops.
func (m *PatinaMapping) Settings() PatinaOptions { return m.options }

func NewPatinaMapping(palette []string, names map[string]string, opts PatinaOptions) (*PatinaMapping, error) {
	if len(palette) == 0 {
		return nil, errors.New("empty patina palette")
	}
	m := &PatinaMapping{options: opts, strength: 1}
	toLab := color.SRGBToOKLab
	if opts.Style == "exact" || opts.Style == "shaded" {
		toLab = color.RGBToOKLab
	}
	for _, hex := range palette {
		if !Hex(hex) {
			return nil, errors.New("invalid patina color")
		}
		rgb := color.HexToRGB(hex)
		m.swatches = append(m.swatches, swatch{rgb, toLab(rgb)})
	}
	if opts.Style == "" {
		m.options.Style = "alloy"
	}
	if m.options.Style == "exact" || m.options.Style == "shaded" {
		if opts.Strength != nil || opts.Harmony != "" || len(opts.Stops) > 0 {
			return nil, errors.New("exact and shaded take no strength, harmony or stops")
		}
		return m, nil
	}
	strength := 100
	if opts.Strength != nil {
		strength = *opts.Strength
	}
	if strength < 0 || strength > 100 {
		return nil, errors.New("strength must be between 0 and 100")
	}
	m.strength = float64(strength) / 100
	m.options.Strength = &strength
	switch m.options.Style {
	case "alloy", "harmonize", "natural":
		if len(opts.Stops) > 0 {
			return nil, errors.New("stops require gradient or duotone")
		}
		if opts.Harmony == "" {
			m.options.Harmony = "auto"
		}
		offsets := map[string][]float64{"auto": {30, -30, 150, -150, 180}, "analogous": {30, -30}, "complementary": {180}, "palette": nil, "source": nil}
		angles, ok := offsets[m.options.Harmony]
		if !ok {
			return nil, fmt.Errorf("unknown harmony %q", opts.Harmony)
		}
		m.hues = buildHueMap(m.swatches, angles, m.options.Harmony == "source")
	case "palette-blend", "color-transfer", "split-tone", "muted", "vivid", "pastel", "night", "accent", "posterize", "dither", "ink":
		if opts.Harmony != "" || len(opts.Stops) > 0 {
			return nil, errors.New("harmony requires alloy, harmonize or natural; stops require gradient or duotone")
		}
	case "gradient", "duotone":
		if opts.Harmony != "" {
			return nil, errors.New("harmony requires alloy, harmonize or natural")
		}
		if len(names) == 0 {
			names = make(map[string]string)
			for _, hex := range palette {
				names[hex] = hex
			}
		}
		for _, hex := range names {
			if !Hex(hex) {
				return nil, errors.New("invalid named palette color")
			}
		}
		if len(opts.Stops) == 0 {
			m.options.Stops = automaticStops(names, m.options.Style)
		}
		stops := m.options.Stops
		if len(stops) < 2 || (m.options.Style == "duotone" && len(stops) != 2) {
			return nil, errors.New("gradient needs at least two stops and duotone needs exactly two")
		}
		for _, name := range stops {
			hex, ok := names[name]
			if !ok || !Hex(hex) {
				return nil, fmt.Errorf("unknown or invalid palette stop %q", name)
			}
			m.ramp = append(m.ramp, color.SRGBToOKLab(color.HexToRGB(hex)))
		}
	default:
		return nil, errors.New("unknown patina style")
	}
	if m.options.Style != "natural" && m.options.Style != "palette-blend" && len(m.ramp) == 0 {
		m.prepareTones(names)
	}
	return m, nil
}

func automaticStops(names map[string]string, style string) []string {
	keys := make([]string, 0, len(names))
	tones := make(map[string]color.OKLCH, len(names))
	for key, hex := range names {
		keys = append(keys, key)
		tones[key] = color.OKLabToOKLCH(color.SRGBToOKLab(color.HexToRGB(hex)))
	}
	sort.Strings(keys)
	lo, hi := "background", "foreground"
	if names[lo] == "" || names[hi] == "" || names[lo] == names[hi] {
		lo, hi = keys[0], keys[0]
		for _, k := range keys {
			if tones[k].L < tones[lo].L {
				lo = k
			}
			if tones[k].L > tones[hi].L {
				hi = k
			}
		}
	}
	if tones[lo].L > tones[hi].L {
		lo, hi = hi, lo
	}
	if style == "gradient" {
		low, high := tones[lo].L, tones[hi].L
		middle, best := "", math.Inf(1)
		// If the accent duplicates an endpoint, prefer a midtone with the
		// accent's character over an unrelated vivid terminal color.
		accent := tones["accent"]
		for _, key := range keys {
			c := tones[key]
			if c.L <= low+0.02 || c.L >= high-0.02 || c.C < 0.025 {
				continue
			}
			if key == "accent" {
				middle = key
				break
			}
			score := math.Abs(c.L-(low+high)/2) + math.Abs(c.C-max(0.06, min(0.12, accent.C)))
			if accent.C >= 0.025 {
				score += 0.12 * arc(c.H, accent.H) / 180
			}
			if score < best {
				middle, best = key, score
			}
		}
		if middle != "" {
			return []string{lo, middle, hi}
		}
	}
	return []string{lo, hi}
}

func mix(a, b, t float64) float64 { return a + (b-a)*t }
func mixLab(a, b color.OKLab, t float64) color.OKLab {
	return color.OKLab{L: mix(a.L, b.L, t), A: mix(a.A, b.A, t), B: mix(a.B, b.B, t)}
}
func smooth(low, high, x float64) float64 {
	t := max(0, min(1, (x-low)/(high-low)))
	return t * t * (3 - 2*t)
}

// Hue correspondence is independent of pixel lightness. Precompute one turn of
// the wheel and interpolate across the seam as well as between adjacent degrees.
// A mapped axis is affine in source chroma: chroma*unit + tint. Direct matches
// borrow some palette chroma; synthesized hues retain the source chroma.
type hueMatch struct{ unitA, unitB, tintA, tintB float64 }

func (a hueMatch) blend(b hueMatch, t float64) hueMatch {
	return hueMatch{mix(a.unitA, b.unitA, t), mix(a.unitB, b.unitB, t), mix(a.tintA, b.tintA, t), mix(a.tintB, b.tintB, t)}
}

type hueAnchor struct{ angle, a, b, chroma float64 }

func anchor(angle, chroma float64) hueAnchor {
	sine, cosine := math.Sincos(angle * math.Pi / 180)
	return hueAnchor{math.Mod(angle+360, 360), cosine, sine, chroma}
}
func arc(a, b float64) float64 { d := math.Abs(a - b); return min(d, 360-d) }

func hueMatchAt(h float64, anchors []hueAnchor, borrow float64) (hueMatch, float64) {
	nearest := 180.0
	for _, p := range anchors {
		nearest = min(nearest, arc(h, p.angle))
	}
	var sum hueMatch
	weight := 0.0
	for _, p := range anchors {
		// Only near-ties share weight, to avoid abrupt borders at hue midpoints.
		w := 1 - smooth(0, 12, arc(h, p.angle)-nearest)
		if w == 0 {
			continue
		}
		weight += w
		sum.unitA += w * p.a * (1 - borrow)
		sum.unitB += w * p.b * (1 - borrow)
		sum.tintA += w * p.a * p.chroma * borrow
		sum.tintB += w * p.b * p.chroma * borrow
	}
	return hueMatch{sum.unitA / weight, sum.unitB / weight, sum.tintA / weight, sum.tintB / weight}, nearest
}

func buildHueMap(swatches []swatch, offsets []float64, source bool) []hueMatch {
	var direct, derived []hueAnchor
	for _, s := range swatches {
		c := color.OKLabToOKLCH(s.lab)
		if c.C < 0.025 {
			continue
		}
		direct = append(direct, anchor(c.H, c.C))
		for _, d := range offsets {
			derived = append(derived, anchor(c.H+d, c.C))
		}
	}
	if len(direct) == 0 {
		return nil
	}
	wheel := make([]hueMatch, 361)
	for i := range 360 {
		h := float64(i)
		match, distance := hueMatchAt(h, direct, 0.45)
		// Keep genuine palette hues first. Fade into the missing-hue rule
		// across the edge of a color family instead of switching abruptly.
		missing := smooth(18, 38, distance)
		if missing > 0 && source {
			p := anchor(h, 0)
			match = match.blend(hueMatch{unitA: p.a, unitB: p.b}, missing)
		} else if missing > 0 && len(derived) > 0 {
			extension, gap := hueMatchAt(h, derived, 0)
			if gap < distance {
				match = match.blend(extension, missing*smooth(0, 8, distance-gap))
			}
		}
		wheel[i] = match
	}
	wheel[360] = wheel[0]
	return wheel
}

func (m *PatinaMapping) pixel(rgb color.RGB) color.RGB {
	return m.pixelAt(rgb, 0, 0, 0)
}

func (m *PatinaMapping) pixelAt(rgb color.RGB, x, y int, edge float64) color.RGB {
	if m.strength == 0 {
		return rgb
	}
	if m.options.Style == "exact" || m.options.Style == "shaded" {
		return mapped(color.RGBToOKLab(rgb), m.swatches, m.options.Style)
	}
	lab := color.SRGBToOKLab(rgb)
	var target color.OKLab
	switch m.options.Style {
	case "gradient", "duotone":
		pos := max(0, min(1, lab.L)) * float64(len(m.ramp)-1)
		i := min(int(pos), len(m.ramp)-2)
		target = mixLab(m.ramp[i], m.ramp[i+1], pos-float64(i))
	case "palette-blend":
		target = m.paletteBlend(lab)
	case "alloy", "harmonize", "natural":
		c := color.OKLabToOKLCH(lab)
		target = color.OKLab{L: lab.L}
		if len(m.hues) > 0 {
			i := min(int(c.H), 359)
			match := m.hues[i].blend(m.hues[i+1], c.H-float64(i))
			target = color.OKLab{L: lab.L, A: match.unitA*c.C + match.tintA, B: match.unitB*c.C + match.tintB}
			target = mixLab(lab, target, smooth(.010, .050, c.C))
		} else if m.options.Style == "natural" && m.options.Harmony == "source" {
			return rgb
		}
		if m.options.Style != "natural" {
			mid := m.middle(c)
			// The harmony rule tints the midtone between the palette endpoints.
			if len(m.hues) > 0 {
				mid.A = mix(mid.A, target.A, .24)
				mid.B = mix(mid.B, target.B, .24)
			}
			target = m.toned(lab.L, mid)
			if m.options.Style == "alloy" {
				target = alloyTone(m.paletteBlend(lab), target, c.C)
			}
		}
	default:
		target = m.stylize(lab, x, y, edge)
	}
	target = mixLab(lab, target, m.strength)
	return color.GamutMappedRGB(target)
}
