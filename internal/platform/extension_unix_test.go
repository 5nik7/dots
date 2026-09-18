//go:build unix

package platform

import (
	"os"
	"path/filepath"
	"syscall"
	"testing"
)

func TestExtensionUnixEntryTypes(t *testing.T) {
	root := t.TempDir()
	p := filepath.Join(root, "payload")
	if err := os.WriteFile(p, []byte("inert"), 0600); err != nil {
		t.Fatal(err)
	}
	if _, err := ExtensionFile(p, true); err == nil {
		t.Fatal("accepted non-executable file")
	}
	if err := os.Chmod(p, 0700); err != nil {
		t.Fatal(err)
	}
	if _, err := ExtensionFile(p, true); err != nil {
		t.Fatal(err)
	}
	if err := os.Remove(p); err != nil {
		t.Fatal(err)
	}
	if err := syscall.Mkfifo(p, 0600); err != nil {
		t.Fatal(err)
	}
	if _, err := ExtensionFile(p, false); err == nil {
		t.Fatal("accepted FIFO")
	}
}
