package anodize

import (
	"bytes"
	"encoding/binary"
	"hash/crc32"
	"image"
	"image/color"
	"image/gif"
	"image/jpeg"
	"image/png"
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
	if len(Modes()) != 23 {
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
