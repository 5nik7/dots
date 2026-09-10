package extension

import (
	"errors"
	"github.com/5nik7/dots/internal/dispatch"
	"github.com/5nik7/dots/internal/platform"
	"io"
	"os"
	"path/filepath"
	"runtime"
	"sort"
	"strings"
)

type Kind string

const (
	RootFailure     Kind = "command directory invalid or inaccessible"
	Conflict        Kind = "external command collision"
	InvalidMetadata Kind = "invalid external metadata"
	EntryFailure    Kind = "command entry invalid or inaccessible"
	Unsupported     Kind = "unsupported external launcher"
	Unavailable     Kind = "external command unavailable on this platform"
	Limit           Kind = "external discovery limit exceeded"
	Unknown         Kind = "unknown command or unsupported arguments"
)

type Error struct{ Kind Kind }

func (e *Error) Error() string { return string(e.Kind) }
func fail(k Kind) error        { return &Error{k} }

// Access permits operation-count tests without coupling pure dispatch to I/O.
type Access struct {
	Root    func(string) (string, os.FileInfo, error)
	File    func(string, bool) (os.FileInfo, error)
	Read    func(string) ([]byte, error)
	Entries func(string) ([]string, error)
}

func NativeAccess() Access {
	return Access{platform.ExtensionRoot, platform.ExtensionFile, readMetadata, entries}
}
func readMetadata(path string) ([]byte, error) {
	f, err := platform.OpenReadOnly(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()
	info, err := f.Stat()
	if err != nil {
		return nil, err
	}
	if !info.Mode().IsRegular() || info.Size() > MaxMetadataBytes {
		return nil, fail(InvalidMetadata)
	}
	data, err := io.ReadAll(io.LimitReader(f, MaxMetadataBytes+1))
	if err != nil {
		return nil, err
	}
	if len(data) > MaxMetadataBytes {
		return nil, fail(InvalidMetadata)
	}
	return data, nil
}
func entries(path string) ([]string, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()
	names, err := f.Readdirnames(MaxEntries + 1)
	if err != nil && err != io.EOF {
		return nil, err
	}
	if len(names) > MaxEntries {
		return nil, fail(Limit)
	}
	sort.Strings(names)
	return names, nil
}

type Resolver struct {
	roots   []string
	access  Access
	target  string
	windows bool
}
type Definition struct {
	Metadata     Metadata
	Path         string
	Availability error
}

func New(paths []string, target string, access Access) (*Resolver, error) {
	if len(paths) > dispatch.MaxCommandRoots {
		return nil, fail(Limit)
	}
	r := &Resolver{access: access, target: target, windows: runtime.GOOS == "windows"}
	infos := []os.FileInfo{}
	for _, path := range paths {
		canonical, info, err := access.Root(path)
		if err != nil {
			return nil, fail(RootFailure)
		}
		for _, old := range infos {
			if os.SameFile(old, info) {
				return nil, fail(Conflict)
			}
		}
		infos = append(infos, info)
		r.roots = append(r.roots, canonical)
	}
	return r, nil
}

var suffixes = []string{".json", "", ".exe", ".cmd", ".bat", ".ps1", ".com", ".sh"}

func (r *Resolver) definition(root, base string) (*Definition, error) {
	present := map[string]bool{}
	for _, suffix := range suffixes {
		_, err := r.access.File(filepath.Join(root, base+suffix), false)
		if err == nil {
			present[suffix] = true
		} else if !errors.Is(err, os.ErrNotExist) {
			return nil, fail(EntryFailure)
		}
	}
	if len(present) == 0 {
		return nil, nil
	}
	native := ""
	if r.windows {
		native = ".exe"
	}
	if !present[".json"] {
		for _, s := range suffixes[3:] {
			if present[s] {
				return nil, fail(Unsupported)
			}
		}
		return nil, fail(InvalidMetadata)
	}
	data, err := r.access.Read(filepath.Join(root, base+".json"))
	if err != nil {
		return nil, fail(InvalidMetadata)
	}
	m, err := Parse(data, base)
	if err != nil {
		return nil, fail(InvalidMetadata)
	}
	if dispatch.Protected(m.Route[0]) {
		return nil, fail(Conflict)
	}
	d := &Definition{Metadata: m, Path: filepath.Join(root, base+native)}
	supported := false
	for _, p := range m.Platforms {
		if p == r.target {
			supported = true
		}
	}
	if !supported || r.target == "wsl" || !(r.target == "termux" || r.target == "linux" || r.target == "windows") {
		d.Availability = fail(Unavailable)
	}
	if !present[native] {
		d.Availability = fail(Unavailable)
		for _, s := range suffixes[3:] {
			if present[s] {
				d.Availability = fail(Unsupported)
			}
		}
	} else if _, err = r.access.File(d.Path, true); err != nil {
		return nil, fail(EntryFailure)
	}
	return d, nil
}

func (r *Resolver) Lookup(candidates [][]string) (*Definition, []string, error) {
	for _, route := range candidates {
		base := "dots-" + strings.Join(route, "-")
		var found *Definition
		for _, root := range r.roots {
			d, err := r.definition(root, base)
			if err != nil {
				return nil, nil, err
			}
			if d != nil {
				if found != nil {
					return nil, nil, fail(Conflict)
				}
				found = d
			}
		}
		if found != nil {
			return found, route, nil
		}
	}
	return nil, nil, fail(Unknown)
}

// Discover enumerates only for an explicit request. No partial result on error.
func (r *Resolver) Discover(check bool) ([]Definition, error) {
	bases := map[string]bool{}
	for _, root := range r.roots {
		names, err := r.access.Entries(root)
		if err != nil {
			var categorized *Error
			if errors.As(err, &categorized) {
				return nil, err
			}
			return nil, fail(RootFailure)
		}
		if len(names) > MaxEntries {
			return nil, fail(Limit)
		}
		for _, name := range names {
			if r.windows {
				name = strings.Map(func(c rune) rune {
					if c >= 'A' && c <= 'Z' {
						return c + ('a' - 'A')
					}
					return c
				}, name)
			}
			if !strings.HasPrefix(name, "dots-") {
				continue
			}
			for _, c := range name {
				if c > 127 {
					return nil, fail(InvalidMetadata)
				}
			}
			base := name
			for _, suffix := range suffixes {
				if suffix != "" && strings.HasSuffix(base, suffix) {
					base = strings.TrimSuffix(base, suffix)
					break
				}
			}
			parts := strings.Split(strings.TrimPrefix(base, "dots-"), "-")
			if len(parts) > dispatch.MaxRouteDepth {
				return nil, fail(InvalidMetadata)
			}
			for _, part := range parts {
				if !dispatch.ExternalSegment(part) {
					return nil, fail(InvalidMetadata)
				}
			}
			bases[base] = true
			if len(bases) > MaxDefinitions {
				return nil, fail(Limit)
			}
		}
	}
	ordered := make([]string, 0, len(bases))
	for base := range bases {
		ordered = append(ordered, base)
	}
	sort.Strings(ordered)
	result := []Definition{}
	for _, base := range ordered {
		route := strings.Split(strings.TrimPrefix(base, "dots-"), "-")
		d, _, err := r.Lookup([][]string{route})
		if err != nil {
			return nil, err
		}
		if check && d.Availability != nil {
			// An intentional foreign-platform declaration is valid but unavailable.
			declared := false
			for _, p := range d.Metadata.Platforms {
				if p == r.target {
					declared = true
				}
			}
			if declared {
				return nil, d.Availability
			}
		}
		result = append(result, *d)
	}
	return result, nil
}
