//go:build unix

package platform

import (
	"os"
	"syscall"
)

// OpenReadOnly follows symlinks and opens without waiting for a FIFO writer.
// Callers must classify the returned handle before reading; this flag does not
// impose a deadline on regular-file I/O or filesystem path resolution.
func OpenReadOnly(path string) (*os.File, error) {
	return os.OpenFile(path, os.O_RDONLY|syscall.O_NONBLOCK, 0)
}
