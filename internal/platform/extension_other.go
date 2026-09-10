//go:build !unix && !windows

package platform

import (
	"errors"
	"os"
)

func extensionRootSyntax(string) error { return errors.New("external commands unavailable") }
func extensionRootPolicy(string) error { return errors.New("external commands unavailable") }
func extensionFilePolicy(string, os.FileInfo, bool) error {
	return errors.New("external commands unavailable")
}
func ExecuteExtension(string, []string) (int, error) {
	return 1, errors.New("external commands unavailable")
}
