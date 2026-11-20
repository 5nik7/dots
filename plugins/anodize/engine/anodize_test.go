package anodize

import (
	"bytes"
	"encoding/binary"
	anodizeColor "github.com/5nik7/dots/anodize/color"
	"hash/crc32"
	"image"
	"image/color"
	"image/gif"
	"image/jpeg"
	"image/png"
	"math"
	"reflect"
	"testing"
)

func fixture() []byte { return fixtureSize(32, 32) }
func fixtureSize(width, height int) []byte {
	img := image.NewNRGBA(image.Rect(0, 0, width, height))
	for y := 0; y < height; y++ {
		for x := 0; x < width; x++ {
			img.SetNRGBA(x, y, color.NRGBA{uint8(x * 8), uint8(y * 8), uint8((x + y) * 4), 255})
		}
	}
	var b bytes.Buffer
	_ = png.Encode(&b, img)
	return b.Bytes()
}
func document(t *testing.T) Document {
	t.Helper()
	p, err := Generate(nil, "#725ac1", Options{Mode: "normal"})
	if err != nil {
		t.Fatal(err)
	}
	return Document{Schema: 1, ID: "fixture", Baseline: p, Options: Options{Mode: "normal"}}
}
func TestModesAndDeterminism(t *testing.T) {
	if len(Modes()) != 35 {
		t.Fatal("missing modes")
	}
	data := fixture()
	for _, mode := range Modes() {
		for _, light := range []bool{false, true} {
			t.Run(mode+map[bool]string{false: "/dark", true: "/light"}[light], func(t *testing.T) {
				opts := Options{mode, light}
				a, err := Generate(data, "", opts)
				if err != nil {
					t.Fatal(err)
				}
				b, err := Generate(data, "", opts)
				if err != nil {
					t.Fatal(err)
				}
				if !reflect.DeepEqual(a, b) {
					t.Fatal("non-deterministic generation")
				}
				if len(a) != 16 {
					t.Fatal("expected 16 ANSI colors")
				}
				for k, v := range a {
					if !Hex(v) {
						t.Fatalf("invalid %s=%s", k, v)
					}
				}
				p, err := Generate(nil, "#725ac1", opts)
				if err != nil {
					t.Fatal(err)
				}
				if p["background"] == p["foreground"] {
					t.Fatal("foreground equals background")
				}
			})
		}
	}
}
func TestImageValidationAndFormats(t *testing.T) {
	opts := Options{Mode: "normal"}
	for _, data := range [][]byte{nil, []byte("not an image"), make([]byte, MaxImageBytes+1)} {
		if _, err := Generate(data, "", opts); err == nil {
			t.Fatal("accepted invalid input")
		}
	}
	img := image.NewNRGBA(image.Rect(0, 0, 1, 1))
	var b bytes.Buffer
	_ = png.Encode(&b, img)
	if _, err := Generate(b.Bytes(), "", opts); err == nil {
		t.Fatal("accepted fully transparent input")
	}
	img.Set(0, 0, color.White)
	for _, encode := range []func(*bytes.Buffer) error{
		func(b *bytes.Buffer) error { return png.Encode(b, img) },
		func(b *bytes.Buffer) error { return jpeg.Encode(b, img, nil) },
		func(b *bytes.Buffer) error { return gif.Encode(b, img, nil) },
	} {
		b.Reset()
		if err := encode(&b); err != nil {
			t.Fatal(err)
		}
		if _, err := Generate(b.Bytes(), "", opts); err != nil {
			t.Fatal(err)
		}
	}
	if _, err := Generate(fixture(), "#123456", opts); err == nil {
		t.Fatal("accepted two sources")
	}
	if _, err := Generate(nil, "#xyzxyz", opts); err == nil {
		t.Fatal("accepted invalid color")
	}
	if _, err := Generate(nil, "#123456", Options{Mode: "invalid"}); err == nil {
		t.Fatal("accepted invalid mode")
	}
	// Oversized dimensions are refused before attempting allocation/decoding.
	b.Reset()
	_ = png.Encode(&b, image.NewNRGBA(image.Rect(0, 0, 1, 1)))
	data := b.Bytes()
	data[16], data[17], data[18], data[19] = 0x7f, 0xff, 0xff, 0xff
	binary.BigEndian.PutUint32(data[29:33], crc32.ChecksumIEEE(data[12:29]))
	if _, err := Generate(data, "", opts); err == nil || err.Error() != "image exceeds 20 million pixels" {
		t.Fatal("did not reject oversized dimensions before decoding", err)
	}
}
func TestRepeatableAdjustmentsOverridesAndVariants(t *testing.T) {
	d := document(t)
	original := d.Baseline["blue"]
	d.Adjustments = map[string]float64{"brightness": 10, "gamma": 1.2}
	d.Overrides = map[string]string{"accent": "#123456"}
	a, err := Render(d)
	if err != nil {
		t.Fatal(err)
	}
	b, err := Render(d)
	if err != nil {
		t.Fatal(err)
	}
	if !reflect.DeepEqual(a, b) || d.Baseline["blue"] != original {
		t.Fatal("adjustments compound or mutate baseline")
	}
	if a["accent"] != "#123456" || a["color4"] != a["blue"] {
		t.Fatal("override/ANSI mismatch")
	}
	d.Adjustments = nil
	d.Overrides = nil
	c, _ := Render(d)
	if c["blue"] != original {
		t.Fatal("reset did not restore baseline")
	}
	d.Options.Light = true
	light, err := Variant(d)
	if err != nil {
		t.Fatal(err)
	}
	if light["background"] == c["background"] {
		t.Fatal("variant did not change background")
	}
	if Contrast(map[string]string{"background": "#000000", "foreground": "#ffffff"}) != 21 {
		t.Fatal("contrast math")
	}
}
func TestInvalidDocuments(t *testing.T) {
	for _, mutate := range []func(*Document){
		func(d *Document) { d.Schema = 99 },
		func(d *Document) { d.Baseline["mode"] = "#ffffff" },
		func(d *Document) { d.Overrides = map[string]string{"color0": "#ffffff"} },
		func(d *Document) { d.Options.Mode = "bad" },
		func(d *Document) { d.Adjustments = map[string]float64{"gamma": 0} },
		func(d *Document) { d.Adjustments = map[string]float64{"unknown": 1} },
		func(d *Document) { d.Baseline["red"] = "oops" },
		func(d *Document) { delete(d.Baseline, "red") },
		func(d *Document) { d.Overrides = map[string]string{"escape\n": "#ffffff"} },
	} {
		d := document(t)
		mutate(&d)
		if _, err := Render(d); err == nil {
			t.Fatal("accepted invalid document")
		}
	}
}
func BenchmarkExtract(b *testing.B) {
	data := fixture()
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_, _ = Generate(data, "", Options{Mode: "normal"})
	}
}
func BenchmarkSeed(b *testing.B) {
	for i := 0; i < b.N; i++ {
		_, _ = Generate(nil, "#725ac1", Options{Mode: "normal"})
	}
}

