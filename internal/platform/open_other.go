//go:build !unix

package platform

import "os"

// OpenReadOnly preserves the platform's native read-only open semantics.
// Callers must classify the returned handle before reading. This provides no
// Unix FIFO or general I/O timeout guarantee on non-Unix platforms.
func OpenReadOnly(path string) (*os.File, error) {
	return os.Open(path)
}
