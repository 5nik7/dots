// Package cli contains only the experimental built-ins, not extension dispatch.
package cli

import (
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"runtime"
	"strings"

	"dots.local/portability/internal/platform"
)

const Version = "0.0.0-spike"

type command struct {
	names    []string
	synopsis string
	summary  string
}

// This table is deliberately local to the spike; it does not settle the future
// extension metadata format. Help and accepted command names use the same data.
var commands = []command{
	{[]string{"help", "-h", "--help"}, "help, -h, --help", "Display this help message"},
	{[]string{"--version"}, "--version", "Print the experimental build version"},
	{[]string{"doctor"}, "doctor [--json]", "Report platform evidence and candidate paths (read-only)"},
}

func Run(args []string, out, errOut io.Writer, logo func() string, diagnose func() platform.Report) int {
	if len(args) == 0 {
		return help(out, logo, false)
	}
	selected := -1
	for i, c := range commands {
		for _, name := range c.names {
			if args[0] == name {
				selected = i
			}
		}
	}
	usageError := func() int {
		// Do not echo arbitrary arguments: they can contain secrets or escapes.
		fmt.Fprintln(errOut, "dots-spike: unknown command or unsupported arguments; use --help")
		return 2
	}
	switch selected {
	case 0:
		if len(args) != 1 {
			return usageError()
		}
		return help(out, logo, false)
	case 1:
		if len(args) != 1 {
			return usageError()
		}
		_, err := fmt.Fprintf(out, "dots-spike %s %s %s/%s\n", Version, runtime.Version(), runtime.GOOS, runtime.GOARCH)
		return outputStatus(err)
	case 2:
		if len(args) == 2 && (args[1] == "--help" || args[1] == "-h") {
			return help(out, logo, true)
		}
		if len(args) > 2 || (len(args) == 2 && args[1] != "--json") {
			return usageError()
		}
		report := diagnose()
		if len(args) == 2 {
			encoder := json.NewEncoder(out)
			encoder.SetIndent("", "  ")
			return outputStatus(encoder.Encode(report))
		}
		return outputStatus(report.WriteText(out))
	default:
		return usageError()
	}
}

func outputStatus(err error) int {
	if err != nil {
		return 1
	}
	return 0
}

func help(out io.Writer, logo func() string, doctor bool) int {
	var text strings.Builder
	text.WriteString(logo())
	text.WriteString("dots-spike - for your dotfiles (experimental Go portability core)\n\n")
	if doctor {
		text.WriteString("Usage: dots-spike doctor [--json | -h | --help]\n\n")
		text.WriteString(commands[2].summary + ".\n")
		text.WriteString("No configuration contents are read and no capabilities are probed by writing files.\n")
	} else {
		text.WriteString("Usage: dots-spike [help | -h | --help | --version]\n       dots-spike doctor [--json]\n\n")
		for _, c := range commands {
			fmt.Fprintf(&text, "  %-22s %s\n", c.synopsis, c.summary)
		}
		text.WriteString("\nGo remains provisional. No installation or managed-file operations are implemented.\n")
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
	path := filepath.Join(repo, "logo.txt")
	info, err := os.Stat(path)
	const limit = 64 * 1024
	if err != nil || !info.Mode().IsRegular() || info.Size() == 0 || info.Size() > limit {
		return ""
	}
	file, err := os.Open(path)
	if err != nil {
		return ""
	}
	defer file.Close()
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
