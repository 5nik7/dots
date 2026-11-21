package main

import (
	"encoding/base64"
	"encoding/json"
	"errors"
	"fmt"
	"image"
	"image/color"
	"image/draw"
	"image/gif"
	"image/jpeg"
	"image/png"
	"io"
	"slices"
	"sort"
	"strconv"
	"strings"

	"github.com/5nik7/dots/anodize"
)

type candidate struct {
	anodize.PatinaOptions
	Label  string            `json:"label"`
	Colors map[string]string `json:"colors"`
}

func encode(w io.Writer, r request, img image.Image) error {
	switch r.Format {
	case "", "png":
		return png.Encode(w, img)
	case "jpeg", "bmp":
		flat := image.NewRGBA(img.Bounds())
		draw.Draw(flat, flat.Bounds(), image.NewUniform(hexColor(r.Colors["background"])), image.Point{}, draw.Src)
		draw.Draw(flat, flat.Bounds(), img, img.Bounds().Min, draw.Over)
		if r.Format == "bmp" {
			return png.Encode(w, flat)
		} // staged for Pillow
		return jpeg.Encode(w, flat, &jpeg.Options{Quality: r.Quality})
	case "gif":
		return gif.Encode(w, indexedGIF(img), nil)
	case "svg":
		if _, err := fmt.Fprintf(w, `<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="%d" height="%d"><image width="100%%" height="100%%" xlink:href="data:image/png;base64,`, img.Bounds().Dx(), img.Bounds().Dy()); err != nil {
			return err
		}
		enc := base64.NewEncoder(base64.StdEncoding, w)
		if err := png.Encode(enc, img); err != nil {
			return err
		}
		if err := enc.Close(); err != nil {
			return err
		}
		_, err := io.WriteString(w, `"/></svg>`)
		return err
	default:
		return errors.New("unsupported engine output format")
	}
}

// Keep small palettes exact. For a photographic image use a bounded 6x7x6
// RGB cube with ordered dithering. Encoding then takes linear time per frame.
func indexedGIF(img image.Image) *image.Paletted {
	out := image.NewPaletted(img.Bounds(), color.Palette{color.Transparent})
	indices := map[color.NRGBA]uint8{}
	complete := true
scan:
	for y := range img.Bounds().Dy() {
		for x := range img.Bounds().Dx() {
			pixel := color.NRGBAModel.Convert(img.At(x, y)).(color.NRGBA)
			if pixel.A < 128 {
				continue
			}
			pixel.A = 255
			index, ok := indices[pixel]
			if !ok {
				if len(out.Palette) == 256 {
					complete = false
					break scan
				}
				index = uint8(len(out.Palette))
				out.Palette = append(out.Palette, pixel)
				indices[pixel] = index
			}
			out.SetColorIndex(x, y, index)
		}
	}
	if complete {
		return out
	}
	out.Palette = out.Palette[:1]
	for r := range 6 {
		for g := range 7 {
			for b := range 6 {
				out.Palette = append(out.Palette, color.NRGBA{R: uint8(r * 51), G: uint8((g*255 + 3) / 6), B: uint8(b * 51), A: 255})
			}
		}
	}
	thresholds := [4]int{32, 160, 224, 96}
	for y := range img.Bounds().Dy() {
		for x := range img.Bounds().Dx() {
			p := color.NRGBAModel.Convert(img.At(x, y)).(color.NRGBA)
			index := 0
			if p.A >= 128 {
				bias := thresholds[(y%2)*2+x%2]
				r, g, b := (int(p.R)*5+bias)/255, (int(p.G)*6+bias)/255, (int(p.B)*5+bias)/255
				index = 1 + r*42 + g*6 + b
			}
			out.SetColorIndex(x, y, uint8(index))
		}
	}
	return out
}

func writePatina(w, metadata io.Writer, r request) error {
	var img image.Image
	header := map[string]any{"schema": 1, "patina_version": 2}
	if r.Sheet {
		sheet, err := renderCandidates(r, true)
		if err != nil {
			return err
		}
		img = sheet.canvas
		header["settings"] = r.PatinaOptions
		header["panels"] = sheet.labels
	} else {
		mapping, err := anodize.NewPatinaMapping(r.Palette, r.Colors, r.PatinaOptions)
		if err != nil {
			return err
		}
		img, err = mapping.Render(r.Image)
		if err != nil {
			return err
		}
		header["settings"] = mapping.Settings()
	}
	header["width"], header["height"] = img.Bounds().Dx(), img.Bounds().Dy()
	if r.Columns > 0 && r.Rows > 0 {
		header["thumbnail"] = thumbnail(anodize.PatinaThumbnail(img, r.Columns, r.Rows))
	}
	if err := encode(w, r, img); err != nil {
		return err
	}
	return json.NewEncoder(metadata).Encode(header)
}

func thumbnail(img image.Image) map[string]any {
	pixels, ok := img.(*image.NRGBA)
	if !ok {
		pixels = image.NewNRGBA(img.Bounds())
		draw.Draw(pixels, pixels.Bounds(), img, img.Bounds().Min, draw.Src)
	}
	return map[string]any{"width": pixels.Bounds().Dx(), "pixels": pixels.Pix}
}

func writePatinaPreviews(w io.Writer, r request) error {
	result, err := renderCandidates(r, false)
	if err != nil {
		return err
	}
	return json.NewEncoder(w).Encode(map[string]any{"schema": 1, "thumbnails": result.previews})
}

type candidateRender struct {
	canvas   *image.RGBA
	labels   []string
	previews []map[string]any
}

func hexColor(hex string) color.RGBA {
	v, _ := strconv.ParseUint(strings.TrimPrefix(hex, "#"), 16, 24)
	return color.RGBA{uint8(v >> 16), uint8(v >> 8), uint8(v), 255}
}

