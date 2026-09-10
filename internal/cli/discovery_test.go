package cli

import (
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"reflect"
	"strings"
	"testing"

	"github.com/5nik7/dots/internal/dispatch"
	"github.com/5nik7/dots/internal/extension"
)

func TestCatalogContract(t *testing.T) {
	var out, stderr bytes.Buffer
	panicProvider := func() string { t.Fatal("catalog read logo"); return "" }
	if code := Run([]string{"commands", "--json"}, &out, &stderr, panicProvider, nil); code != 0 || stderr.Len() != 0 {
		t.Fatal(code, stderr.String())
	}
	var envelope map[string]json.RawMessage
	if err := json.Unmarshal(out.Bytes(), &envelope); err != nil {
		t.Fatal(err)
	}
	if len(envelope) != 2 || string(envelope["schema_version"]) != "1" {
		t.Fatal(out.String())
	}
	var records []map[string]json.RawMessage
	if err := json.Unmarshal(envelope["commands"], &records); err != nil {
		t.Fatal(err)
	}
	wantIDs := []string{"commands", "doctor", "help", "version"}
	keys := strings.Fields("kind id route global_options aliases summary synopsis examples platforms capabilities hidden outputs mutation availability")
	for i, record := range records {
		if len(record) != len(keys) {
			t.Fatal("record fields", record)
		}
		for _, key := range keys {
			if _, ok := record[key]; !ok {
				t.Fatal("missing", key)
			}
		}
		if string(record["id"]) != fmt.Sprintf("%q", wantIDs[i]) || string(record["kind"]) != `"builtin"` {
			t.Fatal(record)
		}
		for _, key := range []string{"route", "global_options", "aliases", "examples", "platforms", "capabilities", "outputs"} {
			if !bytes.HasPrefix(record[key], []byte("[")) {
				t.Fatal("non-array", key)
			}
		}
		for _, key := range []string{"summary", "synopsis", "mutation"} {
			var s string
			if json.Unmarshal(record[key], &s) != nil || s == "" {
				t.Fatal("non-string", key)
			}
		}
		if string(record["hidden"]) != "false" {
			t.Fatal("hidden", record)
		}
		var availability map[string]json.RawMessage
		if json.Unmarshal(record["availability"], &availability) != nil || len(availability) != 2 || string(availability["status"]) != `"available"` || string(availability["reason"]) != "null" {
			t.Fatal("availability", record)
		}
	}
	if len(records) != 4 || string(records[3]["route"]) != "[]" || !bytes.Contains(records[3]["global_options"], []byte(`"--version"`)) {
		t.Fatal("global-only version")
	}
	var outputs []catalogOutput
	if json.Unmarshal(records[0]["outputs"], &outputs) != nil || !reflect.DeepEqual(outputs, []catalogOutput{{"json", 1}, {"text", 0}}) {
		t.Fatal("self-description", outputs)
	}
	if !strings.HasSuffix(out.String(), "\n") || strings.ContainsAny(out.String(), "\x1b") {
		t.Fatal("decoration")
	}
	var again bytes.Buffer
	if Run([]string{"commands", "--json"}, &again, &stderr, nil, nil) != 0 || out.String() != again.String() {
		t.Fatal("unstable")
	}
}

