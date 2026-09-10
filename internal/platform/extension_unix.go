//go:build unix

package platform

import (
	"errors"
	"os"
	"syscall"
)

func extensionRootSyntax(string) error { return nil }
func extensionRootPolicy(string) error { return nil }
func extensionFilePolicy(_ string, info os.FileInfo, executable bool) error {
	if executable && info.Mode().Perm()&0111 == 0 {
		return errors.New("command file is not executable")
	}
	return nil
}

// Successful execution replaces dots: no parent, extra signal forwarding or I/O pipes.
func ExecuteExtension(path string, args []string) (int, error) {
	return 1, syscall.Exec(path, append([]string{path}, args...), os.Environ())
}
