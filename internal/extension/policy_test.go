package extension

import (
	"errors"
	"os"
	"path/filepath"
	"runtime"
	"syscall"
	"testing"
)

func TestUnavailableUnsupportedAndForeign(t *testing.T) {
	root := t.TempDir()
	writeDefinition(t, root, "probe")
	r := resolver(t, root)
	native := "dots-probe"
	if runtime.GOOS == "windows" {
		native += ".exe"
	}
	if err := os.Remove(filepath.Join(root, native)); err != nil {
		t.Fatal(err)
	}
	d, _, err := r.Lookup([][]string{{"probe"}})
	if err != nil {
		t.Fatal(err)
	}
	kind(t, d.Availability, Unavailable)
	_, err = r.Discover(true)
	kind(t, err, Unavailable)
	if err = os.WriteFile(filepath.Join(root, "dots-probe.cmd"), []byte("inert"), 0600); err != nil {
		t.Fatal(err)
	}
	d, _, err = r.Lookup([][]string{{"probe"}})
	if err != nil {
		t.Fatal(err)
	}
	kind(t, d.Availability, Unsupported)
	m := fixtureMetadata("probe")
	m.Platforms = []string{"wsl"}
	m.Hidden = true
	if err = os.WriteFile(filepath.Join(root, "dots-probe.json"), encode(m), 0600); err != nil {
		t.Fatal(err)
	}
	all, err := r.Discover(true)
	if err != nil || len(all) != 1 || !all[0].Metadata.Hidden || all[0].Availability == nil {
		t.Fatal("foreign definition", err)
	}
	if err = os.Remove(filepath.Join(root, "dots-probe.json")); err != nil {
		t.Fatal(err)
	}
	_, _, err = r.Lookup([][]string{{"probe"}})
	kind(t, err, Unsupported)
}
func TestRootAliasesAndEntrySymlinks(t *testing.T) {
	root := t.TempDir()
	writeDefinition(t, root, "probe")
	alias := filepath.Join(t.TempDir(), "alias")
	if err := os.Symlink(root, alias); err != nil {
		if runtime.GOOS == "windows" && (errors.Is(err, syscall.Errno(5)) || errors.Is(err, syscall.Errno(50)) || errors.Is(err, syscall.Errno(1314))) {
			t.Skipf("fixture symlink unavailable: %v", err)
		}
		t.Fatal(err)
	}
	_, err := New([]string{root, alias}, "linux", NativeAccess())
	kind(t, err, Conflict)
	r := resolver(t, alias)
	if err = os.Rename(filepath.Join(root, "dots-probe.json"), filepath.Join(root, "source.json")); err != nil {
		t.Fatal(err)
	}
	if err = os.Symlink("source.json", filepath.Join(root, "dots-probe.json")); err != nil {
		t.Fatal(err)
	}
	_, _, err = r.Lookup([][]string{{"probe"}})
	kind(t, err, EntryFailure)
	if err = os.Remove(filepath.Join(root, "source.json")); err != nil {
		t.Fatal(err)
	}
	_, _, err = r.Lookup([][]string{{"probe"}})
	kind(t, err, EntryFailure)
}
func TestFilenameCasePolicy(t *testing.T) {
	root := t.TempDir()
	writeDefinition(t, root, "probe")
	r := resolver(t, root)
	// Rename through a distinct spelling to avoid filesystem rename shortcuts.
	native := "dots-probe"
	upper := "DOTS-PROBE"
	if runtime.GOOS == "windows" {
		native += ".exe"
		upper += ".EXE"
	}
	for _, pair := range [][2]string{{"dots-probe.json", "DOTS-PROBE.JSON"}, {native, upper}} {
		if err := os.Rename(filepath.Join(root, pair[0]), filepath.Join(root, "temp")); err != nil {
			t.Fatal(err)
		}
		if err := os.Rename(filepath.Join(root, "temp"), filepath.Join(root, pair[1])); err != nil {
			t.Fatal(err)
		}
	}
	_, _, err := r.Lookup([][]string{{"probe"}})
	if runtime.GOOS == "windows" {
		if err != nil {
			t.Fatal(err)
		}
		all, err := r.Discover(true)
		if err != nil || len(all) != 1 {
			t.Fatal("case identity", err)
		}
	} else {
		kind(t, err, Unknown)
	}
}
