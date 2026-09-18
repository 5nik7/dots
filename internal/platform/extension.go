package platform

import (
	"errors"
	"os"
	"path/filepath"
)

// Root aliases are resolved once. Identity is checked by the caller with SameFile.
func ExtensionRoot(path string) (string, os.FileInfo, error) {
	if !filepath.IsAbs(path) {
		return "", nil, errors.New("absolute command directory required")
	}
	if err := extensionRootSyntax(path); err != nil {
		return "", nil, err
	}
	canonical, err := filepath.EvalSymlinks(filepath.Clean(path))
	if err != nil {
		return "", nil, err
	}
	if err = extensionRootSyntax(canonical); err != nil {
		return "", nil, err
	}
	info, err := os.Stat(canonical)
	if err != nil {
		return "", nil, err
	}
	if !info.IsDir() {
		return "", nil, errors.New("command root is not a directory")
	}
	if err = extensionRootPolicy(canonical); err != nil {
		return "", nil, err
	}
	return canonical, info, nil
}

func ExtensionFile(path string, executable bool) (os.FileInfo, error) {
	info, err := os.Lstat(path)
	if err != nil {
		return nil, err
	}
	if !info.Mode().IsRegular() {
		return nil, errors.New("command entry is not a plain regular file")
	}
	if err = extensionFilePolicy(path, info, executable); err != nil {
		return nil, err
	}
	return info, nil
}
