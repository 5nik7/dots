// Adapted from Aether; see ../../PROVENANCE.md (module root PROVENANCE.md).
package extraction

// normalizeCounts turns per-color pixel counts into coverage shares in [0,1]
// (each count divided by the total). Returns nil for empty/zero input so callers
// fall back to lightness-only selection.
func normalizeCounts(counts []int) []float64 {
	total := 0
	for _, c := range counts {
		total += c
	}
	if total == 0 {
		return nil
	}
	weights := make([]float64, len(counts))
	for i, c := range counts {
		weights[i] = float64(c) / float64(total)
	}
	return weights
}

// GeneratePaletteByMode dispatches to the palette generator for a given mode.
// The source-tonal recipe retains the original monochrome/chromatic selection.
// The current normal recipe works from original samples before this quantization.
// weights (optional, aligned with dominantColors) carries per-color image coverage;
// the default and source-driven modes use it to prioritize common colors.
func GeneratePaletteByMode(dominantColors []string, weights []float64, lightMode bool, mode string) [16]string {
	switch mode {
	case "dominant", "accent-pop", "hue-balanced", "tonal-range", "teal-orange", "faded-film", "cyanotype", "risograph", "jewel-tones", "accented-analogous", "pentadic", "neutral-accent":
		return studioPalette(dominantColors, weights, lightMode, mode)
	case "monochromatic":
		return GenerateMonochromaticPalette(dominantColors, lightMode)
	case "analogous":
		return GenerateAnalogousPalette(dominantColors, lightMode)
	case "pastel":
		return GeneratePastelPalette(dominantColors, lightMode)
	case "material":
		return GenerateMaterialPalette(dominantColors, lightMode)
	case "colorful":
		return GenerateColorfulPalette(dominantColors, lightMode)
	case "muted":
		return GenerateMutedPalette(dominantColors, lightMode)
	case "bright":
		return GenerateBrightPalette(dominantColors, lightMode)
	case "complementary":
		return GenerateComplementaryPalette(dominantColors, lightMode)
	case "triadic":
		return GenerateTriadicPalette(dominantColors, lightMode)
	case "split-complementary":
		return GenerateSplitComplementaryPalette(dominantColors, lightMode)
	case "tetradic":
		return GenerateTetradicPalette(dominantColors, lightMode)
	case "fire":
		return GenerateFirePalette(dominantColors, lightMode)
	case "ocean":
		return GenerateOceanPalette(dominantColors, lightMode)
	case "forest":
		return GenerateForestPalette(dominantColors, lightMode)
	case "earthtone":
		return GenerateEarthtonePalette(dominantColors, lightMode)
	case "neon":
		return GenerateNeonPalette(dominantColors, lightMode)
	case "sunset":
		return GenerateSunsetPalette(dominantColors, lightMode)
	case "vaporwave":
		return GenerateVaporwavePalette(dominantColors, lightMode)
	case "midnight":
		return GenerateMidnightPalette(dominantColors, lightMode)
	case "aurora":
		return GenerateAuroraPalette(dominantColors, lightMode)
	case "high-contrast":
		return GenerateHighContrastPalette(dominantColors, lightMode)
	case "duotone":
		return GenerateDuotonePalette(dominantColors, lightMode)
	default:
		if isMonochromeWeighted(dominantColors, weights) {
			return GenerateMonochromePalette(dominantColors, lightMode)
		}
		return GenerateChromaticPalette(dominantColors, weights, lightMode)
	}
}
