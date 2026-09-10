package extension

import (
	"errors"
	"fmt"
	"github.com/5nik7/dots/internal/dispatch"
	"os"
	"path/filepath"
	"runtime"
	"testing"
)

func writeDefinition(t *testing.T, root string, route ...string) {
	t.Helper()
	m := fixtureMetadata(route...)
	base := "dots-" + m.Projection().ID
	if err := os.WriteFile(filepath.Join(root, base+".json"), encode(m), 0600); err != nil {
		t.Fatal(err)
	}
	if runtime.GOOS == "windows" {
		base += ".exe"
	}
	if err := os.WriteFile(filepath.Join(root, base), []byte("inert"), 0700); err != nil {
		t.Fatal(err)
	}
}
func resolver(t *testing.T, roots ...string) *Resolver {
	t.Helper()
	target := "linux"
	if runtime.GOOS == "android" {
		target = "termux"
	}
	if runtime.GOOS == "windows" {
		target = "windows"
	}
	r, err := New(roots, target, NativeAccess())
	if err != nil {
		t.Fatal(err)
	}
	return r
}
func kind(t *testing.T, err error, want Kind) {
	t.Helper()
	var e *Error
	if !errors.As(err, &e) || e.Kind != want {
		t.Fatalf("got %v want %s", err, want)
	}
}
func TestTargetedLookupAndCollisions(t *testing.T) {
	root := t.TempDir()
	writeDefinition(t, root, "files")
	writeDefinition(t, root, "files", "list")
	r := resolver(t, root)
	reads, stats := 0, 0
	access := r.access
	r.access.Read = func(p string) ([]byte, error) { reads++; return access.Read(p) }
	r.access.File = func(p string, e bool) (os.FileInfo, error) { stats++; return access.File(p, e) }
	r.access.Entries = func(string) ([]string, error) { t.Fatal("lookup enumerated"); return nil, nil }
	args := []string{"files", "list", "item", "--", "日本語", ""}
	c, _ := dispatch.Candidates(args)
	d, route, err := r.Lookup(c)
	if err != nil || d.Metadata.Projection().ID != "files-list" || len(route) != 2 || reads != 1 || stats > 20 {
		t.Fatal(d, route, err, reads, stats)
	}
	// Unrelated metadata/registry size never changes direct lookup work.
	for i := 0; i < 1000; i++ {
		if err := os.WriteFile(filepath.Join(root, fmt.Sprintf("dots-unused%d.json", i)), []byte("poison"), 0600); err != nil {
			t.Fatal(err)
		}
	}
	reads, stats = 0, 0
	_, _, err = r.Lookup(c)
	if err != nil || reads != 1 || stats > 20 {
		t.Fatal("scale-dependent lookup", err, reads, stats)
	}
	other := t.TempDir()
	writeDefinition(t, other, "files", "list")
	r = resolver(t, root, other)
	_, _, err = r.Lookup(c)
	kind(t, err, Conflict)
	if err = os.WriteFile(filepath.Join(other, "dots-files-list-item.json"), []byte("invalid"), 0600); err != nil {
		t.Fatal(err)
	}
	_, _, err = r.Lookup(c)
	kind(t, err, InvalidMetadata)
}
func TestRootsDiscoveryAndAvailability(t *testing.T) {
	root := t.TempDir()
	_, err := New([]string{root, filepath.Join(root, ".")}, "linux", NativeAccess())
	kind(t, err, Conflict)
	_, err = New([]string{"relative"}, "linux", NativeAccess())
	kind(t, err, RootFailure)
	writeDefinition(t, root, "files")
	r := resolver(t, root)
	got, err := r.Discover(true)
	if err != nil || len(got) != 1 {
		t.Fatal(got, err)
	}
	r.target = "wsl"
	got, err = r.Discover(false)
	if err != nil || got[0].Availability == nil {
		t.Fatal("WSL availability", err)
	}
	writeDefinition(t, root, "doctor", "extra")
	_, err = r.Discover(true)
	kind(t, err, Conflict)
}
func TestUnsafeEntriesAndLimits(t *testing.T) {
	root := t.TempDir()
	writeDefinition(t, root, "files")
	r := resolver(t, root)
	if err := os.Remove(filepath.Join(root, "dots-files.json")); err != nil {
		t.Fatal(err)
	}
	if err := os.Mkdir(filepath.Join(root, "dots-files.json"), 0700); err != nil {
		t.Fatal(err)
	}
	_, _, err := r.Lookup([][]string{{"files"}})
	kind(t, err, EntryFailure)
	r.access.Entries = func(string) ([]string, error) { return make([]string, MaxEntries+1), nil }
	_, err = r.Discover(false)
	kind(t, err, Limit)
	r.access.Entries = func(string) ([]string, error) {
		names := []string{}
		for i := 0; i <= MaxDefinitions; i++ {
			names = append(names, fmt.Sprintf("dots-c%d.json", i))
		}
		return names, nil
	}
	_, err = r.Discover(false)
	kind(t, err, Limit)
}
