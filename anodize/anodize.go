// Package anodize provides pure palette generation and repeatable theme adjustments.
// It does not read files, execute programs, or write caches.
package anodize

import (
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"image"
	stdcolor "image/color"
	_ "image/gif"
	_ "image/jpeg"
	_ "image/png"
	"math"
	"regexp"
	"slices"
	"strings"

	"github.com/5nik7/dots/anodize/color"
	"github.com/5nik7/dots/anodize/internal/extraction"
)

const MaxImageBytes = 32 << 20
const MaxImagePixels = 20_000_000

var modes = []string{"normal", "monochromatic", "analogous", "pastel", "material", "colorful", "muted", "bright", "complementary", "triadic", "split-complementary", "tetradic", "fire", "ocean", "forest", "earthtone", "neon", "sunset", "vaporwave", "midnight", "aurora", "high-contrast", "duotone"}
var names = []string{"background", "red", "green", "yellow", "blue", "magenta", "cyan", "foreground", "muted", "bright_red", "bright_green", "bright_yellow", "bright_blue", "bright_magenta", "bright_cyan", "bright_foreground"}
var keyPattern = regexp.MustCompile(`^[a-zA-Z_][a-zA-Z0-9_]*$`)

func Modes() []string    { return slices.Clone(modes) }
func ANSIKeys() []string { return slices.Clone(names) }

type Options struct {
	Mode  string `json:"mode"`
	Light bool   `json:"light"`
}

// Document preserves an unadjusted baseline; Render never mutates it.
type Document struct {
	Schema      int                        `json:"schema"`
	ID          string                     `json:"id"`
	Baseline    map[string]string          `json:"baseline"`
	Adjustments map[string]float64         `json:"adjustments"`
	Overrides   map[string]string          `json:"overrides"`
	Options     Options                    `json:"options"`
	Wallpaper   string                     `json:"wallpaper,omitempty"`
	Seed        string                     `json:"seed,omitempty"`
	Provenance  map[string]json.RawMessage `json:"provenance,omitempty"`
}

func Hex(s string) bool { return len(s) == 7 && color.IsHexColor(s) }

// Generate accepts encoded PNG/JPEG/GIF bytes or one #RRGGBB seed (exactly one).
func Generate(data []byte, seed string, options Options) (map[string]string, error) {
	if !slices.Contains(modes, options.Mode) {
		return nil, errors.New("unknown extraction mode")
	}
	if (len(data) == 0) == (seed == "") {
		return nil, errors.New("provide exactly one image or color")
	}
	var dominant []string
	var weights []float64
	if seed != "" {
		if !Hex(seed) {
			return nil, errors.New("color must be #RRGGBB")
		}
		dominant = []string{seed}
		weights = []float64{1}
	} else {
		if len(data) > MaxImageBytes {
			return nil, errors.New("image exceeds 32 MiB")
		}
		cfg, _, err := image.DecodeConfig(bytes.NewReader(data))
		if err != nil {
			return nil, errors.New("unsupported or invalid image; use PNG, JPEG, or GIF")
		}
		if cfg.Width <= 0 || cfg.Height <= 0 || int64(cfg.Width)*int64(cfg.Height) > MaxImagePixels {
			return nil, errors.New("image exceeds 20 million pixels")
		}
		img, _, err := image.Decode(bytes.NewReader(data))
		if err != nil {
			return nil, errors.New("cannot decode image")
		}
		bounds := img.Bounds()
		step := int(math.Ceil(math.Sqrt(float64(bounds.Dx()*bounds.Dy()) / 40000)))
		step = max(1, step)
		pixels := make([]color.RGB, 0, 50000)
		for y := bounds.Min.Y; y < bounds.Max.Y; y += step {
			for x := bounds.Min.X; x < bounds.Max.X; x += step {
				c := stdcolor.NRGBAModel.Convert(img.At(x, y)).(stdcolor.NRGBA)
				if c.A >= 128 {
					pixels = append(pixels, color.RGB{R: float64(c.R), G: float64(c.G), B: float64(c.B)})
				}
			}
		}
		if len(pixels) == 0 {
			return nil, errors.New("image has no opaque pixels")
		}
		// Small icons and solid images are valid inputs too.
		for len(pixels) < 100 {
			pixels = append(pixels, pixels...)
		}
		var counts []int
		dominant, counts, err = extraction.ExtractDominantColorsFromPixels(pixels, 48)
		if err != nil {
			return nil, err
		}
		total := 0
		for _, n := range counts {
			total += n
		}
		for _, n := range counts {
			weights = append(weights, float64(n)/float64(total))
		}
	}
	// Generators select several slots; repeat a small pool without inventing input hues.
	for len(dominant) < 8 {
		dominant = append(dominant, dominant...)
		weights = append(weights, weights...)
	}
	return generatePalette(dominant, weights, options), nil
}

