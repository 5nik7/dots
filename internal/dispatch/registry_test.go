package dispatch

import (
	"errors"
	"fmt"
	"reflect"
	"testing"
)

func entry(id string, route ...string) Entry {
	return Entry{Metadata: Metadata{ID: id, Route: route, Summary: "Fixture command", Synopsis: id, Examples: []string{"dots " + id}, Platforms: []string{"*"}, Outputs: []Output{{Format: "text"}}, Mutation: "read-only"}, Handler: func([]string) int { return 0 }}
}

func TestCollisionsAndValidation(t *testing.T) {
	tests := []struct {
		name   string
		change func([]Entry) []Entry
	}{
		{"duplicate ID", func(e []Entry) []Entry { e[1].Metadata.ID = "help"; return e }},
		{"duplicate route", func(e []Entry) []Entry { e[1].Metadata.Route = []string{"help"}; return e }},
		{"alias shadows route", func(e []Entry) []Entry { e[1].Metadata.Aliases = [][]string{{"help"}}; return e }},
		{"duplicate alias", func(e []Entry) []Entry { e[1].Metadata.Aliases = [][]string{{"old"}, {"old"}}; return e }},
		{"duplicate option", func(e []Entry) []Entry {
			e[0].Metadata.GlobalOptions = []string{"--help"}
			e[1].Metadata.GlobalOptions = []string{"--help"}
			return e
		}},
		{"duplicate own option", func(e []Entry) []Entry { e[0].Metadata.GlobalOptions = []string{"-h", "-h"}; return e }},
		{"flag as route", func(e []Entry) []Entry { e[1].Metadata.Route = []string{"--version"}; return e }},
		{"whitespace token", func(e []Entry) []Entry { e[1].Metadata.Route = []string{"one two"}; return e }},
		{"empty alias", func(e []Entry) []Entry { e[1].Metadata.Aliases = [][]string{{}}; return e }},
		{"empty route", func(e []Entry) []Entry { e[1].Metadata.Route = nil; return e }},
		{"invalid option", func(e []Entry) []Entry { e[0].Metadata.GlobalOptions = []string{"help"}; return e }},
		{"missing summary", func(e []Entry) []Entry { e[0].Metadata.Summary = ""; return e }},
		{"missing synopsis", func(e []Entry) []Entry { e[0].Metadata.Synopsis = ""; return e }},
		{"missing example", func(e []Entry) []Entry { e[0].Metadata.Examples = nil; return e }},
		{"empty example", func(e []Entry) []Entry { e[0].Metadata.Examples = []string{" "}; return e }},
		{"missing handler", func(e []Entry) []Entry { e[0].Handler = nil; return e }},
		{"missing platforms", func(e []Entry) []Entry { e[0].Metadata.Platforms = nil; return e }},
		{"unknown platform", func(e []Entry) []Entry { e[0].Metadata.Platforms = []string{"android"}; return e }},
		{"mixed wildcard", func(e []Entry) []Entry { e[0].Metadata.Platforms = []string{"*", "linux"}; return e }},
		{"missing outputs", func(e []Entry) []Entry { e[0].Metadata.Outputs = nil; return e }},
		{"unversioned JSON", func(e []Entry) []Entry { e[0].Metadata.Outputs = []Output{{Format: "json"}}; return e }},
		{"duplicate output", func(e []Entry) []Entry {
			e[0].Metadata.Outputs = []Output{{Format: "text"}, {Format: "text"}}
			return e
		}},
		{"unsupported mutation", func(e []Entry) []Entry { e[0].Metadata.Mutation = "apply"; return e }},
		{"duplicate capability", func(e []Entry) []Entry { e[0].Metadata.Capabilities = []string{"copy", "copy"}; return e }},
	}
	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			r, err := New(tc.change([]Entry{entry("help", "help"), entry("doctor", "doctor")}), "help")
			if err == nil || r != nil {
				t.Fatal("invalid table exposed a registry")
			}
		})
	}
	if r, err := New([]Entry{entry("help", "help")}, "absent"); err == nil || r != nil {
		t.Fatal("missing default accepted")
	}
}

