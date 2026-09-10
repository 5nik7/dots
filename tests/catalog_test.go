package tests

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"reflect"
	"runtime"
	"strings"
	"testing"
	"time"
)

func catalogRun(t *testing.T, bin, cwd string, args ...string) (int, []byte, string) {
	t.Helper()
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	cmd := exec.CommandContext(ctx, bin, args...)
	cmd.Env = fixtureEnv("echo")
	cmd.Dir = cwd
	cmd.WaitDelay = 500 * time.Millisecond
	var out, stderr bytes.Buffer
	cmd.Stdout = &out
	cmd.Stderr = &stderr
	err := cmd.Run()
	if ctx.Err() != nil || cmd.ProcessState == nil {
		t.Fatal("catalog deadline/start", err)
	}
	return cmd.ProcessState.ExitCode(), out.Bytes(), stderr.String()
}
func editCatalogSidecar(t *testing.T, root, route string, change func(map[string]any)) {
	t.Helper()
	p := filepath.Join(root, "dots-"+route+".json")
	data, err := os.ReadFile(p)
	if err != nil {
		t.Fatal(err)
	}
	var m map[string]any
	if json.Unmarshal(data, &m) != nil {
		t.Fatal("fixture metadata")
	}
	change(m)
	data, err = json.Marshal(m)
	if err != nil {
		t.Fatal(err)
	}
	if err = os.WriteFile(p, data, 0600); err != nil {
		t.Fatal(err)
	}
}
func TestCatalogProcess(t *testing.T) {
	bin, root := externalFixture(t)
	editCatalogSidecar(t, root, "probe-child", func(m map[string]any) {
		m["hidden"] = true
		m["platforms"] = []string{"wsl"}
		m["summary"] = `日本語 "quoted" <metadata>`
	})
	before := snapshot(t, root)
	code, out, stderr := catalogRun(t, bin, root, "--command-dir", root, "commands", "--json")
	if code != 0 || stderr != "" {
		t.Fatal(code, stderr, string(out))
	}
	var c struct {
		SchemaVersion int `json:"schema_version"`
		Commands      []struct {
			Kind, ID, Summary string
			Hidden            bool
			Availability      struct {
				Status string
				Reason *string
			}
		}
	}
	if json.Unmarshal(out, &c) != nil || c.SchemaVersion != 1 || len(c.Commands) != 7 {
		t.Fatal(string(out))
	}
	if c.Commands[5].ID != "probe" || c.Commands[5].Availability.Status != "available" || c.Commands[5].Availability.Reason != nil || c.Commands[6].ID != "probe-child" || !c.Commands[6].Hidden || c.Commands[6].Availability.Reason == nil || *c.Commands[6].Availability.Reason != "unavailable" || c.Commands[6].Summary != `日本語 "quoted" <metadata>` {
		t.Fatal(string(out))
	}
	if bytes.Contains(out, []byte(root)) || bytes.Contains(out, []byte("fixture stderr")) || bytes.Contains(out, []byte("Sentinel")) {
		t.Fatal("executed fixture or leaked internal path")
	}
	code, text, stderr := catalogRun(t, bin, root, "--command-dir", root, "commands")
	if code != 0 || stderr != "" || bytes.Contains(text, []byte("probe child")) {
		t.Fatal("changed hidden text policy")
	}
	code, noRoots, stderr := catalogRun(t, bin, root, "commands", "--json")
	if code != 0 || stderr != "" || bytes.Contains(noRoots, []byte(`"external"`)) {
		t.Fatal("implicit root")
	}
	if !reflect.DeepEqual(before, snapshot(t, root)) {
		t.Fatal("static catalog mutated roots")
	}
	second := t.TempDir()
	// Move the deeper definition into another selected root; enumeration/insertion
	// and root order must not affect the successful catalog bytes.
	for _, entry := range []string{"dots-probe-child.json", "dots-probe-child" + map[bool]string{true: ".exe"}[runtime.GOOS == "windows"]} {
		if err := os.Rename(filepath.Join(root, entry), filepath.Join(second, entry)); err != nil {
			t.Fatal(err)
		}
	}
	moved := snapshot(t, root)
	other := snapshot(t, second)
	for _, roots := range [][]string{{root, second}, {second, root}} {
		code, again, stderr := catalogRun(t, bin, root, "--command-dir", roots[0], "--command-dir", roots[1], "commands", "--json")
		if code != 0 || stderr != "" || !bytes.Equal(out, again) {
			t.Fatal("root order changed catalog", code, stderr)
		}
	}
	if !reflect.DeepEqual(moved, snapshot(t, root)) || !reflect.DeepEqual(other, snapshot(t, second)) {
		t.Fatal("discovery mutated fixture roots")
	}

}

