// Private bounded JSON transport for the Dots CLI adapter.
package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"image/png"
	"io"
	"maps"
	"os"

	"github.com/5nik7/dots/anodize"
	"github.com/5nik7/dots/anodize/color"
)

type request struct {
	IncludeBaselines bool                    `json:"include_baselines,omitempty"`
	Geometry         *anodize.PatinaGeometry `json:"geometry,omitempty"`
	SampleInk        bool                    `json:"sample_ink,omitempty"`
	TransferGroups   []color.OKLab           `json:"transfer_groups,omitempty"`
	Modes            []string                `json:"modes,omitempty"`
	Palette          []string                `json:"palette,omitempty"`
	anodize.PatinaOptions
	Colors     map[string]string `json:"colors,omitempty"`
	Format     string            `json:"format"`
	Quality    int               `json:"quality"`
	Rendered   bool              `json:"rendered,omitempty"`
	Sheet      bool              `json:"sheet"`
	Candidates []candidate       `json:"candidates,omitempty"`
	Columns    int               `json:"columns,omitempty"`
	Rows       int               `json:"rows,omitempty"`
	Schema     int               `json:"schema"`
	Action     string            `json:"action"`
	Image      []byte            `json:"image,omitempty"`
	Color      string            `json:"color,omitempty"`
	Options    anodize.Options   `json:"options"`
	Document   anodize.Document  `json:"document"`
}

func run() error {
	data, err := io.ReadAll(io.LimitReader(os.Stdin, 48<<20+1))
	if err != nil {
		return err
	}
	if len(data) > 48<<20 {
		return fmt.Errorf("request exceeds 48 MiB")
	}
	var r request
	if err = json.Unmarshal(data, &r); err != nil {
		return fmt.Errorf("invalid engine request")
	}
	if r.Schema != 1 {
		return fmt.Errorf("unsupported request schema")
	}
	out := map[string]any{"schema": 1}
	switch r.Action {
	case "patina-sample":
		sample, groups, geometry, err := anodize.PreparePatinaSample(r.Image, r.Columns, r.Rows*2, r.Style == "color-transfer", r.SampleInk)
		if err != nil {
			return err
		}
		var encoded bytes.Buffer
		if err := png.Encode(&encoded, sample); err != nil {
			return err
		}
		out["image"], out["transfer_groups"], out["geometry"] = encoded.Bytes(), groups, geometry
	case "patina-previews":
		return writePatinaPreviews(os.Stdout, r)
	case "patina":
		return writePatina(os.Stdout, os.Stderr, r)
	case "modes":
		out["modes"] = anodize.Modes()
		out["descriptions"] = anodize.ModeDescriptions()
	case "generate-modes":
		palettes, err := anodize.GenerateModes(r.Image, r.Color, r.Colors, r.Modes, r.Options.Light)
		if err != nil {
			return err
		}
		if r.IncludeBaselines {
			out["baselines"] = maps.Clone(palettes)
		}
		if r.Rendered {
			for mode, baseline := range palettes {
				doc := anodize.Document{Schema: 1, Baseline: baseline, Options: anodize.Options{Mode: mode, Light: r.Options.Light}, Adjustments: r.Document.Adjustments, Overrides: r.Document.Overrides}
				palettes[mode], err = anodize.Render(doc)
				if err != nil {
					return err
				}
			}
		}
		out["palettes"] = palettes
	case "generate":
		colors, e := anodize.Generate(r.Image, r.Color, r.Options)
		if e != nil {
			return e
		}
		out["colors"] = colors
	case "render":
		colors, e := anodize.Render(r.Document)
		if e != nil {
			return e
		}
		out["colors"] = colors
		out["contrast"] = anodize.Contrast(colors)
	case "variant":
		colors, e := anodize.Variant(r.Document)
		if e != nil {
			return e
		}
		out["colors"] = colors
	default:
		return fmt.Errorf("unknown engine action")
	}
	return json.NewEncoder(os.Stdout).Encode(out)
}
func main() {
	if err := run(); err != nil {
		fmt.Fprintln(os.Stderr, "anodize:", err)
		os.Exit(1)
	}
}
