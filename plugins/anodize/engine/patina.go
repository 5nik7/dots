package anodize

import (
	"image"
	stdcolor "image/color"
	"image/draw"
	"math"

	"github.com/5nik7/dots/anodize/color"
)

type swatch struct {
	rgb color.RGB
	lab color.OKLab
}

// Patina maps visible pixels to an ordered palette. Equal distances favor
// the first swatch. A GIF's first frame is placed on its logical canvas.
func Patina(data []byte, palette []string, style string) (image.Image, error) {
	mapping, err := NewPatinaMapping(palette, nil, PatinaOptions{Style: style})
	if err != nil {
		return nil, err
	}
	return mapping.Render(data)
}

// Render applies one mapping at the source resolution.
func (m *PatinaMapping) Render(data []byte) (image.Image, error) {
	src, cfg, err := decodeImage(data)
	if err != nil {
		return nil, err
	}
	if m.options.Style == "color-transfer" {
		m.SetTransferGroups(TransferGroups(src, cfg.Width, cfg.Height))
	}
	canvas := image.Rect(0, 0, cfg.Width, cfg.Height)
	// Retain 16-bit PNG alpha where present without doubling memory for
	// ordinary wallpapers. Transparent space outside a GIF frame stays clear.
	switch img := src.(type) {
	case *image.NRGBA64:
		return m.map16(img), nil
	case *image.RGBA64, *image.Gray16:
		out := image.NewNRGBA64(canvas)
		draw.Draw(out, canvas, src, image.Point{}, draw.Src)
		return m.map16(out), nil
	}

	out, ok := src.(*image.NRGBA)
	if !ok {
		out = image.NewNRGBA(canvas)
		draw.Draw(out, src.Bounds(), src, src.Bounds().Min, draw.Src)
	}
	return m.map8(out), nil
}

func (m *PatinaMapping) map8(out *image.NRGBA) *image.NRGBA {
	if m.strength == 0 {
		return out
	}
	for i := len(out.Pix) - 4; i >= 0; i -= 4 {
		p := out.Pix[i : i+4]
		if p[3] != 0 {
			x, y := (i%out.Stride)/4, i/out.Stride
			c := m.pixelAt(color.RGB{R: float64(p[0]), G: float64(p[1]), B: float64(p[2])}, x, y, m.edge(out, x, y))
			p[0], p[1], p[2] = uint8(math.Round(c.R)), uint8(math.Round(c.G)), uint8(math.Round(c.B))
		}
	}
	return out
}

func (m *PatinaMapping) map16(out *image.NRGBA64) *image.NRGBA64 {
	if m.strength == 0 {
		return out
	}
	for y := out.Bounds().Max.Y - 1; y >= 0; y-- {
		for x := out.Bounds().Max.X - 1; x >= 0; x-- {
			p := out.NRGBA64At(x, y)
			if p.A == 0 {
				continue
			}
			c := m.pixelAt(color.RGB{R: float64(p.R) / 257, G: float64(p.G) / 257, B: float64(p.B) / 257}, x, y, m.edge(out, x, y))
			out.SetNRGBA64(x, y, stdcolor.NRGBA64{uint16(math.Round(c.R * 257)), uint16(math.Round(c.G * 257)), uint16(math.Round(c.B * 257)), p.A})
		}
	}
	return out
}

func mapped(lab color.OKLab, colors []swatch, style string) color.RGB {
	best, distance := colors[0], 1e9
	for _, c := range colors {
		l, a, b := lab.L-c.lab.L, lab.A-c.lab.A, lab.B-c.lab.B
		d := l*l + a*a + b*b
		if d < distance {
			best, distance = c, d
		}
	}
	if style == "shaded" {
		return color.WithLightness(best.lab, lab.L)
	}
	return best.rgb
}

// SamplePatinaInput decodes once, honoring the logical canvas of a GIF.
// Each candidate uses the same bounded sample and the full-resolution mapper.
func SamplePatinaInput(data []byte, columns, rows int) (image.Image, error) {
	src, cfg, err := decodeImage(data)
	if err != nil {
		return nil, err
	}
	return sampleRaster(src, cfg.Width, cfg.Height, columns, rows), nil
}

// PatinaThumbnail samples the completed output for final review.
func PatinaThumbnail(img image.Image, columns, rows int) image.Image {
	return sampleRaster(img, img.Bounds().Dx(), img.Bounds().Dy(), columns, rows)
}

func sampleRaster(src image.Image, width, height, columns, rows int) image.Image {
	scale := min(1.0, float64(max(1, min(360, columns)))/float64(width), float64(2*max(1, min(120, rows)))/float64(height))
	cols, lines := max(1, int(math.Round(float64(width)*scale))), max(1, int(math.Round(float64(height)*scale)))
	bounds := image.Rect(0, 0, cols, lines)
	var out draw.Image
	switch src.(type) {
	case *image.NRGBA64, *image.RGBA64, *image.Gray16:
		out = image.NewNRGBA64(bounds)
	default:
		out = image.NewNRGBA(bounds)
	}
	for y := range lines {
		for x := range cols {
			sx := int(int64(2*x+1) * int64(width) / int64(2*cols))
			sy := int(int64(2*y+1) * int64(height) / int64(2*lines))
			if image.Pt(sx, sy).In(src.Bounds()) {
				draw.Draw(out, image.Rect(x, y, x+1, y+1), src, image.Pt(sx, sy), draw.Src)
			}
		}
	}
	return out
}

// Preview renders a separate copy so the input sample can be shared by styles.
func (m *PatinaMapping) Preview(sample image.Image) image.Image {
	if img, ok := sample.(*image.NRGBA64); ok {
		out := image.NewNRGBA64(img.Bounds())
		copy(out.Pix, img.Pix)
		return m.map16(out)
	}
	out := image.NewNRGBA(sample.Bounds())
	draw.Draw(out, out.Bounds(), sample, sample.Bounds().Min, draw.Src)
	return m.map8(out)
}

// Reverse traversal leaves the left and upper neighbors in their original colors.
func (m *PatinaMapping) edge(src image.Image, x, y int) float64 {
	if m.options.Style != "ink" {
		return 0
	}
	luminance := func(x, y int) float64 {
		r, g, b, _ := src.At(x, y).RGBA()
		return (.2126*float64(r) + .7152*float64(g) + .0722*float64(b)) / 65535
	}
	l := luminance(x, y)
	return math.Max(math.Abs(l-luminance(max(0, x-1), y)), math.Abs(l-luminance(x, max(0, y-1))))
}

// PatinaSamples shares one decode between every candidate and its transfer analysis.
func PatinaSamples(data []byte, width, height int, transfer bool) (image.Image, []color.OKLab, error) {
	src, cfg, err := decodeImage(data)
	if err != nil {
		return nil, nil, err
	}
	var groups []color.OKLab
	if transfer {
		groups = TransferGroups(src, cfg.Width, cfg.Height)
	}
	return sampleRaster(src, cfg.Width, cfg.Height, width, height/2), groups, nil
}
