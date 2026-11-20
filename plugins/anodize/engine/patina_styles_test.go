package anodize

import (
	"bytes"
	"image"
	stdcolor "image/color"
	"image/png"
	"math"
	"reflect"
	"testing"

	"github.com/5nik7/dots/anodize/color"
)

func standardLCH(rgb color.RGB) color.OKLCH { return color.OKLabToOKLCH(color.SRGBToOKLab(rgb)) }

func TestPatinaKanagawaLeaves(t *testing.T) {
	palette := []string{"#363646", "#60382c", "#76946a", "#98bb6c"}
	transform, err := NewPatinaMapping(palette, nil, PatinaOptions{Style: "harmonize"})
	if err != nil {
		t.Fatal(err)
	}
	green := standardLCH(color.HexToRGB("#76946a"))
	for _, hex := range []string{"#334b24", "#2d5329", "#486b39", "#688455", "#7d9c67"} {
		input := color.HexToRGB(hex)
		result := standardLCH(transform.pixel(input))
		if math.Abs(result.H-green.H) > 30 {
			t.Fatalf("leaf %s became %+v; want a theme green", hex, result)
		}
	}
}

func TestPatinaMissingHueRulesAndNeutrals(t *testing.T) {
	purple := "#935dc1"
	p := standardLCH(color.HexToRGB(purple))
	for _, tc := range []struct {
		rule         string
		offset, want float64
	}{
		{"auto", 150, 150}, {"auto", 180, 180}, {"analogous", 55, 30},
		{"complementary", 160, 180}, {"palette", 180, 0}, {"source", 115, 115},
	} {
		m, err := NewPatinaMapping([]string{purple, "#505050"}, nil, PatinaOptions{Style: "natural", Harmony: tc.rule})
		if err != nil {
			t.Fatal(err)
		}
		src := color.OKLCHToRGB(color.OKLCH{L: 0.64, C: 0.080, H: p.H + tc.offset})
		result := standardLCH(m.pixel(src))
		if arc(result.H, math.Mod(p.H+tc.want, 360)) > 4 || math.Abs(result.L-0.64) > 0.006 {
			t.Fatalf("%+v gave %+v", tc, result)
		}
		if tc.rule != "palette" && math.Abs(result.C-0.08) > 0.007 {
			t.Fatal("missing hue lost chroma", tc, result)
		}
		cloud := color.HexToRGB("#d1d1d1")
		if c := standardLCH(m.pixel(cloud)); c.C > 0.001 {
			t.Fatal("neutral cloud picked up color", c)
		}
	}
	gray, err := NewPatinaMapping([]string{"#404040", "#eeeeee"}, nil, PatinaOptions{})
	if err != nil {
		t.Fatal(err)
	}
	if c := standardLCH(gray.pixel(color.HexToRGB("#4279ae"))); c.C > 0.001 {
		t.Fatal("gray palette introduced hue", c)
	}
}

func TestPatinaNamedRampsAndStrength(t *testing.T) {
	names := map[string]string{"background": "#dddddd", "foreground": "#222222", "custom": "#388766", "accent": "#388766"}
	palette := []string{"#222222", "#388766", "#dddddd"}
	m, err := NewPatinaMapping(palette, names, PatinaOptions{Style: "gradient"})
	if err != nil {
		t.Fatal(err)
	}
	if !reflect.DeepEqual(m.Settings().Stops, []string{"foreground", "accent", "background"}) {
		t.Fatal(m.Settings())
	}
	stops := []string{"custom", "background"}
	input := color.HexToRGB("#789bc5")
	var full color.OKLab
	for _, pct := range []int{100, 50, 0} {
		tint, err := NewPatinaMapping(palette, names, PatinaOptions{Style: "duotone", Strength: &pct, Stops: stops})
		if err != nil {
			t.Fatal(err)
		}
		pixel := tint.pixel(input)
		switch pct {
		case 100:
			full = color.SRGBToOKLab(pixel)
			for index, hex := range []string{"#000000", "#ffffff"} {
				got := color.SRGBToOKLab(tint.pixel(color.HexToRGB(hex)))
				if color.OKLabDistance(got, color.SRGBToOKLab(color.HexToRGB(names[stops[index]]))) > 0.001 {
					t.Fatal("wrong ordered endpoint", got)
				}
			}
		case 50:
			if color.OKLabDistance(color.SRGBToOKLab(pixel), mixLab(color.SRGBToOKLab(input), full, 0.5)) > 0.001 {
				t.Fatal("incorrect blend", pixel)
			}
		case 0:
			if pixel != input {
				t.Fatal("zero strength changed source", pixel)
			}
		}
	}
	for _, opts := range []PatinaOptions{{Style: "exact", Harmony: "source"}, {Style: "gradient", Stops: []string{"bad", "foreground"}}, {Style: "duotone", Stops: []string{"background", "foreground", "custom"}}} {
		if _, err := NewPatinaMapping(palette, names, opts); err == nil {
			t.Fatal("accepted", opts)
		}
	}
}

