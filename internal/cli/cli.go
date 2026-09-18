// Package cli binds the permanent built-ins and explicit external resolver.
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
	"github.com/5nik7/dots/internal/extension"
	"github.com/5nik7/dots/internal/platform"
)

const Version = "0.0.0-dev"

// Registry constructs validated metadata and closures without inspecting the
// environment. Only successful help/doctor handlers invoke their providers.
func registry(out, errOut io.Writer, logo func() string, diagnose func() platform.Report, discover ...func(*dispatch.Registry, []string) int) (*dispatch.Registry, error) {
	var r *dispatch.Registry
	usageError := func() int {
		fmt.Fprintln(errOut, "dots: unknown command or unsupported arguments; use --help")
		return 2
	}
	entries := []dispatch.Entry{
		{Metadata: dispatch.Metadata{ID: "completion", Route: []string{"completion"}, Summary: "Generate static Zsh completion (no installation)", Synopsis: "completion (zsh | -h | --help)", Examples: []string{"dots completion zsh"}, Platforms: []string{"*"}, Outputs: []dispatch.Output{{Format: "text"}}, Mutation: "read-only"}, Handler: func(args []string) int {
			if len(args) == 1 && (args[0] == "--help" || args[0] == "-h") {
				return help(out, logo, r, "completion")
			}
			if len(args) != 1 || args[0] != "zsh" {
				return usageError()
			}
			if len(discover) > 0 {
				return discover[0](r, []string{"completion", "zsh"})
			}
			return completionOutput(out, errOut, r, nil, nil)
		}},
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
		{Metadata: dispatch.Metadata{ID: "commands", Route: []string{"commands"}, Summary: "List or validate static command metadata", Synopsis: "commands [--json | --check | -h | --help]", Examples: []string{"dots commands", "dots commands --json"}, Platforms: []string{"*"}, Outputs: []dispatch.Output{{Format: "text"}, {Format: "json", SchemaVersion: 1}}, Mutation: "read-only"}, Handler: func(args []string) int {
			if len(args) == 1 && (args[0] == "--help" || args[0] == "-h") {
				return help(out, logo, r, "commands")
			}
			if len(args) > 1 || len(args) == 1 && args[0] != "--check" && args[0] != "--json" {
				return usageError()
			}
			if len(discover) > 0 {
				return discover[0](r, args)
			}
			return commandListing(out, errOut, r, nil, args)
		}},
	}
	var err error
	r, err = dispatch.New(entries, "help")
	return r, err
}

func Run(args []string, out, errOut io.Writer, logo func() string, diagnose func() platform.Report) int {
	roots, remaining, err := commandPrefix(args)
	if err != nil {
		fmt.Fprintln(errOut, "dots: invalid --command-dir syntax or root-count limit")
		return 2
	}
	args = remaining
	reportError := func(err error) int {
		fmt.Fprintln(errOut, "dots: "+err.Error())
		if e, ok := err.(*extension.Error); ok && e.Kind == extension.Unknown {
			return 2
		}
		return 1
	}
	resolve := func() (*extension.Resolver, error) {
		target := "unknown"
		if len(roots) > 0 {
			target = diagnose().Platform
		}
		return extension.New(roots, target, extension.NativeAccess())
	}
	r, err := registry(out, errOut, logo, diagnose, func(r *dispatch.Registry, args []string) int {
		resolver, err := resolve()
		if err != nil {
			return reportError(err)
		}
		definitions, err := resolver.Discover(len(args) == 1 && args[0] == "--check")
		if err != nil {
			return reportError(err)
		}
		if len(args) == 2 && args[0] == "completion" {
			return completionOutput(out, errOut, r, definitions, roots)
		}
		return commandListing(out, errOut, r, definitions, args)
	})
	if err != nil {
		fmt.Fprintln(errOut, "dots: invalid built-in registry")
		return 1
	}
	handler, rest, err := r.Resolve(args, "", nil)
	if err == nil {
		return handler(rest)
	}
	if len(args) == 0 || dispatch.Protected(args[0]) {
		return reportError(&extension.Error{Kind: extension.Unknown})
	}
	candidates, err := dispatch.Candidates(args)
	if err != nil {
		fmt.Fprintln(errOut, "dots: external route exceeds matching limit; use -- before arguments")
		return 2
	}
	if len(candidates) == 0 || len(roots) == 0 {
		return reportError(&extension.Error{Kind: extension.Unknown})
	}
	resolver, err := resolve()
	if err != nil {
		return reportError(err)
	}
	definition, route, err := resolver.Lookup(candidates)
	if err != nil {
		return reportError(err)
	}
	if dispatch.ExternalHelp(args) {
		return externalHelp(out, definition)
	}
	if definition.Availability != nil {
		return reportError(definition.Availability)
	}
	code, err := platform.ExecuteExtension(definition.Path, args[len(route):])
	if err != nil {
		fmt.Fprintln(errOut, "dots: external command launch failed")
		return 1
	}
	return code
}

func commandPrefix(args []string) ([]string, []string, error) {
	roots := []string{}
	for len(args) > 0 && args[0] == "--command-dir" {
		if len(args) < 2 || args[1] == "" || strings.HasPrefix(args[1], "-") || len(roots) == dispatch.MaxCommandRoots {
			return nil, nil, fmt.Errorf("invalid command roots")
		}
		roots = append(roots, args[1])
		args = args[2:]
	}
	return roots, args, nil
}

func commandList(out io.Writer, r *dispatch.Registry, definitions []extension.Definition, check bool) int {
	var text strings.Builder
	for _, m := range r.Project() {
		if check || !m.Hidden {
			fmt.Fprintf(&text, "%s: %s [built-in]\n", m.Synopsis, m.Summary)
		}
	}
	for _, d := range definitions {
		m := d.Metadata.Projection()
		if !check && m.Hidden {
			continue
		}
		status := "external, declared read-only"
		if d.Availability != nil {
			status = d.Availability.Error()
		}
		fmt.Fprintf(&text, "%s: %s [%s]\n", strings.Join(m.Route, " "), m.Summary, status)
	}
	if check {
		text.WriteString("Command metadata validation passed.\n")
	}
	_, err := io.WriteString(out, text.String())
	return outputStatus(err)
}

func externalHelp(out io.Writer, d *extension.Definition) int {
	m := d.Metadata.Projection()
	var text strings.Builder
	fmt.Fprintf(&text, "Usage: dots %s\n\n%s\n", m.Synopsis, m.Summary)
	for _, example := range m.Examples {
		fmt.Fprintf(&text, "  %s\n", example)
	}
	text.WriteString("\nExternal command; read-only is an author declaration.\n")
	if d.Availability != nil {
		fmt.Fprintf(&text, "Unavailable: %s\n", d.Availability)
	}
	_, err := io.WriteString(out, text.String())
	return outputStatus(err)
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
				if id == "doctor" {
					text.WriteString("No configuration contents are read and no capabilities are probed by writing files.\n")
				} else {
					text.WriteString("Reads static metadata only; no extensions are executed.\n")
				}
			}
		}
	} else {
		text.WriteString("Usage: dots [--command-dir <absolute-trusted-root>]... <command or global option>\n\n")
		for _, m := range metadata {
			if !m.Hidden {
				fmt.Fprintf(&text, "  %-30s %s\n", m.Synopsis, m.Summary)
			}
		}
		text.WriteString("\nDevelopment binary; use commands to discover explicitly selected extensions. No installation or managed-file operations are implemented.\n")
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
