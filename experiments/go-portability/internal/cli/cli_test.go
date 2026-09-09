package cli

import (
	"bytes"
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"dots.local/portability/internal/platform"
)

func TestCLI(t *testing.T) {
	for _, tc := range []struct {
		name             string
		args             []string
		code             int
		want             string
		logo, diagnostic bool
	}{
		{"empty", nil, 0, "Usage:", true, false},
		{"help command", []string{"help"}, 0, "Usage:", true, false},
		{"short help", []string{"-h"}, 0, "Usage:", true, false},
		{"long help", []string{"--help"}, 0, "Usage:", true, false},
		{"version", []string{"--version"}, 0, "dots-spike 0.0.0-spike", false, false},
		{"doctor", []string{"doctor"}, 0, "Platform: termux", false, true},
		{"doctor help", []string{"doctor", "--help"}, 0, "Usage: dots-spike doctor", true, false},
		{"doctor short help", []string{"doctor", "-h"}, 0, "Usage: dots-spike doctor", true, false},
		{"unknown", []string{"TOP_SECRET"}, 2, "", false, false},
		{"unimplemented", []string{"apply"}, 2, "", false, false},
		{"completion deferred", []string{"completion"}, 2, "", false, false},
		{"extra help", []string{"help", "TOP_SECRET"}, 2, "", false, false},
		{"extra version", []string{"--version", "TOP_SECRET"}, 2, "", false, false},
		{"unknown flag", []string{"doctor", "--reveal"}, 2, "", false, false},
		{"trailing argument", []string{"doctor", "--json", "TOP_SECRET"}, 2, "", false, false},
	} {
		t.Run(tc.name, func(t *testing.T) {
			var out, errOut bytes.Buffer
			logoCalls, diagnosticCalls := 0, 0
			code := Run(tc.args, &out, &errOut, func() string { logoCalls++; return "LOGO\n" }, func() platform.Report {
				diagnosticCalls++
				return platform.Report{Platform: "termux"}
			})
			if code != tc.code || !strings.Contains(out.String(), tc.want) {
				t.Fatalf("code=%d stdout=%q stderr=%q", code, out.String(), errOut.String())
			}
			if (logoCalls != 0) != tc.logo || (diagnosticCalls != 0) != tc.diagnostic {
				t.Fatalf("unexpected initialization: logo=%d diagnostics=%d", logoCalls, diagnosticCalls)
			}
			if (tc.code == 0 && errOut.Len() != 0) || (tc.code != 0 && (out.Len() != 0 || errOut.Len() == 0)) {
				t.Fatal("output on wrong stream")
			}
			if strings.Contains(out.String()+errOut.String(), "TOP_SECRET") {
				t.Fatal("argument leaked")
			}
		})
	}
}

func TestDiagnosticJSON(t *testing.T) {
	var out, errOut bytes.Buffer
	code := Run([]string{"doctor", "--json"}, &out, &errOut, func() string { t.Fatal("JSON read logo"); return "" }, func() platform.Report {
		return platform.Report{SchemaVersion: 1, Platform: "termux", Capabilities: map[string]string{"copy": "not_probed"}}
	})
	var report map[string]any
	if code != 0 || errOut.Len() != 0 || json.Unmarshal(out.Bytes(), &report) != nil {
		t.Fatalf("invalid structured output: %q / %q", out.String(), errOut.String())
	}
	if report["schema_version"] != float64(1) || report["platform"] != "termux" || strings.Contains(out.String(), "\x1b") {
		t.Fatal("JSON contract changed")
	}
}

func TestMetadata(t *testing.T) {
	seen := map[string]bool{}
	var out bytes.Buffer
	help(&out, func() string { return "" }, false)
	for _, c := range commands {
		if c.summary == "" || c.synopsis == "" || !strings.Contains(out.String(), c.synopsis) {
			t.Fatal("incomplete or unadvertised metadata")
		}
		for _, name := range c.names {
			if seen[name] {
				t.Fatalf("duplicate route: %s", name)
			}
			seen[name] = true
		}
	}
	if len(seen) != 5 || !seen["help"] || !seen["doctor"] || !seen["--version"] {
		t.Fatal("unexpected experimental command surface")
	}
}

func TestLogo(t *testing.T) {
	root := t.TempDir()
	bin := filepath.Join(root, "bin")
	if err := os.Mkdir(bin, 0700); err != nil {
		t.Fatal(err)
	}
	exe := filepath.Join(bin, "dots-spike")
	if err := os.WriteFile(exe, nil, 0600); err != nil {
		t.Fatal(err)
	}
	getExe := func() (string, error) { return exe, nil }
	logoPath := filepath.Join(root, "logo.txt")
	if got := loadLogo("", getExe); got != "" {
		t.Fatal("missing logo")
	}
	for _, content := range []string{"", "art", "art\n", "\nart\n\n", strings.Repeat("x", 65537)} {
		if err := os.WriteFile(logoPath, []byte(content), 0600); err != nil {
			t.Fatal(err)
		}
		want := content
		if content == "" || len(content) > 65536 {
			want = ""
		} else {
			if !strings.HasSuffix(want, "\n") {
				want += "\n"
			}
			want += "\n"
		}
		if got := loadLogo("", getExe); got != want {
			t.Fatalf("logo formatting length=%d", len(content))
		}
	}
	other := t.TempDir()
	if err := os.WriteFile(filepath.Join(other, "logo.txt"), []byte("override"), 0600); err != nil {
		t.Fatal(err)
	}
	if got := loadLogo(other, func() (string, error) { t.Fatal("DOTS must take precedence"); return "", nil }); got != "override\n\n" {
		t.Fatal("DOTS override ignored")
	}
	if err := os.Remove(logoPath); err != nil {
		t.Fatal(err)
	}
	if err := os.Mkdir(logoPath, 0700); err != nil {
		t.Fatal(err)
	}
	if loadLogo("", getExe) != "" {
		t.Fatal("directory logo read")
	}
	if loadLogo("", func() (string, error) { return "", errors.New("unavailable") }) != "" {
		t.Fatal("executable error")
	}
}

type failedWriter struct{}

func (failedWriter) Write([]byte) (int, error) { return 0, errors.New("closed") }

func TestOutputFailure(t *testing.T) {
	if Run([]string{"--version"}, failedWriter{}, &bytes.Buffer{}, nil, nil) != 1 {
		t.Fatal("lost write error")
	}
}