func TestPatinaSkyRampAndPickerParity(t *testing.T) {
	input := image.NewNRGBA64(image.Rect(0, 0, 180, 1))
	for x := range 180 {
		p := stdcolor.NRGBA64{R: uint16(7000 + 150*x), G: uint16(15000 + 170*x), B: uint16(30000 + 175*x), A: uint16(5000 + 300*x)}
		input.SetNRGBA64(x, 0, p)
	}
	var buf bytes.Buffer
	if err := png.Encode(&buf, input); err != nil {
		t.Fatal(err)
	}
	sample, err := SamplePatinaInput(buf.Bytes(), 37, 4)
	if err != nil {
		t.Fatal(err)
	}
	for _, style := range []string{"alloy", "harmonize", "gradient", "duotone", "exact", "shaded"} {
		m, err := NewPatinaMapping([]string{"#5f7db4", "#162a46", "#bed2e0"}, nil, PatinaOptions{Style: style})
		if err != nil {
			t.Fatal(err)
		}
		full, err := m.Render(buf.Bytes())
		if err != nil {
			t.Fatal(err)
		}
		if !reflect.DeepEqual(m.Preview(sample), PatinaThumbnail(full, 37, 4)) {
			t.Fatal("picker and final differ", style)
		}
		var last color.OKLab
		for x := range 180 {
			dst := full.(*image.NRGBA64).NRGBA64At(x, 0)
			if dst.A != input.NRGBA64At(x, 0).A {
				t.Fatal("lost alpha", style, x)
			}
			lab := color.SRGBToOKLab(color.RGB{R: float64(dst.R) / 257, G: float64(dst.G) / 257, B: float64(dst.B) / 257})
			if style == "harmonize" && x > 0 && lab.L <= last.L {
				t.Fatal("sky lightness reversed", x, last, lab)
			}
			if (style == "alloy" || style == "harmonize") && x > 0 && color.OKLabDistance(lab, last) > .01 {
				t.Fatal("sky band", style, x, last, lab)
			}
			last = lab
		}
	}
	zero := 0
	m, err := NewPatinaMapping([]string{"#ee8899"}, nil, PatinaOptions{Strength: &zero})
	if err != nil {
		t.Fatal(err)
	}
	full, err := m.Render(buf.Bytes())
	if err != nil || !reflect.DeepEqual(full, input) {
		t.Fatal("zero-strength 16-bit PNG lost precision", err)
	}
}

func TestPatinaLegacySwatches(t *testing.T) {
	palette := []string{"#363646", "#60382c", "#76946a", "#98bb6c"}
	inputs := []string{"#2d5329", "#abba64", "#204367", "#808080"}
	for style, want := range map[string][]string{
		"exact":  {"#60382c", "#98bb6c", "#363646", "#76946a"},
		"shaded": {"#653c2f", "#9ac061", "#3f3f51", "#6c8b5b"},
	} {
		m, err := NewPatinaMapping(palette, nil, PatinaOptions{Style: style})
		if err != nil {
			t.Fatal(err)
		}
		for i, hex := range inputs {
			if got := m.pixel(color.HexToRGB(hex)); got != color.HexToRGB(want[i]) {
				t.Fatalf("%s(%s) = %+v, want %s", style, hex, got, want[i])
			}
		}
	}
}

// These 8-bit output samples were captured with the pre-alloy engine.
func TestAlloyParentStyles(t *testing.T) {
	palette := []string{"#363646", "#60382c", "#76946a", "#98bb6c"}
	inputs := []string{"#2d5329", "#abba64", "#204367", "#808080"}
	for style, want := range map[string][]string{
		"harmonize":     {"#556b4e", "#7a9b51", "#5a5f74", "#6c7b63"},
		"palette-blend": {"#524441", "#97ba6c", "#393745", "#768f66"},
	} {
		m, err := NewPatinaMapping(palette, nil, PatinaOptions{Style: style})
		if err != nil {
			t.Fatal(err)
		}
		for i, hex := range inputs {
			got := m.pixel(color.HexToRGB(hex))
			if (color.RGB{R: math.Round(got.R), G: math.Round(got.G), B: math.Round(got.B)}) != color.HexToRGB(want[i]) {
				t.Fatalf("%s(%s) = %v, want %s", style, hex, got, want[i])
			}
		}
	}
}

func TestAlloyHueAndLightness(t *testing.T) {
	for _, tc := range []struct{ from, to, want float64 }{{350, 30, 0}, {30, 350, 20}, {40, 160, 70}, {315, 135, 270}} {
		p := color.OKLCHToOKLab(color.OKLCH{L: .43, C: .10, H: tc.from})
		h := color.OKLCHToOKLab(color.OKLCH{L: .75, C: .18, H: tc.to})
		got := color.OKLabToOKLCH(alloyTone(p, h, .12))
		if arc(got.H, tc.want) > 1e-8 || math.Abs(got.C-.12) > 1e-8 || got.L != p.L {
			t.Fatalf("%+v: got %+v", tc, got)
		}
		h.L = p.L
		if distance := color.OKLabDistance(alloyTone(p, h, 0), mixLab(p, h, .25)); distance > 1e-8 {
			t.Fatalf("neutral input used a hue angle: %g", distance)
		}
	}
}