// Variant regenerates a palette from existing colors without needing its original image.
func Variant(d Document) (map[string]string, error) {
	if _, err := Render(d); err != nil {
		return nil, err
	}
	dominant := make([]string, 0, len(names))
	for _, name := range names {
		dominant = append(dominant, d.Baseline[name])
	}
	return generatePalette(dominant, nil, d.Options), nil
}

func generatePalette(dominant []string, weights []float64, options Options) map[string]string {
	palette := extraction.NormalizeBrightness(extraction.GeneratePaletteByMode(dominant, weights, options.Light, options.Mode))
	result := map[string]string{}
	for i, k := range names {
		result[k] = strings.ToLower(palette[i])
	}
	return result
}

func adjustments(values map[string]float64) (color.Adjustments, error) {
	a := color.DefaultAdjustments()
	fields := map[string]*float64{"vibrance": &a.Vibrance, "saturation": &a.Saturation, "contrast": &a.Contrast, "brightness": &a.Brightness, "shadows": &a.Shadows, "highlights": &a.Highlights, "hueShift": &a.HueShift, "temperature": &a.Temperature, "tint": &a.Tint, "gamma": &a.Gamma, "blackPoint": &a.BlackPoint, "whitePoint": &a.WhitePoint}
	for k, v := range values {
		field, ok := fields[k]
		if !ok {
			return a, fmt.Errorf("unknown adjustment: %s", k)
		}
		low, high := -100.0, 100.0
		if k == "hueShift" {
			low, high = -360, 360
		}
		if k == "gamma" {
			low, high = 0.1, 10
		}
		if math.IsNaN(v) || math.IsInf(v, 0) || v < low || v > high {
			return a, fmt.Errorf("adjustment %s must be between %g and %g", k, low, high)
		}
		*field = v
	}
	return a, nil
}

func Render(d Document) (map[string]string, error) {
	if d.Schema != 1 {
		return nil, errors.New("unsupported Anodize document schema")
	}
	if !slices.Contains(modes, d.Options.Mode) {
		return nil, errors.New("unknown extraction mode")
	}
	a, err := adjustments(d.Adjustments)
	if err != nil {
		return nil, err
	}
	out := map[string]string{}
	for k, v := range d.Baseline {
		if !keyPattern.MatchString(k) || k == "mode" || len(k) > 64 || !Hex(v) {
			return nil, errors.New("invalid baseline color")
		}
		out[k] = strings.ToLower(color.AdjustColor(v, a))
	}
	for _, k := range names {
		if out[k] == "" {
			return nil, fmt.Errorf("missing baseline color: %s", k)
		}
	}
	for k, v := range d.Overrides {
		for i := range names {
			if k == fmt.Sprintf("color%d", i) {
				return nil, fmt.Errorf("override %s using its named key %s", k, names[i])
			}
		}
		if !keyPattern.MatchString(k) || k == "mode" || len(k) > 64 || !Hex(v) {
			return nil, errors.New("invalid color override")
		}
		out[k] = strings.ToLower(v)
	}
	defaults := map[string]string{"accent": "blue", "cursor": "foreground", "selection": "muted", "selection_background": "selection", "selection_foreground": "foreground", "error": "red", "warning": "yellow", "info": "blue", "hint": "cyan", "orange": "yellow", "brown": "muted", "dark_background": "background", "darker_background": "background", "lighter_background": "background", "dark_foreground": "foreground", "light_foreground": "foreground"}
	// Selection is resolved first because selection_background references it.
	if out["selection"] == "" {
		out["selection"] = out["muted"]
	}
	for k, v := range defaults {
		if out[k] == "" {
			out[k] = out[v]
		}
	}
	for i, k := range names {
		out[fmt.Sprintf("color%d", i)] = out[k]
	}
	return out, nil
}

func Contrast(colors map[string]string) float64 {
	return color.ContrastRatio(colors["foreground"], colors["background"])
}