func renderCandidates(r request, sheet bool) (candidateRender, error) {
	var result candidateRender
	if len(r.Candidates) == 0 || len(r.Candidates) > 64 {
		return result, errors.New("expected 1 to 64 previews")
	}
	w, h := r.Columns, r.Rows*2
	const tileW, tileH = 288, 198
	if sheet {
		w, h = tileW-16, tileH-44
	}
	transfer := slices.ContainsFunc(r.Candidates, func(c candidate) bool { return c.Style == "color-transfer" })
	ink := slices.ContainsFunc(r.Candidates, func(c candidate) bool { return c.Style == "ink" })
	sample, groups, geometry, err := anodize.PreparePatinaSample(r.Image, w, h, transfer && r.Geometry == nil, ink && r.Geometry == nil)
	if err != nil {
		return result, err
	}
	if r.Geometry != nil {
		groups, geometry = r.TransferGroups, *r.Geometry
	}
	if sheet {
		result.canvas = image.NewRGBA(image.Rect(0, 0, 3*tileW, (len(r.Candidates)+3)/3*tileH))
		draw.Draw(result.canvas, result.canvas.Bounds(), image.NewUniform(color.RGBA{25, 27, 31, 255}), image.Point{}, draw.Src)
		drawTile(result.canvas, image.Rect(0, 0, tileW, tileH), sample, "Original", r.Palette)
		result.labels = append(result.labels, "Original")
	}
	for i, c := range r.Candidates {
		colors, pool := r.Colors, r.Palette
		if len(c.Colors) > 0 {
			colors = c.Colors
			pool = make([]string, 0, len(colors))
			for _, v := range colors {
				pool = append(pool, v)
			}
			sort.Strings(pool)
			pool = slices.Compact(pool)
		}
		mapping, err := anodize.NewPatinaMapping(pool, colors, c.PatinaOptions)
		if err != nil {
			return result, err
		}
		if c.Style == "color-transfer" {
			mapping.SetTransferGroups(groups)
		}
		img, err := mapping.PreviewWithGeometry(sample, geometry)
		if err != nil {
			return result, err
		}
		if sheet {
			x, y := (i+1)%3*tileW, (i+1)/3*tileH
			label := fmt.Sprintf("%02d %s", i+1, c.Label)
			result.labels = append(result.labels, label)
			drawTile(result.canvas, image.Rect(x, y, x+tileW, y+tileH), img, label, pool)
		} else {
			result.previews = append(result.previews, thumbnail(img))
		}
	}
	return result, nil
}

func drawTile(dst *image.RGBA, box image.Rectangle, img image.Image, label string, swatches []string) {
	x, y := box.Min.X+8, box.Min.Y+8
	drawLabel(dst, x, y, label)
	w := box.Dx() - 16
	for i, hex := range swatches {
		r := image.Rect(x+i*w/len(swatches), y+18, x+(i+1)*w/len(swatches), y+26)
		draw.Draw(dst, r, image.NewUniform(hexColor(hex)), image.Point{}, draw.Src)
	}
	at := image.Pt(x+(w-img.Bounds().Dx())/2, y+29+(box.Dy()-44-img.Bounds().Dy())/2)
	draw.Draw(dst, img.Bounds().Add(at), img, img.Bounds().Min, draw.Over)
}

// A fixed 5x7 bitmap alphabet keeps exported sheet labels portable and the engine offline.
var glyphs = map[rune][5]byte{
	'A': {126, 9, 9, 9, 126}, 'B': {127, 73, 73, 73, 54}, 'C': {62, 65, 65, 65, 34}, 'D': {127, 65, 65, 34, 28},
	'E': {127, 73, 73, 73, 65}, 'F': {127, 9, 9, 9, 1}, 'G': {62, 65, 73, 73, 122}, 'H': {127, 8, 8, 8, 127},
	'I': {0, 65, 127, 65, 0}, 'J': {32, 64, 65, 63, 1}, 'K': {127, 8, 20, 34, 65}, 'L': {127, 64, 64, 64, 64},
	'M': {127, 2, 12, 2, 127}, 'N': {127, 4, 8, 16, 127}, 'O': {62, 65, 65, 65, 62}, 'P': {127, 9, 9, 9, 6},
	'Q': {62, 65, 81, 33, 94}, 'R': {127, 9, 25, 41, 70}, 'S': {38, 73, 73, 73, 50}, 'T': {1, 1, 127, 1, 1},
	'U': {63, 64, 64, 64, 63}, 'V': {31, 32, 64, 32, 31}, 'W': {63, 64, 56, 64, 63}, 'X': {99, 20, 8, 20, 99},
	'Y': {3, 4, 120, 4, 3}, 'Z': {97, 81, 73, 69, 67}, '-': {8, 8, 8, 8, 8},
	'0': {62, 81, 73, 69, 62}, '1': {0, 66, 127, 64, 0}, '2': {66, 97, 81, 73, 70}, '3': {34, 65, 73, 73, 54},
	'4': {24, 20, 18, 127, 16}, '5': {39, 69, 69, 69, 57}, '6': {60, 74, 73, 73, 48}, '7': {1, 113, 9, 5, 3},
	'8': {54, 73, 73, 73, 54}, '9': {6, 73, 73, 41, 30},
}

func drawLabel(dst *image.RGBA, x, y int, label string) {
	for _, r := range strings.ToUpper(label) {
		for col, bits := range glyphs[r] {
			for row := range 7 {
				if bits&(1<<row) != 0 {
					draw.Draw(dst, image.Rect(x+2*col, y+2*row, x+2*col+2, y+2*row+2), image.White, image.Point{}, draw.Src)
				}
			}
		}
		x += 12
	}
}
