// Private bounded JSON transport for the Dots CLI adapter.
package main

import (
	"encoding/json"
	"fmt"
	"github.com/5nik7/dots/anodize"
	"io"
	"os"
)

type request struct {
	Schema   int              `json:"schema"`
	Action   string           `json:"action"`
	Image    []byte           `json:"image,omitempty"`
	Color    string           `json:"color,omitempty"`
	Options  anodize.Options  `json:"options"`
	Document anodize.Document `json:"document"`
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
	case "modes":
		out["modes"] = anodize.Modes()
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
