// Package dispatch validates and resolves built-ins entirely in memory.
// It has no filesystem, environment, process, or platform-collection dependency.
package dispatch

import (
	"errors"
	"strings"
)

var (
	ErrUnknown     = errors.New("unknown command")
	ErrUnavailable = errors.New("command unavailable on this platform")
)

type Output struct {
	Format        string
	SchemaVersion int
}

// Metadata is a private-core contract, not an external metadata carrier or API.
// A global-only entry has no Route; global options never become route tokens.
type Metadata struct {
	ID            string
	Route         []string
	GlobalOptions []string
	Aliases       [][]string
	Summary       string
	Synopsis      string
	Examples      []string
	Platforms     []string
	Capabilities  []string
	Hidden        bool
	Outputs       []Output
	Mutation      string
}

type Handler func([]string) int

type Entry struct {
	Metadata Metadata
	Handler  Handler
}

type node struct {
	children map[string]*node
	entry    *Entry
}

type Registry struct {
	root         node
	globals      map[string]*Entry
	entries      []Entry
	defaultEntry *Entry
}

func token(s string) bool {
	if s == "" || s[0] == '-' {
		return false
	}
	for _, c := range s {
		if !(c >= 'a' && c <= 'z' || c >= '0' && c <= '9' || c == '-') {
			return false
		}
	}
	return true
}

func clone(m Metadata) Metadata {
	m.Route = append([]string(nil), m.Route...)
	m.GlobalOptions = append([]string(nil), m.GlobalOptions...)
	aliases := make([][]string, len(m.Aliases))
	for i, a := range m.Aliases {
		aliases[i] = append([]string(nil), a...)
	}
	m.Aliases = aliases
	m.Examples = append([]string(nil), m.Examples...)
	m.Platforms = append([]string(nil), m.Platforms...)
	m.Capabilities = append([]string(nil), m.Capabilities...)
	m.Outputs = append([]Output(nil), m.Outputs...)
	return m
}

// New validates the entire table before exposing any handler. Errors deliberately
// omit supplied metadata, which could later originate in a sensitive source.
func New(entries []Entry, defaultID string) (*Registry, error) {
	r := &Registry{root: node{children: map[string]*node{}}, globals: map[string]*Entry{}, entries: make([]Entry, len(entries))}
	invalid := func() (*Registry, error) { return nil, errors.New("invalid or duplicate built-in metadata") }
	ids := map[string]bool{}
	for i, entry := range entries {
		m := entry.Metadata
		if !token(m.ID) || ids[m.ID] || entry.Handler == nil || strings.TrimSpace(m.Summary) == "" || strings.ContainsAny(m.Summary, "\r\n\x1b") || strings.TrimSpace(m.Synopsis) == "" || len(m.Examples) == 0 || len(m.Platforms) == 0 || len(m.Outputs) == 0 || m.Mutation != "read-only" {
			return invalid()
		}
		if len(m.Route) == 0 && len(m.GlobalOptions) == 0 {
			return invalid()
		}
		for _, example := range m.Examples {
			if strings.TrimSpace(example) == "" {
				return invalid()
			}
		}
		platforms := map[string]bool{}
		for _, p := range m.Platforms {
			if platforms[p] || !(p == "*" || p == "termux" || p == "linux" || p == "windows" || p == "wsl") {
				return invalid()
			}
			platforms[p] = true
		}
		if platforms["*"] && len(platforms) != 1 {
			return invalid()
		}
		caps := map[string]bool{}
		for _, cap := range m.Capabilities {
			if !token(cap) || caps[cap] {
				return invalid()
			}
			caps[cap] = true
		}
		formats := map[string]bool{}
		for _, output := range m.Outputs {
			if formats[output.Format] || !(output.Format == "text" && output.SchemaVersion == 0 || output.Format == "json" && output.SchemaVersion > 0) {
				return invalid()
			}
			formats[output.Format] = true
		}
		ids[m.ID] = true
		r.entries[i] = Entry{clone(m), entry.Handler}
	}
	for i := range r.entries {
		entry := &r.entries[i]
		m := entry.Metadata
		if m.ID == defaultID {
			r.defaultEntry = entry
		}
		routes := m.Aliases
		if len(m.Route) > 0 {
			routes = append(append([][]string(nil), routes...), m.Route)
		}
		for _, route := range routes {
			if len(route) == 0 {
				return invalid()
			}
			current := &r.root
			for _, part := range route {
				if !token(part) {
					return invalid()
				}
				if current.children[part] == nil {
					current.children[part] = &node{children: map[string]*node{}}
				}
				current = current.children[part]
			}
			if current.entry != nil {
				return invalid()
			}
			current.entry = entry
		}
		for _, option := range m.GlobalOptions {
			name := strings.TrimPrefix(strings.TrimPrefix(option, "-"), "-")
			if !strings.HasPrefix(option, "-") || !token(name) || r.globals[option] != nil {
				return invalid()
			}
			r.globals[option] = entry
		}
	}
	if r.defaultEntry == nil {
		return invalid()
	}
	return r, nil
}

// Project returns an ordered, defensive copy for help and future renderers.
// It does not enumerate directories or invoke a handler/metadata handshake.
func (r *Registry) Project() []Metadata {
	result := make([]Metadata, len(r.entries))
	for i, entry := range r.entries {
		result[i] = clone(entry.Metadata)
	}
	return result
}

// Resolve prefers the deepest exact built-in token route. Remaining arguments
// retain their original bytes and order, including flags, spaces and Unicode.
// Availability is injected; resolution never probes the machine.
func (r *Registry) Resolve(args []string, platform string, capabilities map[string]bool) (Handler, []string, error) {
	var selected *Entry
	used := 0
	if len(args) == 0 {
		selected = r.defaultEntry
	} else if entry := r.globals[args[0]]; entry != nil {
		selected = entry
		used = 1
	} else {
		current := &r.root
		for i, arg := range args {
			next := current.children[arg]
			if next == nil {
				break
			}
			current = next
			if current.entry != nil {
				selected = current.entry
				used = i + 1
			}
		}
	}
	if selected == nil {
		return nil, nil, ErrUnknown
	}
	available := false
	for _, p := range selected.Metadata.Platforms {
		if p == "*" || p == platform {
			available = true
			break
		}
	}
	for _, cap := range selected.Metadata.Capabilities {
		if !capabilities[cap] {
			available = false
		}
	}
	if !available {
		return nil, nil, ErrUnavailable
	}
	return selected.Handler, args[used:], nil
}