func TestDefaultAlloyWithHarmony(t *testing.T) {
	palette := []string{"#222222", "#efefef", "#935dc1"}
	input := color.HexToRGB("#30994c")
	var previous color.RGB
	for _, rule := range []string{"palette", "complementary"} {
		opts := PatinaOptions{Harmony: rule}
		implicit, err := NewPatinaMapping(palette, nil, opts)
		if err != nil {
			t.Fatal(err)
		}
		opts.Style = "alloy"
		explicit, err := NewPatinaMapping(palette, nil, opts)
		if err != nil {
			t.Fatal(err)
		}
		got := implicit.pixel(input)
		if implicit.Settings().Style != "alloy" || got != explicit.pixel(input) || got == previous {
			t.Fatal(rule, got)
		}
		p := implicit.paletteBlend(color.SRGBToOKLab(input))
		if math.Abs(color.SRGBToOKLab(got).L-p.L) > 1e-6 {
			t.Fatal("lost palette-blend lightness", rule)
		}
		previous = got
	}
}

func TestPatinaTreatmentsDistinctAndStrength(t *testing.T) {
	data := fixtureSize(36, 30)
	palette := []string{"#26253a", "#e1ddc4", "#91b283", "#df9bbe", "#7493bc", "#c28b68"}
	names := map[string]string{"background": palette[0], "foreground": palette[1], "accent": palette[3]}
	source, _, _ := decodeImage(data)
	seen := map[string]string{}
	zero := 0
	for _, style := range []string{"alloy", "harmonize", "natural", "palette-blend", "color-transfer", "split-tone", "muted", "vivid", "pastel", "night", "accent", "posterize", "dither", "ink", "gradient", "duotone", "exact", "shaded"} {
		m, err := NewPatinaMapping(palette, names, PatinaOptions{Style: style})
		if err != nil {
			t.Fatal(style, err)
		}
		img, err := m.Render(data)
		if err != nil {
			t.Fatal(style, err)
		}
		pixels := string(img.(*image.NRGBA).Pix)
		if other, ok := seen[pixels]; ok {
			t.Fatalf("%s duplicates %s", style, other)
		}
		seen[pixels] = style
		if style == "exact" || style == "shaded" {
			continue
		}
		m, _ = NewPatinaMapping(palette, names, PatinaOptions{Style: style, Strength: &zero})
		img, err = m.Render(data)
		if err != nil {
			t.Fatal(err)
		}
		for y := range img.Bounds().Dy() {
			for x := range img.Bounds().Dx() {
				if stdcolor.NRGBAModel.Convert(img.At(x, y)) != stdcolor.NRGBAModel.Convert(source.At(x, y)) {
					t.Fatalf("%s changed input at zero strength", style)
				}
			}
		}
	}
}

func TestHarmonizeThemeAnchorsAndNatural(t *testing.T) {
	palette := []string{"#302c40", "#ddd2ba", "#76946a"}
	names := map[string]string{"background": palette[0], "foreground": palette[1], "accent": palette[2]}
	full, _ := NewPatinaMapping(palette, names, PatinaOptions{Style: "harmonize"})
	natural, _ := NewPatinaMapping(palette, names, PatinaOptions{Style: "natural"})
	for i, hex := range []string{"#000000", "#ffffff"} {
		source := color.HexToRGB(hex)
		want := color.SRGBToOKLab(color.HexToRGB(palette[i]))
		if d := color.OKLabDistance(color.SRGBToOKLab(full.pixel(source)), want); d > .001 {
			t.Fatal("endpoint missed the theme", hex, d)
		}
		if d := color.OKLabDistance(color.SRGBToOKLab(natural.pixel(source)), color.SRGBToOKLab(source)); d > .001 {
			t.Fatal("natural changed neutral", hex, d)
		}
	}
}

func TestColorTransferPreviewUsesFullImageGroups(t *testing.T) {
	data := fixtureSize(173, 119)
	opts := PatinaOptions{Style: "color-transfer"}
	mapping, err := NewPatinaMapping([]string{"#254040", "#789659", "#be7651", "#c9cef2"}, nil, opts)
	if err != nil {
		t.Fatal(err)
	}
	full, err := mapping.Render(data)
	if err != nil {
		t.Fatal(err)
	}
	sample, groups, err := PatinaSamples(data, 40, 22, true)
	if err != nil {
		t.Fatal(err)
	}
	mapping.SetTransferGroups(groups)
	if !reflect.DeepEqual(mapping.Preview(sample), PatinaThumbnail(full, 40, 11)) {
		t.Fatal("thumbnail changed color assignments")
	}
}
