//go:build unix

package cli

import (
	"context"
	"os"
	"os/exec"
	"path/filepath"
	"syscall"
	"testing"
	"time"

	"dots.local/portability/internal/platform"
)

func TestLogoReplacement(t *testing.T) {
	if os.Getenv("DOTS_TEST_LOGO_REPLACEMENT_CHILD") != "1" {
		// A blocked open/read must fail this test without stranding a goroutine
		// or preventing cleanup. Only this test-owned child may be killed.
		root := t.TempDir()
		for _, name := range []string{"home", "config", "data", "state", "cache", "tmp", "repo", "bin"} {
			if err := os.Mkdir(filepath.Join(root, name), 0700); err != nil {
				t.Fatal(err)
			}
		}
		executable, err := os.Executable()
		if err != nil {
			t.Fatal(err)
		}
		ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()
		cmd := exec.CommandContext(ctx, executable, "-test.run=^TestLogoReplacement$", "-test.v")
		cmd.Dir = filepath.Join(root, "repo")
		cmd.Env = []string{
			"DOTS_TEST_LOGO_REPLACEMENT_CHILD=1", "PATH=",
			"HOME=" + filepath.Join(root, "home"), "DOTS=" + filepath.Join(root, "repo"),
			"XDG_CONFIG_HOME=" + filepath.Join(root, "config"),
			"XDG_DATA_HOME=" + filepath.Join(root, "data"),
			"XDG_STATE_HOME=" + filepath.Join(root, "state"),
			"XDG_CACHE_HOME=" + filepath.Join(root, "cache"),
			"TMPDIR=" + filepath.Join(root, "tmp"),
		}
		output, err := cmd.CombinedOutput()
		if ctx.Err() != nil {
			t.Fatalf("logo replacement blocked past the child deadline: %v\n%s", ctx.Err(), output)
		}
		if err != nil {
			t.Fatalf("logo replacement child failed: %v\n%s", err, output)
		}
		t.Logf("isolated child:\n%s", output)
		return
	}

	for _, mode := range []string{"fifo", "symlink-to-fifo", "fifo-with-writer", "regular-symlink"} {
		t.Run(mode, func(t *testing.T) {
			root := t.TempDir()
			path := filepath.Join(root, "logo.txt")
			target := path
			if mode == "symlink-to-fifo" || mode == "regular-symlink" {
				target = filepath.Join(root, "source with spaces")
				if err := os.Symlink(target, path); err != nil {
					t.Fatal(err)
				}
			}
			if err := os.WriteFile(target, []byte("REGULAR LOGO"), 0600); err != nil {
				t.Fatal(err)
			}
			if mode == "regular-symlink" {
				if got := loadLogo(root, nil); got != "REGULAR LOGO\n\n" {
					t.Fatalf("valid logo symlink changed: %q", got)
				}
				return
			}
			opened := false
			got := readLogo(path, func(name string) (*os.File, error) {
				opened = true
				// This callback runs after the preliminary pathname Stat.
				if err := os.Remove(target); err != nil {
					t.Fatal(err)
				}
				if err := syscall.Mkfifo(target, 0600); err != nil {
					t.Fatal(err)
				}
				if mode == "fifo-with-writer" {
					writer, err := os.OpenFile(target, os.O_RDWR|syscall.O_NONBLOCK, 0)
					if err != nil {
						t.Fatal(err)
					}
					t.Cleanup(func() { writer.Close() })
					if _, err := writer.WriteString("PIPE CONTENT MUST NOT BE READ"); err != nil {
						t.Fatal(err)
					}
				}
				return platform.OpenReadOnly(name)
			})
			if !opened || got != "" {
				t.Fatalf("replaced logo was not omitted: opened=%v logo=%q", opened, got)
			}
		})
	}
}
