package extraction

import (
	"math"
	"sort"

	"github.com/5nik7/dots/anodize/color"
)

type weightedTone struct {
	color.OKLCH
	weight float64
}

// Merge duplicate representatives before ranking their image coverage.
func studioPalette(colors []string, weights []float64, light bool, mode string) [16]string {
	shares := map[string]float64{}
	for i, hex := range colors {
		w := 1.0
		if i < len(weights) {
			w = weights[i]
		}
		shares[hex] += w
	}
	tones := make([]weightedTone, 0, len(shares))
	keys := make([]string, 0, len(shares))
	for key := range shares {
		keys = append(keys, key)
	}
	sort.Strings(keys)
	for _, key := range keys {
		tones = append(tones, weightedTone{color.OKLabToOKLCH(color.SRGBToOKLab(color.HexToRGB(key))), shares[key]})
	}
	sort.SliceStable(tones, func(i, j int) bool {
		if tones[i].weight == tones[j].weight {
			return tones[i].C > tones[j].C
		}
		return tones[i].weight > tones[j].weight
	})
	base := tones[0].H
	for _, t := range tones {
		if t.C > .035 {
			base = t.H
			break
		}
	}
	vivid := tones[0]
	for _, t := range tones {
		if t.C > vivid.C {
			vivid = t
		}
	}
	if mode == "tonal-range" {
		sort.SliceStable(tones, func(i, j int) bool { return tones[i].L < tones[j].L })
	}
	var hue, chroma, offset [6]float64
	for i := range hue {
		t := tones[i%len(tones)]
		hue[i], chroma[i], offset[i] = t.H, math.Max(.045, t.C), (t.L-.5)*.35
		switch mode {
		case "dominant":
			// Keep the most common source families, including their muted shades.
			chroma[i] = t.C
		case "hue-balanced":
			// Maximize the smallest angular distance to a previously assigned hue.
			if i > 0 {
				best := -1.0
				for _, candidate := range tones {
					gap := 180.0
					for _, h := range hue[:i] {
						d := math.Abs(h - candidate.H)
						gap = math.Min(gap, math.Min(d, 360-d))
					}
					score := gap*math.Min(1, candidate.C/.06) + candidate.weight*.01
					if score > best {
						best = score
						t = candidate
					}
				}
			}
			hue[i], chroma[i], offset[i] = t.H, math.Max(.09, t.C), float64(i-2)*.018
		case "tonal-range":
			total := 0.0
			for _, tone := range tones {
				total += tone.weight
			}
			quantile := total * float64(i) / 5
			for _, tone := range tones {
				t = tone
				quantile -= t.weight
				if quantile <= 0 {
					break
				}
			}
			hue[i], chroma[i], offset[i] = t.H, t.C, (float64(i)-2.5)*.065
		case "accent-pop", "neutral-accent":
			hue[i], chroma[i] = base, .015
			if mode == "accent-pop" {
				hue[i], chroma[i] = t.H, t.C*.40
			}
			if i == 3 {
				hue[i], chroma[i] = vivid.H, math.Max(.17, vivid.C)
			}
			offset[i] = float64(i-2) * .035
		case "teal-orange":
			hue[i] = [6]float64{38, 180, 62, 212, 28, 194}[i]
			chroma[i] = .13
			offset[i] = float64(i%3-1) * .07
		case "faded-film":
			hue[i] = base + [6]float64{18, 60, 86, 186, 310, 200}[i]
			chroma[i] = .055
			offset[i] = .065 + float64(i%3)*.025
		case "cyanotype":
			hue[i] = 234 + float64(i)*3
			chroma[i] = .105 - float64(i)*.01
			offset[i] = float64(i-3) * .066
		case "risograph":
			hue[i] = [6]float64{16, 165, 91, 265, 346, 209}[i]
			chroma[i] = .205
			offset[i] = float64(i%3-1) * .06
		case "jewel-tones":
			hue[i] = [6]float64{19, 151, 81, 265, 310, 195}[i]
			chroma[i] = .185
			offset[i] = -.10 + float64(i%3)*.027
		case "accented-analogous":
			hue[i] = base + [6]float64{-36, -18, 0, 180, 18, 36}[i]
			chroma[i] = .13
			offset[i] = float64(i%3-1) * .05
		case "pentadic":
			hue[i] = base + float64(i%5)*72
			chroma[i] = .145
			offset[i] = float64(i-2) * .026
		}
	}
	// Anchor themed paper and shadows in the same family as the print inks.
	// A small rotation keeps fixed-hue looks responsive to the source.
	tint := 8 * math.Sin(base*math.Pi/180)
	switch mode {
	case "cyanotype":
		base = 242
	case "teal-orange":
		base = 198
	case "risograph":
		base = 62
	case "jewel-tones":
		base = 275
	default:
		return buildSchemePalette(base, light, hue, chroma, offset)
	}
	for i := range hue {
		hue[i] += tint
	}
	return buildSchemePalette(base+tint, light, hue, chroma, offset)
}
