package main

import (
	"bytes"
	"image"
	"image/color"
	"image/gif"
	"image/jpeg"
	"testing"
)

func TestGIFPaletteAndTransparency(t *testing.T) {
	img := image.NewNRGBA(image.Rect(0, 0, 4, 1))
	img.SetNRGBA(1, 0, color.NRGBA{R: 124, G: 87, B: 63, A: 255})
	img.SetNRGBA(2, 0, color.NRGBA{R: 255, G: 255, B: 255, A: 255})
	img.SetNRGBA(3, 0, color.NRGBA{G: 255, A: 12})
	var buf bytes.Buffer
	if err := encode(&buf, request{Format: "gif"}, img); err != nil {
		t.Fatal(err)
	}
	decoded, err := gif.DecodeAll(&buf)
	if err != nil {
		t.Fatal(err)
	}
	if len(decoded.Image) != 1 {
		t.Fatal("expected one frame")
	}
	for x := range 4 {
		p := color.NRGBAModel.Convert(decoded.Image[0].At(x, 0)).(color.NRGBA)
		if x == 0 || x == 3 {
			if p.A != 0 {
				t.Fatal("expected transparency", p)
			}
		} else if p != img.NRGBAAt(x, 0) {
			t.Fatal("palette color changed", p)
		}
	}
}

func TestJPEGBackground(t *testing.T) {
	img := image.NewNRGBA(image.Rect(0, 0, 32, 32))
	var buf bytes.Buffer
	if err := encode(&buf, request{Format: "jpeg", Quality: 90, Colors: map[string]string{"background": "#204060"}}, img); err != nil {
		t.Fatal(err)
	}
	decoded, err := jpeg.Decode(&buf)
	if err != nil {
		t.Fatal(err)
	}
	rgb := color.NRGBAModel.Convert(decoded.At(16, 16)).(color.NRGBA)
	if rgb.R < 30 || rgb.R > 34 || rgb.G < 62 || rgb.G > 66 || rgb.B < 94 || rgb.B > 98 {
		t.Fatal(rgb)
	}
}