func TestCatalogValidationProcess(t *testing.T) {
	for _, kind := range []string{"missing-native", "unsupported", "invalid-hidden", "duplicate-root", "duplicate-route", "missing-root", "entry", "entry-limit", "definition-limit"} {
		t.Run(kind, func(t *testing.T) {
			bin, root := externalFixture(t)
			roots := []string{root}
			want := 1
			native := "dots-probe"
			if runtime.GOOS == "windows" {
				native += ".exe"
			}
			switch kind {
			case "missing-native", "unsupported":
				if err := os.Remove(filepath.Join(root, native)); err != nil {
					t.Fatal(err)
				}
				if kind == "unsupported" {
					if err := os.WriteFile(filepath.Join(root, "dots-probe.cmd"), []byte("poison"), 0600); err != nil {
						t.Fatal(err)
					}
				}
				want = 0
			case "invalid-hidden":
				editCatalogSidecar(t, root, "probe-child", func(m map[string]any) { m["hidden"] = true; m["unknown"] = true })
			case "duplicate-root":
				roots = append(roots, root)
			case "duplicate-route":
				_, other := externalFixture(t)
				roots = append(roots, other)
			case "missing-root":
				roots = []string{filepath.Join(root, "SECRET-missing")}
			case "entry":
				if err := os.Remove(filepath.Join(root, native)); err != nil {
					t.Fatal(err)
				}
				if err := os.Mkdir(filepath.Join(root, native), 0700); err != nil {
					t.Fatal(err)
				}
			case "entry-limit":
				for i := 0; i < 4097; i++ {
					if err := os.WriteFile(filepath.Join(root, fmt.Sprintf("unrelated%d", i)), nil, 0600); err != nil {
						t.Fatal(err)
					}
				}
			case "definition-limit":
				for i := 0; i < 1025; i++ {
					if err := os.WriteFile(filepath.Join(root, fmt.Sprintf("dots-extra%d.json", i)), nil, 0600); err != nil {
						t.Fatal(err)
					}
				}
			}
			before := snapshot(t, root)
			args := []string{}
			for _, r := range roots {
				args = append(args, "--command-dir", r)
			}
			args = append(args, "commands", "--json")
			code, out, stderr := catalogRun(t, bin, root, args...)
			if code != want || strings.Contains(stderr, "SECRET") {
				t.Fatal(code, stderr)
			}
			if want == 1 {
				if len(out) != 0 || stderr == "" {
					t.Fatal("partial catalog", string(out), stderr)
				}
			} else {
				reason := "unavailable"
				if kind == "unsupported" {
					reason = "unsupported_launcher"
				}
				if stderr != "" || !json.Valid(out) || !bytes.Contains(out, []byte(`"reason": "`+reason+`"`)) {
					t.Fatal("availability", string(out), stderr)
				}
				// JSON is listing, not strict check; a current-platform missing launcher
				// still fails --check while valid unavailable JSON succeeds.
				args[len(args)-1] = "--check"
				code, _, _ = catalogRun(t, bin, root, args...)
				if code != 1 {
					t.Fatal("changed check semantics")
				}
			}
			completionArgs := append(append([]string{}, args[:len(args)-2]...), "completion", "zsh")
			completionCode, completion, completionErr := catalogRun(t, bin, root, completionArgs...)
			if completionCode != want || (want == 1 && (len(completion) != 0 || completionErr == "")) || (want == 0 && (completionErr != "" || bytes.Contains(completion, []byte("'probe'")))) {
				t.Fatal("completion validation/availability", completionCode, string(completion), completionErr)
			}
			if !reflect.DeepEqual(before, snapshot(t, root)) {
				t.Fatal("catalog mutated roots")
			}
		})
	}
}
