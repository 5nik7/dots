package cli

import (
	"bytes"
	"github.com/5nik7/dots/internal/platform"
	"strings"
	"testing"
)

func TestBuiltinsPrecedeRootHealth(t *testing.T) {
	for _, args := range [][]string{{"--help"}, {"--version"}, {"doctor", "--help"}, {"commands", "--help"}, {"doctor", "--json"}} {
		var out, errOut bytes.Buffer
		all := append([]string{"--command-dir", "missing-relative-root"}, args...)
		code := Run(all, &out, &errOut, func() string { return "" }, func() platform.Report { return platform.Report{SchemaVersion: 1} })
		if code != 0 || errOut.Len() != 0 {
			t.Fatal(args, code, errOut.String())
		}
	}
	for _, args := range [][]string{{"--command-dir"}, {"--command-dir", ""}, {"--command-dir=x", "files"}} {
		var out, errOut bytes.Buffer
		if code := Run(args, &out, &errOut, nil, nil); code != 2 {
			t.Fatal(args, code)
		}
	}
	var out, errOut bytes.Buffer
	if code := Run([]string{"--command-dir", "relative-secret", "files"}, &out, &errOut, nil, func() platform.Report { return platform.Report{Platform: "linux"} }); code != 1 || strings.Contains(errOut.String(), "secret") {
		t.Fatal(code, errOut.String())
	}
}
