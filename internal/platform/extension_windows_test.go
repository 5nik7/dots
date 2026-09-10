package platform

import (
	"testing"
)

func TestWindowsCommandRootSyntax(t *testing.T) {
	for _, path := range []string{`relative`, `C:relative`, `\\server\share\commands`, `\\?\C:\commands`, `C:\commands:stream`, `C:\commands\x:stream`} {
		if _, _, err := ExtensionRoot(path); err == nil {
			t.Fatal("accepted unsupported root", path)
		}
	}
	root := t.TempDir()
	if _, _, err := ExtensionRoot(root); err != nil {
		t.Fatal("native NTFS root policy", err)
	}
}
