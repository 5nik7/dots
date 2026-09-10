package tests

import (
	"bufio"
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

func externalFixture(t *testing.T) (string, string) {
	t.Helper()
	bin, fixture := os.Getenv("DOTS_CORE_TEST_BIN"), os.Getenv("DOTS_EXTENSION_TEST_BIN")
	if !filepath.IsAbs(bin) || !filepath.IsAbs(fixture) {
		t.Fatal("use isolated core verifier")
	}
	root := filepath.Join(t.TempDir(), "-trusted space 日本語")
	if err := os.Mkdir(root, 0700); err != nil {
		t.Fatal(err)
	}
	data, err := os.ReadFile(fixture)
	if err != nil {
		t.Fatal(err)
	}
	suffix := ""
	if runtime.GOOS == "windows" {
		suffix = ".exe"
	}
	for _, route := range []string{"probe", "probe-child"} {
		if err = os.WriteFile(filepath.Join(root, "dots-"+route+suffix), data, 0700); err != nil {
			t.Fatal(err)
		}
		m := map[string]any{"schema_version": 1, "route": strings.Split(route, "-"), "summary": "Disposable fixture", "synopsis": strings.ReplaceAll(route, "-", " ") + " [args]", "examples": []string{"dots " + strings.ReplaceAll(route, "-", " ")}, "platforms": []string{"termux", "linux", "windows"}, "hidden": false, "outputs": []any{map[string]any{"format": "json", "schema_version": 1}}, "mutation": "read-only", "aliases": []string{}, "capabilities": []string{}}
		b, _ := json.Marshal(m)
		if err = os.WriteFile(filepath.Join(root, "dots-"+route+".json"), b, 0600); err != nil {
			t.Fatal(err)
		}
	}
	return bin, root
}
func fixtureEnv(mode string) []string {
	// The verifier already owns HOME/config/state/cache and all Go configuration.
	env := []string{}
	for _, entry := range os.Environ() {
		if !strings.HasPrefix(entry, "PATH=") && !strings.HasPrefix(entry, "DOTS_FIXTURE_") {
			env = append(env, entry)
		}
	}
	return append(env, "PATH=", "DOTS_FIXTURE_MODE="+mode, "DOTS_FIXTURE_SENTINEL=forwarded 日本語", "DOTS_FIXTURE_EXIT=37")
}
func TestExternalProcessContract(t *testing.T) {
	bin, root := externalFixture(t)
	forwarded := []string{"--", "--help", "-h", "--command-dir", "", "a b", "日本語", `quote"inside`, `back\slash\`, `tail space\`, "a&b|c%PATH%!x!^", "--version"}
	ctx, cancel := context.WithTimeout(context.Background(), 15*time.Second)
	defer cancel()
	cmd := exec.CommandContext(ctx, bin, append([]string{"--command-dir", root, "probe", "child"}, forwarded...)...)
	cmd.Env = fixtureEnv("echo")
	cmd.Dir = root
	cmd.Stdin = strings.NewReader("stdin\x00日本語\n")
	var out, stderr bytes.Buffer
	cmd.Stdout = &out
	cmd.Stderr = &stderr
	err := cmd.Run()
	exit, ok := err.(*exec.ExitError)
	if !ok || exit.ExitCode() != 37 {
		t.Fatalf("exit: %v stderr: %s", err, stderr.String())
	}
	var got struct {
		Args                 []string
		Input, Cwd, Sentinel string
	}
	if json.Unmarshal(out.Bytes(), &got) != nil {
		t.Fatal(out.String())
	}
	if !reflect.DeepEqual(got.Args, forwarded) || got.Input != "stdin\x00日本語\n" || got.Cwd != root || got.Sentinel != "forwarded 日本語" || stderr.String() != "fixture stderr\n" {
		t.Fatalf("forwarding: %+v %s", got, stderr.String())
	}
	before := snapshot(t, root)
	for _, args := range [][]string{{"probe", "--help"}, {"probe", "child", "-h"}, {"probe", "child", "--option", "--help"}, {"commands"}, {"commands", "--check"}} {
		cmd = exec.CommandContext(ctx, bin, append([]string{"--command-dir", root}, args...)...)
		cmd.Env = fixtureEnv("echo")
		cmd.Dir = root
		output, err := cmd.CombinedOutput()
		if err != nil || bytes.Contains(output, []byte("fixture stderr")) || bytes.Contains(output, []byte("Sentinel")) {
			t.Fatalf("static path executed fixture: %v %s", err, output)
		}
	}
	if !reflect.DeepEqual(before, snapshot(t, root)) {
		t.Fatal("static discovery/help mutated roots")
	}
	// No implicit PATH discovery, even with valid definitions in cwd and PATH.
	cmd = exec.CommandContext(ctx, bin, "probe")
	cmd.Dir = root
	cmd.Env = append(fixtureEnv("noop"), "PATH="+root)
	if err = cmd.Run(); err == nil || cmd.ProcessState.ExitCode() != 2 {
		t.Fatal("implicit search", err)
	}
	// An invalid deeper definition refuses fallback and never invokes the fixture.
	if err = os.WriteFile(filepath.Join(root, "dots-probe-child.json"), []byte("invalid"), 0600); err != nil {
		t.Fatal(err)
	}
	cmd = exec.CommandContext(ctx, bin, "--command-dir", root, "probe", "child")
	cmd.Env = fixtureEnv("echo")
	output, err := cmd.CombinedOutput()
	if err == nil || cmd.ProcessState.ExitCode() != 1 || !bytes.Contains(output, []byte("invalid external metadata")) {
		t.Fatalf("fallback: %v %s", err, output)
	}
}

// Start a signal-aware fixture and wait until its native handler is ready.
func signalProcess(t *testing.T, bin, root string) (*exec.Cmd, *bufio.Reader) {
	t.Helper()
	cmd := exec.Command(bin, "--command-dir", root, "probe")
	cmd.Env = fixtureEnv("wait")
	cmd.Dir = root
	cmd.Stderr = os.Stderr
	pipe, err := cmd.StdoutPipe()
	if err != nil {
		t.Fatal(err)
	}
	if err = cmd.Start(); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = cmd.Process.Kill() })
	return cmd, bufio.NewReader(pipe)
}
func readyPID(t *testing.T, r *bufio.Reader) int {
	t.Helper()
	line, err := r.ReadString('\n')
	if err != nil {
		t.Fatal("readiness", err)
	}
	var pid int
	if _, err = fmt.Sscan(line, &pid); err != nil {
		t.Fatal(err)
	}
	return pid
}
func interruptedExit(t *testing.T, cmd *exec.Cmd, r *bufio.Reader) {
	t.Helper()
	line, err := r.ReadString('\n')
	if err != nil || line != "interrupted\n" {
		t.Fatalf("signal not handled: %q %v", line, err)
	}
	err = cmd.Wait()
	exit, ok := err.(*exec.ExitError)
	if !ok || exit.ExitCode() != 23 {
		t.Fatalf("wrapper failed to await native exit: %v", err)
	}
}
