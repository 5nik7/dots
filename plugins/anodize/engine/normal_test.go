package anodize

import (
	"bytes"
	"image"
	stdcolor "image/color"
	"image/png"
	"math"
	"testing"

	"github.com/5nik7/dots/anodize/color"
)

func TestNormalPaletteCoverageAndContrast(t *testing.T) {
	tone := func(hex string) color.OKLCH {
		return color.OKLabToOKLCH(color.SRGBToOKLab(color.HexToRGB(hex)))
	}
	for _, field := range []string{"#49634d", "#e8ca81", "#999999", "#ffffff", "#000000"} {
		// Exercise a dominant area, deep shadow, and small brick-red detail.
		pixels := make([]color.RGB, 100)
		for i := range pixels {
			hex := field
			if i < 15 {
				hex = "#11131a"
			}
			if i == 0 {
				hex = "#b34a3a"
			}
			pixels[i] = color.HexToRGB(hex)
		}
		for _, light := range []bool{false, true} {
			p := normalPalette(pixels, light)
			bg, fg := tone(p["background"]), tone(p["foreground"])
			source := tone(field)
			if source.C > .02 && (hueGap(bg.H, source.H) > 4 || bg.C < .025) {
				t.Fatalf("%s light=%t lost dominant family in %s", field, light, p["background"])
			}
			if source.C < .01 && (bg.C > .005 || fg.C > .005) {
				t.Fatalf("neutral source picked up a minority tint: %v", p)
			}
			if light && (fg.L > .2 || bg.L < .81) || !light && (fg.L < .94 || bg.L > .5) || color.ContrastRatio(p["background"], p["foreground"]) < 7 {
				t.Fatalf("%s light=%t foreground contrast or polarity: %v", field, light, p)
			}
			for _, role := range namedHues {
				c := tone(p[role.name])
				if c.C < .023 || hueGap(c.H, role.hue) > role.radius+3 {
					t.Errorf("%s light=%t %s outside hue family: %+v", field, light, role.name, c)
				}
				if role.name != "brown" && color.ContrastRatio(p[role.name], p["background"]) < 4.5 {
					t.Errorf("unreadable %s accent %s on %s", role.name, p[role.name], p["background"])
				}
				if bright, ok := p["bright_"+role.name]; ok && hueGap(c.H, tone(bright).H) > 4 {
					t.Errorf("bright %s lost hue: %s, %s", role.name, p[role.name], bright)
				}
			}
			if hueGap(tone(p["red"]).H, tone("#b34a3a").H) > 3 {
				t.Fatalf("small red detail lost: %s", p["red"])
			}
			if tone(p["brown"]).L >= tone(p["orange"]).L && !light {
				t.Errorf("brown is not darker than orange on %s", p["background"])
			}
			doc := Document{Schema: 1, Options: Options{"normal", light}, Baseline: p,
				Overrides: map[string]string{"green": "#123456", "warning": "#abcdef"}}
			rendered, err := Render(doc)
			if err != nil || rendered["success"] != "#123456" || rendered["warning"] != "#abcdef" || rendered["error"] != p["red"] || rendered["info"] != p["blue"] || rendered["hint"] != p["cyan"] {
				t.Fatalf("semantic aliases and overrides: %v, %v", rendered, err)
			}
		}
	}
	gray := normalPalette([]color.RGB{color.HexToRGB("#777777")}, false)
	for _, role := range namedHues {
		c := tone(gray[role.name])
		if c.C < .045 || c.C > .125 || math.IsNaN(c.H) {
			t.Errorf("grayscale fallback for %s: %+v", role.name, c)
		}
	}
}

func TestSourceTonalRetainsOriginalMossPalette(t *testing.T) {
	img := image.NewNRGBA(image.Rect(0, 0, 100, 100))
	for y := range 100 {
		for x := range 100 {
			c := stdcolor.NRGBA{73, 99, 77, 255}
			switch {
			case x < 15:
				c = stdcolor.NRGBA{16, 18, 23, 255}
			case x < 20:
				c = stdcolor.NRGBA{214, 207, 182, 255}
			}
			img.SetNRGBA(x, y, c)
		}
	}
	var buf bytes.Buffer
	if err := png.Encode(&buf, img); err != nil {
		t.Fatal(err)
	}
	p, err := Generate(buf.Bytes(), "", Options{Mode: "source-tonal"})
	if err != nil {
		t.Fatal(err)
	}
	original := map[string]string{"background": "#101218", "foreground": "#d6d0b3", "red": "#9a9c7d", "green": "#b5cfae", "yellow": "#e6ffd3", "blue": "#668d7f", "cyan": "#bcebc8", "magenta": "#bbaf85"}
	for key, want := range original {
		if p[key] != want {
			t.Errorf("original normal %s = %s, got %s", key, want, p[key])
		}
	}
}
