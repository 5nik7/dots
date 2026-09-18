package platform

import (
	"bytes"
	"encoding/json"
	"path/filepath"
	"strings"
	"testing"
)

func TestDetection(t *testing.T) {
	for _, tc := range []struct {
		name string
		in   inputs
		want string
	}{
		{"termux", inputs{os: "android", env: map[string]string{"TERMUX_VERSION": "test", "PREFIX": "/fixture/usr"}, prefixBin: true}, "termux"},
		{"generic Android", inputs{os: "android"}, "unknown"},
		{"Android env alone", inputs{os: "android", env: map[string]string{"TERMUX_VERSION": "test"}}, "unknown"},
		{"Linux env spoof", inputs{os: "linux", env: map[string]string{"TERMUX_VERSION": "test"}, prefixBin: true}, "linux"},
		{"Linux binary on Android", inputs{os: "linux", androidLinker: true, prefixBin: true, env: map[string]string{"TERMUX_VERSION": "test", "PREFIX": "/fixture/usr"}}, "termux"},
		{"generic Linux on Android", inputs{os: "linux", androidLinker: true}, "unknown"},
		{"Linux", inputs{os: "linux"}, "linux"},
		{"WSL kernel", inputs{os: "linux", kernel: "6.6.0-microsoft-standard-WSL2"}, "wsl"},
		{"WSL env", inputs{os: "linux", env: map[string]string{"WSL_DISTRO_NAME": "fixture"}}, "wsl"},
		{"native Windows", inputs{os: "windows", env: map[string]string{"WSL_DISTRO_NAME": "fixture", "TERMUX_VERSION": "test"}, prefixBin: true}, "windows"},
		{"unsupported", inputs{os: "freebsd"}, "unknown"},
	} {
		t.Run(tc.name, func(t *testing.T) {
			r := inspect(tc.in)
			if r.Platform != tc.want {
				t.Fatalf("got %s want %s", r.Platform, tc.want)
			}
			for _, value := range r.Capabilities {
				if value != "not_probed" {
					t.Fatal("unverified capability claimed")
				}
			}
			if r.Evidence == nil || r.Warnings == nil || r.Paths == nil {
				t.Fatal("JSON collections must not be null")
			}
		})
	}
}

func TestPathsAndAllowlist(t *testing.T) {
	home := t.TempDir()
	config := filepath.Join(home, "config override")
	in := inputs{os: "linux", env: map[string]string{"HOME": home, "XDG_CONFIG_HOME": config, "XDG_STATE_HOME": "relative", "TOP_SECRET": "must-not-appear"}}
	r := inspect(in)
	if r.Paths["config"] != filepath.Join(config, "dots") || r.Paths["state"] != filepath.Join(home, ".local", "state", "dots") || r.Paths["repository"] != filepath.Join(home, "dots") {
		t.Fatalf("incorrect path candidates: %#v", r.Paths)
	}
	if len(r.Warnings) != 1 {
		t.Fatal("relative override was not reported")
	}
	data, err := json.Marshal(r)
	if err != nil || bytes.Contains(data, []byte("must-not-appear")) {
		t.Fatal("unallowlisted environment leaked")
	}
	delete(in.env, "HOME")
	r = inspect(in)
	if _, ok := r.Paths["home"]; ok {
		t.Fatal("missing home inferred from real machine")
	}
	if _, ok := r.Paths["state"]; ok {
		t.Fatal("relative path accepted without home")
	}
	if r.Paths["config"] != filepath.Join(config, "dots") {
		t.Fatal("absolute override lost without home")
	}
}

func TestHumanOutputQuotesPaths(t *testing.T) {
	r := Report{Paths: map[string]string{"home": "path\n\x1b[31m"}}
	var out bytes.Buffer
	if err := r.WriteText(&out); err != nil {
		t.Fatal(err)
	}
	if strings.Contains(out.String(), "\x1b") || !strings.Contains(out.String(), `path\n\x1b[31m`) {
		t.Fatal("unsafe terminal path output")
	}
}
