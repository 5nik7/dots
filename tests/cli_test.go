// Package tests exercises a prebuilt binary supplied only by the isolated runner.
package tests

import (
	"context"
	"crypto/sha256"
	"encoding/json"
	"io/fs"
	"os"
	"os/exec"
	"path/filepath"
	"reflect"
	"runtime"
	"strings"
	"testing"
	"time"
)

type observed struct {
	Mode     fs.FileMode
	Size     int64
	Modified int64
	Content  [32]byte
}

func snapshot(t *testing.T, root string) map[string]observed {
	t.Helper()
	result := map[string]observed{}
	err := filepath.WalkDir(root, func(path string, d fs.DirEntry, err error) error {
		if err != nil {
			return err
		}
		info, err := d.Info()
		if err != nil {
			return err
		}
		item := observed{Mode: info.Mode(), Size: info.Size(), Modified: info.ModTime().UnixNano()}
		if info.Mode().IsRegular() {
			data, err := os.ReadFile(path)
			if err != nil {
				return err
			}
			item.Content = sha256.Sum256(data)
		}
		result[path] = item
		return nil
	})
	if err != nil {
		t.Fatal(err)
	}
	return result
}

func TestDevelopmentProcess(t *testing.T) {
	binary := os.Getenv("DOTS_CORE_TEST_BIN")
	if !filepath.IsAbs(binary) {
		t.Fatal("run through tools/verify_core.py check with a test-owned prebuilt binary")
	}
	root := t.TempDir()
	for _, name := range []string{"home", "config", "data", "state", "cache", "tmp", "repo", "bin", "usr/bin"} {
		if err := os.MkdirAll(filepath.Join(root, name), 0700); err != nil {
			t.Fatal(err)
		}
	}
	// A tempting extension and a poison config stay inert even for matching input.
	for name, content := range map[string]string{"repo/dots.toml": "INVALID TOP_SECRET_CONFIG", "bin/dots-apply": "TOP_SECRET_EXTENSION", "repo/logo.txt": "PROCESS LOGO\n"} {
		if err := os.WriteFile(filepath.Join(root, name), []byte(content), 0600); err != nil {
			t.Fatal(err)
		}
	}
	env := []string{"PATH=", "HOME=" + filepath.Join(root, "home"), "DOTS=" + filepath.Join(root, "repo"), "XDG_CONFIG_HOME=" + filepath.Join(root, "config"), "XDG_DATA_HOME=" + filepath.Join(root, "data"), "XDG_STATE_HOME=" + filepath.Join(root, "state"), "XDG_CACHE_HOME=" + filepath.Join(root, "cache"), "TMPDIR=" + filepath.Join(root, "tmp"), "TMP=" + filepath.Join(root, "tmp"), "TEMP=" + filepath.Join(root, "tmp"), "USERPROFILE=" + filepath.Join(root, "home"), "APPDATA=" + filepath.Join(root, "config"), "LOCALAPPDATA=" + filepath.Join(root, "data"), "NO_COLOR=1", "TOP_SECRET_ENV=TOP_SECRET_VALUE"}
	if runtime.GOOS == "android" {
		env = append(env, "TERMUX_VERSION=fixture", "PREFIX="+filepath.Join(root, "usr"))
	}
	if runtime.GOOS == "windows" {
		for _, key := range []string{"SystemRoot", "WINDIR"} {
			if value := os.Getenv(key); value != "" {
				env = append(env, key+"="+value)
			}
		}
		volume := filepath.VolumeName(filepath.Join(root, "home"))
		env = append(env, "HOMEDRIVE="+volume, "HOMEPATH="+strings.TrimPrefix(filepath.Join(root, "home"), volume))
	}
	before := snapshot(t, root)
	for _, args := range [][]string{nil, {"--help"}, {"help"}, {"-h"}, {"--version"}, {"doctor"}, {"doctor", "--json"}, {"doctor", "-h"}, {"doctor", "--help"}, {"version"}, {"commands"}, {"completion"}, {"apply"}, {"--dir"}, {"-r", "--dir"}, {"doctor", "--json", "TOP_SECRET_ARGUMENT"}, {"--help", "path with spaces"}, {"日本語"}, {"-leading-dash"}} {
		t.Run(strings.Join(args, " "), func(t *testing.T) {
			ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
			defer cancel()
			cmd := exec.CommandContext(ctx, binary, args...)
			cmd.Dir = filepath.Join(root, "repo")
			cmd.Env = env
			var stdout, stderr strings.Builder
			cmd.Stdout = &stdout
			cmd.Stderr = &stderr
			err := cmd.Run()
			valid := len(args) == 0 || len(args) == 1 && (args[0] == "--help" || args[0] == "help" || args[0] == "-h" || args[0] == "--version" || args[0] == "doctor") || len(args) == 2 && args[0] == "doctor" && (args[1] == "--json" || args[1] == "-h" || args[1] == "--help")
			if ctx.Err() != nil {
				t.Fatal("command exceeded deadline")
			}
			if valid {
				if err != nil || stderr.Len() != 0 {
					t.Fatalf("read-only command failed: %v", err)
				}
			} else {
				exit, ok := err.(*exec.ExitError)
				if !ok || exit.ExitCode() != 2 || stdout.Len() != 0 || stderr.Len() == 0 {
					t.Fatalf("wrong usage error: %v", err)
				}
			}
			if strings.Contains(stdout.String()+stderr.String(), "TOP_SECRET") {
				t.Fatal("secret sentinel leaked")
			}
			if reflect.DeepEqual(args, []string{"--version"}) {
				if !strings.HasPrefix(stdout.String(), "dots 0.0.0-dev ") || strings.Contains(stdout.String(), "LOGO") {
					t.Fatal("version contract")
				}
			}
			if reflect.DeepEqual(args, []string{"doctor", "--json"}) {
				var report map[string]any
				if json.Unmarshal([]byte(stdout.String()), &report) != nil || report["schema_version"] != float64(1) || len(report) != 9 {
					t.Fatal("JSON schema contract")
				}
				for _, v := range report["capabilities"].(map[string]any) {
					if v != "not_probed" {
						t.Fatal("unexpected capability")
					}
				}
				if strings.ContainsAny(stdout.String(), "\x1b") || strings.Contains(stdout.String(), "LOGO") {
					t.Fatal("decorated JSON")
				}
			}
			after := snapshot(t, root)
			if !reflect.DeepEqual(before, after) {
				for path, old := range before {
					if current, ok := after[path]; !ok || current != old {
						rel, _ := filepath.Rel(root, path)
						t.Logf("changed %s: before=%+v after=%+v present=%t", rel, old, current, ok)
					}
				}
				for path := range after {
					if _, ok := before[path]; !ok {
						rel, _ := filepath.Rel(root, path)
						t.Logf("added %s", rel)
					}
				}
				t.Fatal("read-only process changed owned roots")
			}
		})
	}
}