func BenchmarkExtractWallpaper(b *testing.B) {
	data := fixtureSize(1920, 1080)
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_, _ = Generate(data, "", Options{Mode: "normal"})
	}
}

func TestPatinaPixelsAndTransparency(t *testing.T) {
	input := image.NewNRGBA64(image.Rect(0, 0, 4, 1))
	for i, level := range []uint16{0, 0x3333, 0xaaaa, 0xffff} {
		input.SetNRGBA64(i, 0, color.NRGBA64{R: level, G: level, B: level, A: uint16(i) * 0x4567})
	}
	var buf bytes.Buffer
	if err := png.Encode(&buf, input); err != nil {
		t.Fatal(err)
	}
	palette := []string{"#ff0000"}
	for _, style := range []string{"exact", "shaded"} {
		out, err := Patina(buf.Bytes(), palette, style)
		if err != nil || out.Bounds() != input.Bounds() {
			t.Fatalf("%s: %v", style, err)
		}
		for x := range 4 {
			got := color.NRGBA64Model.Convert(out.At(x, 0)).(color.NRGBA64)
			if got.A != input.NRGBA64At(x, 0).A {
				t.Fatal("lost alpha", got)
			}
			if x == 0 {
				continue
			}
			if style == "exact" && (got.R != 65535 || got.G != 0 || got.B != 0) {
				t.Fatal("outside palette", got)
			}
			if style == "shaded" {
				original := input.NRGBA64At(x, 0)
				lightness := func(p color.NRGBA64) float64 {
					return anodizeColor.RGBToOKLab(anodizeColor.RGB{R: float64(p.R) / 257, G: float64(p.G) / 257, B: float64(p.B) / 257}).L
				}
				if math.Abs(lightness(original)-lightness(got)) > 0.005 {
					t.Fatal("lost source lightness", original, got)
				}
			}
		}
	}
	if _, err := Patina([]byte("invalid"), palette, "exact"); err == nil {
		t.Fatal("accepted malformed input")
	}
}