func TestResolutionAndArguments(t *testing.T) {
	var got []string
	help := entry("help", "help")
	help.Metadata.GlobalOptions = []string{"-h", "--help"}
	group := entry("files", "files")
	group.Handler = func(args []string) int { got = args; return 11 }
	deep := entry("list", "files", "list")
	deep.Metadata.Aliases = [][]string{{"old", "list"}}
	deep.Handler = func(args []string) int { got = args; return 12 }
	version := entry("version")
	version.Metadata.GlobalOptions = []string{"--version"}
	r, err := New([]Entry{help, group, deep, version}, "help")
	if err != nil {
		t.Fatal(err)
	}
	for _, tc := range []struct {
		args []string
		code int
		rest []string
	}{
		{[]string{"files", "list", "space here", "日本語", "-leading", "--", "TOP_SECRET"}, 12, []string{"space here", "日本語", "-leading", "--", "TOP_SECRET"}},
		{[]string{"files", "listing"}, 11, []string{"listing"}},
		{[]string{"old", "list", "x"}, 12, []string{"x"}},
	} {
		saved := append([]string(nil), tc.args...)
		f, args, err := r.Resolve(tc.args, "linux", nil)
		if err != nil || f(args) != tc.code || !reflect.DeepEqual(got, tc.rest) || !reflect.DeepEqual(saved, tc.args) {
			t.Fatalf("resolution/arguments changed: %v", err)
		}
	}
	for _, args := range [][]string{nil, {}, {"-h"}, {"--help"}, {"help"}, {"--version"}} {
		f, rest, err := r.Resolve(args, "unknown", nil)
		if err != nil || f == nil || len(rest) != 0 {
			t.Fatal("global/default lost", err)
		}
	}
	for _, args := range [][]string{{"version"}, {"files-list"}, {"files list"}, {"--unknown"}} {
		if f, _, err := r.Resolve(args, "linux", nil); !errors.Is(err, ErrUnknown) || f != nil {
			t.Fatal("unknown accepted")
		}
	}
}

func TestAvailabilityAndProjectionIsolation(t *testing.T) {
	e := entry("help", "help")
	e.Metadata.GlobalOptions = []string{"-h"}
	e.Metadata.Aliases = [][]string{{"old"}}
	e.Metadata.Platforms = []string{"windows"}
	e.Metadata.Capabilities = []string{"copy"}
	e.Metadata.Outputs = append(e.Metadata.Outputs, Output{Format: "json", SchemaVersion: 1})
	r, err := New([]Entry{e}, "help")
	if err != nil {
		t.Fatal(err)
	}
	baseline := r.Project()
	// Mutating inputs and every projected slice must not change validation/lookup.
	e.Metadata.Route[0] = "corrupt"
	projection := r.Project()
	projection[0].Aliases[0][0] = "changed"
	projection[0].GlobalOptions[0] = "--changed"
	projection[0].Examples[0] = "changed"
	projection[0].Platforms[0] = "*"
	projection[0].Capabilities[0] = "other"
	projection[0].Outputs[0].Format = "changed"
	projection[0].Route[0] = "changed"
	if !reflect.DeepEqual(baseline, r.Project()) {
		t.Fatal("projection exposed mutable registry state")
	}
	for _, tc := range []struct {
		platform string
		caps     map[string]bool
		want     error
	}{
		{"linux", map[string]bool{"copy": true}, ErrUnavailable}, {"windows", nil, ErrUnavailable}, {"windows", map[string]bool{"copy": true}, nil},
	} {
		f, _, err := r.Resolve([]string{"help"}, tc.platform, tc.caps)
		if !errors.Is(err, tc.want) || (err != nil && f != nil) {
			t.Fatalf("availability: %v", err)
		}
	}
	if _, _, err := r.Resolve([]string{"absent"}, "linux", nil); !errors.Is(err, ErrUnknown) {
		t.Fatal("unavailable confused with unknown")
	}
}

func BenchmarkRegistryLookup(b *testing.B) {
	for _, size := range []int{3, 1000, 10000} {
		b.Run(fmt.Sprintf("entries-%d", size), func(b *testing.B) {
			entries := make([]Entry, size)
			for i := range entries {
				name := fmt.Sprintf("route%d", i)
				entries[i] = entry(name, name)
			}
			r, err := New(entries, "route0")
			if err != nil {
				b.Fatal(err)
			}
			args := []string{fmt.Sprintf("route%d", size-1), "argument"}
			b.ReportAllocs()
			b.ResetTimer()
			for i := 0; i < b.N; i++ {
				f, rest, err := r.Resolve(args, "linux", nil)
				if err != nil || len(rest) != 1 || f == nil {
					b.Fatal("lookup failed")
				}
			}
		})
	}
}
