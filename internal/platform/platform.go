// Package platform is the sole boundary for runtime, environment, and path
// mechanics. Reports are observations/candidates, never permission to mutate.
package platform

import (
	"fmt"
	"io"
	"os"
	"path/filepath"
	"runtime"
	"sort"
	"strings"
)

type Report struct {
	SchemaVersion int               `json:"schema_version"`
	Platform      string            `json:"platform"`
	OS            string            `json:"os"`
	Architecture  string            `json:"architecture"`
	GoVersion     string            `json:"go_version"`
	Evidence      []string          `json:"evidence"`
	Paths         map[string]string `json:"paths"`
	Capabilities  map[string]string `json:"capabilities"`
	Warnings      []string          `json:"warnings"`
}

// inputs separates collection from classification so tests never need a real
// home, registry, shell configuration, or platform override environment variable.
type inputs struct {
	os, arch, goVersion, executable, kernel string
	env                                     map[string]string
	prefixBin, androidLinker                bool
}

func Inspect() Report {
	in := inputs{os: runtime.GOOS, arch: runtime.GOARCH, goVersion: runtime.Version(), env: map[string]string{}}
	for _, key := range []string{"HOME", "PREFIX", "TERMUX_VERSION", "DOTS", "XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_STATE_HOME", "XDG_CACHE_HOME", "TMPDIR", "WSL_INTEROP", "WSL_DISTRO_NAME"} {
		in.env[key] = os.Getenv(key)
	}
	in.executable, _ = os.Executable()
	if in.os == "android" || in.os == "linux" {
		prefix := in.env["PREFIX"]
		if filepath.IsAbs(prefix) && filepath.Base(filepath.Clean(prefix)) == "usr" {
			info, err := os.Stat(filepath.Join(prefix, "bin"))
			in.prefixBin = err == nil && info.IsDir()
		}
		for _, path := range []string{"/system/bin/linker64", "/system/bin/linker"} {
			if info, err := os.Stat(path); err == nil && info.Mode().IsRegular() {
				in.androidLinker = true
			}
		}
		if in.os == "linux" {
			// A bounded public kernel marker, not /proc environments or user files.
			if f, err := os.Open("/proc/sys/kernel/osrelease"); err == nil {
				data, _ := io.ReadAll(io.LimitReader(f, 4096))
				f.Close()
				in.kernel = string(data)
			}
		}
	}
	return inspect(in)
}

func inspect(in inputs) Report {
	r := Report{
		SchemaVersion: 1, Platform: "unknown", OS: in.os, Architecture: in.arch, GoVersion: in.goVersion,
		Evidence: []string{"runtime:" + in.os}, Paths: map[string]string{}, Warnings: []string{},
		Capabilities: map[string]string{"file_symlink": "not_probed", "directory_symlink": "not_probed", "copy": "not_probed"},
	}
	android := in.os == "android" || in.androidLinker
	switch {
	case in.os == "windows":
		r.Platform = "windows"
	case (in.os == "android" || in.os == "linux") && android && in.env["TERMUX_VERSION"] != "" && in.prefixBin:
		r.Platform = "termux"
		r.Evidence = append(r.Evidence, "TERMUX_VERSION:set", "PREFIX:usr/bin directory", "Android runtime")
	case in.os == "linux" && !android:
		r.Platform = "linux"
		if in.env["WSL_INTEROP"] != "" || in.env["WSL_DISTRO_NAME"] != "" || strings.Contains(strings.ToLower(in.kernel), "microsoft") {
			r.Platform = "wsl"
			if in.env["WSL_INTEROP"] != "" || in.env["WSL_DISTRO_NAME"] != "" {
				r.Evidence = append(r.Evidence, "WSL environment marker:set")
			}
			if strings.Contains(strings.ToLower(in.kernel), "microsoft") {
				r.Evidence = append(r.Evidence, "kernel:Microsoft marker")
			}
		}
	}
	if in.executable != "" {
		r.Paths["executable"] = in.executable
	}
	if r.Platform == "windows" || r.Platform == "unknown" {
		r.Warnings = append(r.Warnings, "Path resolution is not implemented for this platform in the spike.")
		return r
	}
	// Unix path rules stay here; native Windows known folders remain deferred.
	path := func(key, fallback string) string {
		value := in.env[key]
		if value == "" {
			return fallback
		}
		if !filepath.IsAbs(value) {
			r.Warnings = append(r.Warnings, key+" is relative; using the default candidate if available.")
			return fallback
		}
		return filepath.Clean(value)
	}
	home := path("HOME", "")
	if home == "" {
		r.Warnings = append(r.Warnings, "HOME is missing or invalid; home-relative candidates are unavailable.")
	} else {
		r.Paths["home"] = home
	}
	underHome := func(parts ...string) string {
		if home == "" {
			return ""
		}
		return filepath.Join(append([]string{home}, parts...)...)
	}
	for _, root := range []struct{ name, env, fallback string }{
		{"config", "XDG_CONFIG_HOME", underHome(".config")},
		{"data", "XDG_DATA_HOME", underHome(".local", "share")},
		{"state", "XDG_STATE_HOME", underHome(".local", "state")},
		{"cache", "XDG_CACHE_HOME", underHome(".cache")},
	} {
		if value := path(root.env, root.fallback); value != "" {
			r.Paths[root.name] = filepath.Join(value, "dots")
		}
	}
	if repo := path("DOTS", underHome("dots")); repo != "" {
		r.Paths["repository"] = repo
	}
	temp := "/tmp"
	if r.Platform == "termux" {
		r.Paths["prefix"] = filepath.Clean(in.env["PREFIX"])
		temp = filepath.Join(r.Paths["prefix"], "tmp")
	}
	r.Paths["temp"] = path("TMPDIR", temp)
	return r
}

func (r Report) WriteText(out io.Writer) error {
	var text strings.Builder
	fmt.Fprintf(&text, "Platform: %s\nRuntime: %s/%s (%s)\n", r.Platform, r.OS, r.Architecture, r.GoVersion)
	for _, evidence := range r.Evidence {
		fmt.Fprintf(&text, "Evidence: %s\n", evidence)
	}
	for _, key := range sortedKeys(r.Paths) {
		// Quote path values so control characters cannot inject terminal output.
		fmt.Fprintf(&text, "Path candidate %s: %q\n", key, r.Paths[key])
	}
	for _, key := range sortedKeys(r.Capabilities) {
		fmt.Fprintf(&text, "Capability %s: %s\n", key, r.Capabilities[key])
	}
	for _, warning := range r.Warnings {
		fmt.Fprintf(&text, "Warning: %s\n", warning)
	}
	_, err := io.WriteString(out, text.String())
	return err
}

func sortedKeys(values map[string]string) []string {
	keys := make([]string, 0, len(values))
	for key := range values {
		keys = append(keys, key)
	}
	sort.Strings(keys)
	return keys
}