func TestPatinaGIFCanvasAndFirstFrame(t *testing.T) {
	palette := color.Palette{color.Black, color.White}
	img := image.NewPaletted(image.Rect(1, 1, 2, 2), palette)
	img.Pix[0] = 1
	var buf bytes.Buffer
	err := gif.EncodeAll(&buf, &gif.GIF{Image: []*image.Paletted{img, image.NewPaletted(image.Rect(0, 0, 3, 3), palette)}, Delay: []int{1, 1}, Config: image.Config{ColorModel: palette, Width: 3, Height: 3}})
	if err != nil {
		t.Fatal(err)
	}
	out, err := Patina(buf.Bytes(), []string{"#ffffff", "#000000"}, "exact")
	if err != nil {
		t.Fatal(err)
	}
	if out.Bounds() != image.Rect(0, 0, 3, 3) {
		t.Fatal(out.Bounds())
	}
	r, _, _, a := out.At(1, 1).RGBA()
	_, _, _, outside := out.At(0, 0).RGBA()
	if r != 65535 || a != 65535 || outside != 0 {
		t.Fatal("wrong first frame placement")
	}
}

func BenchmarkPatinaWallpaper(b *testing.B) {
	data := fixtureSize(1920, 1080)
	palette := []string{"#101820", "#ffd080", "#21a0a0", "#bf4080", "#bbbbcc", "#434967", "#aaddff", "#64ad40"}
	for _, style := range []string{"alloy", "palette-blend", "harmonize", "gradient", "duotone", "exact", "shaded"} {
		b.Run(style, func(b *testing.B) {
			for b.Loop() {
				if _, err := Patina(data, palette, style); err != nil {
					b.Fatal(err)
				}
			}
		})
	}
}

func TestBatchModesAndRenderedCustomSources(t *testing.T) {
	data := fixture()
	modes := Modes()
	generated, err := GenerateModes(data, "", nil, modes, false)
	if err != nil {
		t.Fatal(err)
	}
	for _, mode := range modes {
		single, err := Generate(data, "", Options{Mode: mode})
		if err != nil || !reflect.DeepEqual(single, generated[mode]) {
			t.Fatal("batch differs for", mode, err)
		}
	}
	theme := map[string]string{}
	for _, k := range ANSIKeys() {
		theme[k] = "#888888"
	}
	plain, err := GenerateModes(nil, "", theme, []string{"accent-pop"}, true)
	if err != nil {
		t.Fatal(err)
	}
	theme["leaf_tip"] = "#48cd63"
	variant, err := GenerateModes(nil, "", theme, []string{"accent-pop"}, true)
	if err != nil {
		t.Fatal(err)
	}
	if plain["accent-pop"]["blue"] == variant["accent-pop"]["blue"] || !Hex(variant["accent-pop"]["leaf_tip"]) {
		t.Fatal("custom source color did not contribute to the variant")
	}
}
