// Filesystem operations exist ONLY in tests. This is not a managed-file API.
package tests

import (
	"errors"
	"io"
	"os"
	"path/filepath"
	"testing"
)

func fixture(t *testing.T) *os.Root {
	t.Helper()
	r, err := os.OpenRoot(t.TempDir())
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { r.Close() })
	return r
}

func write(t *testing.T, root *os.Root, name, content string) {
	t.Helper()
	f, err := root.OpenFile(name, os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0600)
	if err != nil {
		t.Fatal(err)
	}
	_, err = io.WriteString(f, content)
	closeErr := f.Close()
	if err != nil || closeErr != nil {
		t.Fatalf("write: %v / %v", err, closeErr)
	}
}

func read(t *testing.T, root *os.Root, name string) string {
	t.Helper()
	f, err := root.Open(name)
	if err != nil {
		t.Fatal(err)
	}
	defer f.Close()
	content, err := io.ReadAll(f)
	if err != nil {
		t.Fatal(err)
	}
	return string(content)
}

func copyExclusive(root *os.Root, from, to string) error {
	source, err := root.Open(from)
	if err != nil {
		return err
	}
	defer source.Close()
	target, err := root.OpenFile(to, os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0600)
	if err != nil {
		return err
	}
	_, copyErr := io.Copy(target, source)
	return errors.Join(copyErr, target.Close())
}

func TestSymlinkAndCopy(t *testing.T) {
	for _, name := range []string{"path with spaces", "日本語", "-leading-dash"} {
		t.Run(name, func(t *testing.T) {
			r := fixture(t)
			write(t, r, name, "source contents\n")
			if err := r.Symlink(name, "link"); err != nil {
				t.Fatal(err)
			}
			info, err := r.Lstat("link")
			if err != nil || info.Mode()&os.ModeSymlink == 0 {
				t.Fatalf("not a link: %v", err)
			}
			if target, err := r.Readlink("link"); err != nil || target != name {
				t.Fatalf("link target: %q %v", target, err)
			}
			if read(t, r, "link") != read(t, r, name) {
				t.Fatal("symlink contents differ")
			}
			if err := copyExclusive(r, name, "copy"); err != nil {
				t.Fatal(err)
			}
			info, err = r.Lstat("copy")
			if err != nil || !info.Mode().IsRegular() {
				t.Fatalf("not a regular copy: %v", err)
			}
			original, err := r.Stat(name)
			if err != nil || os.SameFile(original, info) {
				t.Fatal("copy shares source identity")
			}
			if read(t, r, "copy") != read(t, r, name) {
				t.Fatal("copy contents differ")
			}
			if err := r.Remove(name); err != nil {
				t.Fatal(err)
			}
			if _, err := r.Stat("link"); !errors.Is(err, os.ErrNotExist) {
				t.Fatal("removed source should leave broken link")
			}
			if _, err := r.Lstat("link"); err != nil {
				t.Fatal("broken link disappeared")
			}
			if read(t, r, "copy") != "source contents\n" {
				t.Fatal("copy depended on source")
			}
		})
	}
}

func TestExistingTargets(t *testing.T) {
	for _, kind := range []string{"file", "directory", "broken link"} {
		t.Run(kind, func(t *testing.T) {
			r := fixture(t)
			write(t, r, "source", "new")
			switch kind {
			case "file":
				write(t, r, "target", "keep")
			case "directory":
				if err := r.Mkdir("target", 0700); err != nil {
					t.Fatal(err)
				}
			case "broken link":
				if err := r.Symlink("absent", "target"); err != nil {
					t.Fatal(err)
				}
			}
			before, err := r.Lstat("target")
			if err != nil {
				t.Fatal(err)
			}
			if err := r.Symlink("source", "target"); !errors.Is(err, os.ErrExist) {
				t.Fatalf("link overwrite refusal: %v", err)
			}
			if err := copyExclusive(r, "source", "target"); !errors.Is(err, os.ErrExist) {
				t.Fatalf("copy overwrite refusal: %v", err)
			}
			after, err := r.Lstat("target")
			if err != nil || !os.SameFile(before, after) {
				t.Fatal("existing object changed")
			}
			if kind == "file" && read(t, r, "target") != "keep" {
				t.Fatal("existing contents changed")
			}
			if kind == "broken link" {
				if target, err := r.Readlink("target"); err != nil || target != "absent" {
					t.Fatal("broken link changed")
				}
				if _, err := r.Lstat("absent"); !errors.Is(err, os.ErrNotExist) {
					t.Fatal("copy followed broken link")
				}
			}
		})
	}
}

func TestDirectoryLinkAndMissingParent(t *testing.T) {
	r := fixture(t)
	if err := r.Mkdir("source dir", 0700); err != nil {
		t.Fatal(err)
	}
	write(t, r, filepath.Join("source dir", "file"), "inside")
	if err := r.Symlink("source dir", "dir link"); err != nil {
		t.Fatal(err)
	}
	if read(t, r, filepath.Join("dir link", "file")) != "inside" {
		t.Fatal("directory link failed")
	}
	if err := r.Symlink("source dir", "missing/target"); !errors.Is(err, os.ErrNotExist) {
		t.Fatalf("missing parent: %v", err)
	}
	if err := copyExclusive(r, "source dir/file", "missing/copy"); !errors.Is(err, os.ErrNotExist) {
		t.Fatalf("missing copy parent: %v", err)
	}
	if _, err := r.Lstat("missing"); !errors.Is(err, os.ErrNotExist) {
		t.Fatal("failed operation created parent")
	}
}

func TestRootEscapeRefused(t *testing.T) {
	// Both the allowed root and the escape sentinel are test-owned. Even a
	// failing containment assertion cannot target the real home or repository.
	outer := fixture(t)
	write(t, outer, "sentinel", "keep")
	if err := outer.Mkdir("allowed", 0700); err != nil {
		t.Fatal(err)
	}
	r, err := outer.OpenRoot("allowed")
	if err != nil {
		t.Fatal(err)
	}
	defer r.Close()
	write(t, r, "source", "new")
	if err := copyExclusive(r, "source", "../escape"); err == nil {
		t.Fatal("traversal accepted")
	}
	if err := r.Symlink("../sentinel", "outside"); err != nil {
		t.Fatal(err)
	}
	if err := copyExclusive(r, "outside", "copy"); err == nil {
		t.Fatal("symlink escape followed")
	}
	if read(t, outer, "sentinel") != "keep" {
		t.Fatal("sentinel changed")
	}
	if _, err := outer.Lstat("escape"); !errors.Is(err, os.ErrNotExist) {
		t.Fatal("escape created")
	}
}