func TestCatalogProjectionIsolation(t *testing.T) {
	m := dispatch.Metadata{ID: "z", Route: []string{"z", "a"}, GlobalOptions: []string{"--z", "--a"}, Aliases: [][]string{{"z"}, {"a", "b"}, {"a"}}, Summary: `Unicode 日本語 "quotes" <tag>`, Synopsis: "z", Examples: []string{"second", "first"}, Platforms: []string{"windows", "linux"}, Capabilities: []string{"z", "a"}, Outputs: []dispatch.Output{{Format: "text"}, {Format: "json", SchemaVersion: 7}}, Hidden: true, Mutation: "read-only"}
	before, _ := json.Marshal(m)
	got, err := projectCatalog(m, "builtin", nil)
	if err != nil {
		t.Fatal(err)
	}
	if !reflect.DeepEqual(got.Aliases, [][]string{{"a"}, {"a", "b"}, {"z"}}) || !reflect.DeepEqual(got.Route, m.Route) || !reflect.DeepEqual(got.Examples, m.Examples) || !reflect.DeepEqual(got.Platforms, []string{"linux", "windows"}) || !reflect.DeepEqual(got.Capabilities, []string{"a", "z"}) || !reflect.DeepEqual(got.GlobalOptions, []string{"--a", "--z"}) || got.Outputs[0].Format != "json" || !got.Hidden {
		t.Fatal(got)
	}
	data, _ := json.Marshal(got)
	var roundtrip catalogCommand
	if json.Unmarshal(data, &roundtrip) != nil || roundtrip.Summary != m.Summary {
		t.Fatal("escaping")
	}
	got.Route[0] = "changed"
	got.Aliases[0][0] = "changed"
	got.Examples[0] = "changed"
	got.Platforms[0] = "changed"
	got.Capabilities[0] = "changed"
	got.GlobalOptions[0] = "changed"
	got.Outputs[0].Format = "changed"
	after, _ := json.Marshal(m)
	if !bytes.Equal(before, after) {
		t.Fatal("mutated shared metadata")
	}
	for _, tc := range []struct {
		err    error
		reason string
	}{{&extension.Error{Kind: extension.Unavailable}, "unavailable"}, {fmt.Errorf("wrapped: %w", &extension.Error{Kind: extension.Unsupported}), "unsupported_launcher"}} {
		c, err := projectCatalog(m, "external", tc.err)
		if err != nil || c.Availability.Status != "unavailable" || c.Availability.Reason == nil || *c.Availability.Reason != tc.reason {
			t.Fatal(c, err)
		}
	}
	for _, err := range []error{errors.New(string(extension.Unavailable)), &extension.Error{Kind: extension.EntryFailure}} {
		if _, err := projectCatalog(m, "external", err); err == nil {
			t.Fatal("accepted untyped/unexpected availability")
		}
	}
}

func TestCatalogExternalOrder(t *testing.T) {
	r, err := registry(io.Discard, io.Discard, nil, nil)
	if err != nil {
		t.Fatal(err)
	}
	defs := []extension.Definition{{Metadata: extension.Metadata{Route: []string{"z"}, Hidden: true}, Path: "SECRET"}, {Metadata: extension.Metadata{Route: []string{"files", "list"}}, Availability: &extension.Error{Kind: extension.Unavailable}}}
	a, err := encodeCatalog(r, defs)
	if err != nil {
		t.Fatal(err)
	}
	defs[0], defs[1] = defs[1], defs[0]
	b, err := encodeCatalog(r, defs)
	if err != nil || !bytes.Equal(a, b) || bytes.Contains(a, []byte("SECRET")) {
		t.Fatal("ordering or path leak", err)
	}
	var c catalog
	if json.Unmarshal(a, &c) != nil || len(c.Commands) != 6 || c.Commands[4].ID != "files-list" || !c.Commands[5].Hidden {
		t.Fatal("missing hidden/ID", string(a))
	}
}

type catalogFailWriter struct{ short bool }

func (w catalogFailWriter) Write(p []byte) (int, error) {
	if w.short {
		return len(p) - 1, nil
	}
	return 0, errors.New("SECRET")
}
func TestCatalogErrors(t *testing.T) {
	args := [][]string{{"commands", "--json", "--check"}, {"commands", "--check", "--json"}, {"commands", "--json", "--json"}, {"commands", "--json", "--help"}, {"commands", "--json", "--"}, {"commands", "--json", "SECRET"}, {"--command-dir"}, {"--command-dir", "", "commands", "--json"}}
	over := []string{}
	for i := 0; i <= dispatch.MaxCommandRoots; i++ {
		over = append(over, "--command-dir", "/SECRET")
	}
	args = append(args, append(over, "commands", "--json"))
	for _, argv := range args {
		var out, stderr bytes.Buffer
		if code := Run(argv, &out, &stderr, nil, nil); code != 2 || out.Len() != 0 || stderr.Len() == 0 || strings.Contains(stderr.String(), "SECRET") {
			t.Fatal(argv, code, out.String(), stderr.String())
		}
	}
	for _, w := range []catalogFailWriter{{false}, {true}} {
		var stderr bytes.Buffer
		if code := Run([]string{"commands", "--json"}, w, &stderr, nil, nil); code != 1 || stderr.String() != "dots: command catalog output failed\n" {
			t.Fatal(code, stderr.String())
		}
	}
}
