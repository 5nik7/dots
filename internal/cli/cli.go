// Package cli binds the permanent read-only built-ins to their registry.
package cli

import (
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"runtime"
	"strings"

	"github.com/5nik7/dots/internal/dispatch"
	"github.com/5nik7/dots/internal/platform"
)

const Version = "0.0.0-dev"

// Registry constructs validated metadata and closures without inspecting the
// environment. Only successful help/doctor handlers invoke their providers.
func registry(out, errOut io.Writer, logo func() string, diagnose func() platform.Report) (*dispatch.Registry, error) {
	var r *dispatch.Registry
	usageError := func() int {
		fmt.Fprintln(errOut, "dots: unknown command or unsupported arguments; use --help")
		return 2
	}
	entries := []dispatch.Entry{
		{Metadata: dispatch.Metadata{ID: "help", Route: []string{"help"}, GlobalOptions: []string{"-h", "--help"}, Summary: "Display this help message", Synopsis: "help, -h, --help", Examples: []string{"dots --help"}, Platforms: []string{"*"}, Outputs: []dispatch.Output{{Format: "text"}}, Mutation: "read-only"}, Handler: func(args []string) int {
			if len(args) != 0 {
				return usageError()
			}
			return help(out, logo, r, "")
		}},
		{Metadata: dispatch.Metadata{ID: "version", GlobalOptions: []string{"--version"}, Summary: "Print the development build version", Synopsis: "--version", Examples: []string{"dots --version"}, Platforms: []string{"*"}, Outputs: []dispatch.Output{{Format: "text"}}, Mutation: "read-only"}, Handler: func(args []string) int {
			if len(args) != 0 {
				return usageError()
			}
			_, err := fmt.Fprintf(out, "dots %s %s %s/%s\n", Version, runtime.Version(), runtime.GOOS, runtime.GOARCH)
			return outputStatus(err)
		}},
		{Metadata: dispatch.Metadata{ID: "doctor", Route: []string{"doctor"}, Summary: "Report platform evidence and candidate paths (read-only)", Synopsis: "doctor [--json | -h | --help]", Examples: []string{"dots doctor", "dots doctor --json"}, Platforms: []string{"*"}, Outputs: []dispatch.Output{{Format: "text"}, {Format: "json", SchemaVersion: 1}}, Mutation: "read-only"}, Handler: func(args []string) int {
			if len(args) == 1 && (args[0] == "--help" || args[0] == "-h") {
				return help(out, logo, r, "doctor")
			}
			if len(args) > 1 || (len(args) == 1 && args[0] != "--json") {
				return usageError()
			}
			report := diagnose()
			if len(args) == 1 {
				encoder := json.NewEncoder(out)
				encoder.SetIndent("", "  ")
				return outputStatus(encoder.Encode(report))
			}
			return outputStatus(report.WriteText(out))
		}},
	}
	var err error
	r, err = dispatch.New(entries, "help")
	return r, err
}

func Run(args []string, out, errOut io.Writer, logo func() string, diagnose func() platform.Report) int {
	r, err := registry(out, errOut, logo, diagnose)
	if err != nil {
		fmt.Fprintln(errOut, "dots: invalid built-in registry")
		return 1
	}
	// All shipped read-only entries support every runtime, including diagnostic
	// reports for unknown platforms. No platform inspection is needed for lookup.
	handler, remaining, err := r.Resolve(args, "", nil)
	if err != nil {
		if err == dispatch.ErrUnavailable {
			fmt.Fprintln(errOut, "dots: command unavailable on this platform")
		} else {
			fmt.Fprintln(errOut, "dots: unknown command or unsupported arguments; use --help")
		}
		return 2
	}
	return handler(remaining)
}

func outputStatus(err error) int {
	if err != nil {
		return 1
	}
	return 0
}

func help(out io.Writer, logo func() string, r *dispatch.Registry, id string) int {
	var text strings.Builder
	text.WriteString(logo())
	text.WriteString("dots - for your dotfiles (development core)\n\n")
	metadata := r.Project()
	if id != "" {
		for _, m := range metadata {
			if m.ID == id {
				fmt.Fprintf(&text, "Usage: dots %s\n\n%s.\n", m.Synopsis, m.Summary)
				text.WriteString("No configuration contents are read and no capabilities are probed by writing files.\n")
			}
		}
	} else {
		text.WriteString("Usage: dots <command or global option>\n\n")
		for _, m := range metadata {
			if !m.Hidden {
				fmt.Fprintf(&text, "  %-30s %s\n", m.Synopsis, m.Summary)
			}
		}
		text.WriteString("\nDevelopment binary; no installation or managed-file operations are implemented.\n")
	}
	_, err := io.WriteString(out, text.String())
	return outputStatus(err)
}

// Logo mirrors the Bash prototype's DOTS-first, executable-relative lookup.
// Only help calls it. There is no repository walk or embedded/stale logo.
func Logo() string {
	return loadLogo(os.Getenv("DOTS"), os.Executable)
}

func loadLogo(repo string, executable func() (string, error)) string {
	if repo == "" {
		exe, err := executable()
		if err != nil {
			return ""
		}
		exe, err = filepath.EvalSymlinks(exe)
		if err != nil {
			return ""
		}
		repo = filepath.Dir(filepath.Dir(exe))
	}
	return readLogo(filepath.Join(repo, "logo.txt"), platform.OpenReadOnly)
}

func readLogo(path string, open func(string) (*os.File, error)) string {
	info, err := os.Stat(path)
	const limit = 64 * 1024
	if err != nil || !info.Mode().IsRegular() || info.Size() == 0 || info.Size() > limit {
		return ""
	}
	file, err := open(path)
	if err != nil {
		return ""
	}
	defer file.Close()
	// The pathname may have changed since the preliminary check. Only read
	// after classifying the handle we actually opened.
	info, err = file.Stat()
	if err != nil || !info.Mode().IsRegular() || info.Size() == 0 || info.Size() > limit {
		return ""
	}
	data, err := io.ReadAll(io.LimitReader(file, limit+1))
	if err != nil || len(data) == 0 || len(data) > limit {
		return ""
	}
	text := string(data)
	if !strings.HasSuffix(text, "\n") {
		text += "\n"
	}
	return text + "\n"
}
