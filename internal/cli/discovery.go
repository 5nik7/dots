package cli

import (
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"slices"

	"github.com/5nik7/dots/internal/dispatch"
	"github.com/5nik7/dots/internal/extension"
)

// Catalog types are the public wire contract, independent of private carriers.
type catalog struct {
	SchemaVersion int              `json:"schema_version"`
	Commands      []catalogCommand `json:"commands"`
}
type catalogOutput struct {
	Format        string `json:"format"`
	SchemaVersion int    `json:"schema_version"`
}
type catalogAvailability struct {
	Status string  `json:"status"`
	Reason *string `json:"reason"`
}
type catalogCommand struct {
	Kind          string              `json:"kind"`
	ID            string              `json:"id"`
	Route         []string            `json:"route"`
	GlobalOptions []string            `json:"global_options"`
	Aliases       [][]string          `json:"aliases"`
	Summary       string              `json:"summary"`
	Synopsis      string              `json:"synopsis"`
	Examples      []string            `json:"examples"`
	Platforms     []string            `json:"platforms"`
	Capabilities  []string            `json:"capabilities"`
	Hidden        bool                `json:"hidden"`
	Outputs       []catalogOutput     `json:"outputs"`
	Mutation      string              `json:"mutation"`
	Availability  catalogAvailability `json:"availability"`
}

func catalogStrings(values []string, sorted bool) []string {
	result := append([]string{}, values...)
	if sorted {
		slices.Sort(result)
	}
	return result
}
func projectCatalog(m dispatch.Metadata, kind string, unavailable error) (catalogCommand, error) {
	availability := catalogAvailability{Status: "available"}
	if unavailable != nil {
		var category *extension.Error
		if !errors.As(unavailable, &category) {
			return catalogCommand{}, errors.New("unexpected catalog availability")
		}
		reason := ""
		switch category.Kind {
		case extension.Unavailable:
			reason = "unavailable"
		case extension.Unsupported:
			reason = "unsupported_launcher"
		default:
			return catalogCommand{}, errors.New("unexpected catalog availability")
		}
		availability = catalogAvailability{Status: "unavailable", Reason: &reason}
	}
	aliases := make([][]string, len(m.Aliases))
	for i, route := range m.Aliases {
		aliases[i] = catalogStrings(route, false)
	}
	slices.SortFunc(aliases, func(a, b []string) int { return slices.Compare(a, b) })
	outputs := make([]catalogOutput, len(m.Outputs))
	for i, o := range m.Outputs {
		outputs[i] = catalogOutput{o.Format, o.SchemaVersion}
	}
	slices.SortFunc(outputs, func(a, b catalogOutput) int { return compareString(a.Format, b.Format) })
	return catalogCommand{Kind: kind, ID: m.ID, Route: catalogStrings(m.Route, false), GlobalOptions: catalogStrings(m.GlobalOptions, true), Aliases: aliases, Summary: m.Summary, Synopsis: m.Synopsis, Examples: catalogStrings(m.Examples, false), Platforms: catalogStrings(m.Platforms, true), Capabilities: catalogStrings(m.Capabilities, true), Hidden: m.Hidden, Outputs: outputs, Mutation: m.Mutation, Availability: availability}, nil
}
func compareString(a, b string) int {
	if a < b {
		return -1
	}
	if a > b {
		return 1
	}
	return 0
}
func encodeCatalog(r *dispatch.Registry, definitions []extension.Definition) ([]byte, error) {
	result := catalog{SchemaVersion: 1, Commands: []catalogCommand{}}
	for _, m := range r.Project() {
		c, err := projectCatalog(m, "builtin", nil)
		if err != nil {
			return nil, err
		}
		result.Commands = append(result.Commands, c)
	}
	for _, d := range definitions {
		c, err := projectCatalog(d.Metadata.Projection(), "external", d.Availability)
		if err != nil {
			return nil, err
		}
		result.Commands = append(result.Commands, c)
	}
	slices.SortFunc(result.Commands, func(a, b catalogCommand) int {
		if c := compareString(a.Kind, b.Kind); c != 0 {
			return c
		}
		return compareString(a.ID, b.ID)
	})
	data, err := json.MarshalIndent(result, "", "  ")
	if err != nil {
		return nil, err
	}
	return append(data, '\n'), nil
}
func commandListing(out, errOut io.Writer, r *dispatch.Registry, definitions []extension.Definition, args []string) int {
	if len(args) == 1 && args[0] == "--json" {
		data, err := encodeCatalog(r, definitions)
		if err == nil {
			var n int
			n, err = out.Write(data)
			if err == nil && n != len(data) {
				err = io.ErrShortWrite
			}
		}
		if err != nil {
			fmt.Fprintln(errOut, "dots: command catalog output failed")
			return 1
		}
		return 0
	}
	return commandList(out, r, definitions, len(args) == 1 && args[0] == "--check")
}
