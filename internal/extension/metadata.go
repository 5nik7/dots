// Package extension resolves explicitly trusted command definitions. It does not
// execute code during lookup, metadata validation, help or discovery.
package extension

import (
	"bytes"
	"encoding/json"
	"errors"
	"github.com/5nik7/dots/internal/dispatch"
	"io"
	"strings"
	"unicode"
	"unicode/utf8"
)

const MaxMetadataBytes = 65536
const MaxDisplayBytes = 1024
const MaxExamples = 16
const MaxEntries = 4096
const MaxDefinitions = 1024

type Output struct {
	Format        string `json:"format"`
	SchemaVersion int    `json:"schema_version"`
}
type Metadata struct {
	SchemaVersion int      `json:"schema_version"`
	Route         []string `json:"route"`
	Summary       string   `json:"summary"`
	Synopsis      string   `json:"synopsis"`
	Examples      []string `json:"examples"`
	Platforms     []string `json:"platforms"`
	Hidden        bool     `json:"hidden"`
	Outputs       []Output `json:"outputs"`
	Mutation      string   `json:"mutation"`
	Aliases       []string `json:"aliases"`
	Capabilities  []string `json:"capabilities"`
}

func display(s string) bool {
	if strings.TrimSpace(s) == "" || len(s) > MaxDisplayBytes {
		return false
	}
	for _, r := range s {
		if unicode.IsControl(r) || unicode.Is(unicode.Cf, r) || r == utf8.RuneError || r == '\u2028' || r == '\u2029' {
			return false
		}
	}
	return true
}

// Walk tokens before decoding: encoding/json otherwise accepts duplicate keys.
func strictValue(d *json.Decoder, depth int) error {
	if depth > 16 {
		return errors.New("JSON nesting limit")
	}
	tok, err := d.Token()
	if err != nil {
		return err
	}
	if tok == nil {
		return errors.New("null metadata value")
	}
	delimiter, ok := tok.(json.Delim)
	if !ok {
		return nil
	}
	switch delimiter {
	case '{':
		keys := map[string]bool{}
		for d.More() {
			key, err := d.Token()
			if err != nil {
				return err
			}
			s, ok := key.(string)
			if !ok || keys[s] {
				return errors.New("duplicate JSON key")
			}
			keys[s] = true
			if err = strictValue(d, depth+1); err != nil {
				return err
			}
		}
	case '[':
		for d.More() {
			if err := strictValue(d, depth+1); err != nil {
				return err
			}
		}
	default:
		return errors.New("invalid JSON delimiter")
	}
	_, err = d.Token()
	return err
}

func Parse(data []byte, basename string) (Metadata, error) {
	var m Metadata
	invalid := func() (Metadata, error) { return Metadata{}, errors.New("invalid external metadata") }
	if len(data) > MaxMetadataBytes || !utf8.Valid(data) {
		return invalid()
	}
	d := json.NewDecoder(bytes.NewReader(data))
	if strictValue(d, 0) != nil {
		return invalid()
	}
	if _, err := d.Token(); err != io.EOF {
		return invalid()
	}
	var fields map[string]json.RawMessage
	if json.Unmarshal(data, &fields) != nil || len(fields) != 11 {
		return invalid()
	}
	for _, key := range []string{"schema_version", "route", "summary", "synopsis", "examples", "platforms", "hidden", "outputs", "mutation", "aliases", "capabilities"} {
		if _, ok := fields[key]; !ok {
			return invalid()
		}
	}
	var outputFields []map[string]json.RawMessage
	if json.Unmarshal(fields["outputs"], &outputFields) != nil {
		return invalid()
	}
	for _, o := range outputFields {
		if len(o) != 2 || o["format"] == nil || o["schema_version"] == nil {
			return invalid()
		}
	}
	d = json.NewDecoder(bytes.NewReader(data))
	d.DisallowUnknownFields()
	if d.Decode(&m) != nil {
		return invalid()
	}
	if m.SchemaVersion != 1 || len(m.Route) == 0 || len(m.Route) > dispatch.MaxRouteDepth || "dots-"+strings.Join(m.Route, "-") != basename || !display(m.Summary) || !display(m.Synopsis) || len(m.Examples) == 0 || len(m.Examples) > MaxExamples || m.Mutation != "read-only" || len(m.Aliases) != 0 || len(m.Capabilities) != 0 {
		return invalid()
	}
	for _, part := range m.Route {
		if !dispatch.ExternalSegment(part) {
			return invalid()
		}
	}
	for _, example := range m.Examples {
		if !display(example) {
			return invalid()
		}
	}
	platforms := map[string]bool{}
	for _, p := range m.Platforms {
		if platforms[p] || !(p == "termux" || p == "linux" || p == "windows" || p == "wsl") {
			return invalid()
		}
		platforms[p] = true
	}
	if len(platforms) == 0 || len(m.Outputs) == 0 {
		return invalid()
	}
	formats := map[string]bool{}
	for _, o := range m.Outputs {
		if formats[o.Format] || !(o.Format == "text" && o.SchemaVersion == 0 || o.Format == "json" && o.SchemaVersion > 0) {
			return invalid()
		}
		formats[o.Format] = true
	}
	return m, nil
}

func (m Metadata) Projection() dispatch.Metadata {
	outputs := make([]dispatch.Output, len(m.Outputs))
	for i, o := range m.Outputs {
		outputs[i] = dispatch.Output{Format: o.Format, SchemaVersion: o.SchemaVersion}
	}
	return dispatch.Metadata{ID: strings.Join(m.Route, "-"), Route: append([]string{}, m.Route...), Summary: m.Summary, Synopsis: m.Synopsis, Examples: append([]string{}, m.Examples...), Platforms: append([]string{}, m.Platforms...), Hidden: m.Hidden, Outputs: outputs, Mutation: m.Mutation}
}
