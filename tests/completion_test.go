package tests

import (
	"bytes"
	"context"
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

func TestCompletionGenerationProcess(t *testing.T) {
	bin, root := externalFixture(t)
	editCatalogSidecar(t, root, "probe-child", func(m map[string]any) {
		m["hidden"] = true
		m["summary"] = "$(print PWNED) `print PWNED` ' ; <日本語>"
	})
	before := snapshot(t, root)
	code, out, stderr := catalogRun(t, bin, root, "--command-dir", root, "completion", "zsh")
	if code != 0 || stderr != "" || bytes.Contains(out, []byte("PWNED")) || bytes.Contains(out, []byte("'probe child'")) || !bytes.Contains(out, []byte("'probe'")) {
		t.Fatal(code, string(out), stderr)
	}
	if !reflect.DeepEqual(before, snapshot(t, root)) {
		t.Fatal("generation mutated roots")
	}
	editCatalogSidecar(t, root, "probe-child", func(m map[string]any) { m["unknown"] = true })
	before = snapshot(t, root)
	code, out, stderr = catalogRun(t, bin, root, "--command-dir", root, "completion", "zsh")
	if code != 1 || len(out) != 0 || stderr == "" {
		t.Fatal("partial generation", code, string(out), stderr)
	}
	if !reflect.DeepEqual(before, snapshot(t, root)) {
		t.Fatal("failure mutated roots")
	}
}

func shellQuote(s string) string { return "'" + strings.ReplaceAll(s, "'", "'\\''") + "'" }

func zshRun(t *testing.T, root, script string, args ...string) string {
	t.Helper()
	shell := os.Getenv("DOTS_ZSH_TEST_BIN")
	if !filepath.IsAbs(shell) {
		t.Fatal("isolated runner must supply installed Zsh")
	}
	ctx, cancel := context.WithTimeout(context.Background(), 15*time.Second)
	defer cancel()
	cmd := exec.CommandContext(ctx, shell, append([]string{"-f", "-c", script, "fixture"}, args...)...)
	cmd.Dir = root
	cmd.Env = []string{"PATH=", "HOME=" + root, "ZDOTDIR=" + root, "XDG_CONFIG_HOME=" + root, "XDG_DATA_HOME=" + root, "XDG_STATE_HOME=" + root, "XDG_CACHE_HOME=" + root, "TMPDIR=" + root, "LANG=C.UTF-8", "TERM=xterm"}
	cmd.WaitDelay = time.Second
	var out, stderr bytes.Buffer
	cmd.Stdout = &out
	cmd.Stderr = &stderr
	if err := cmd.Run(); err != nil || stderr.Len() != 0 {
		t.Fatalf("Zsh failed: %v stdout=%q stderr=%q", err, out.String(), stderr.String())
	}
	return out.String()
}

func TestZshCompletionRuntime(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("native Windows verifies generation, not Zsh runtime")
	}
	bin, root := externalFixture(t)
	// Two ordered roots, including shell metacharacters. Move the child so both
	// roots contribute visible routes; no selected extension may execute.
	second := filepath.Join(t.TempDir(), "-space 日本語 ' $(print PWNED) `print PWNED`")
	if err := os.Mkdir(second, 0700); err != nil {
		t.Fatal(err)
	}
	for _, name := range []string{"dots-probe-child", "dots-probe-child.json"} {
		if err := os.Rename(filepath.Join(root, name), filepath.Join(second, name)); err != nil {
			t.Fatal(err)
		}
	}
	editCatalogSidecar(t, second, "probe-child", func(m map[string]any) { m["summary"] = "$(print PWNED) ' `print PWNED`" })
	code, data, stderr := catalogRun(t, bin, root, "--command-dir", root, "--command-dir", second, "completion", "zsh")
	if code != 0 || stderr != "" {
		t.Fatal(code, stderr)
	}
	script := filepath.Join(t.TempDir(), "completion.zsh")
	if err := os.WriteFile(script, data, 0600); err != nil {
		t.Fatal(err)
	}
	shellRoot := t.TempDir()
	// Startup files are poison: -f must not load them.
	if err := os.WriteFile(filepath.Join(shellRoot, ".zshrc"), []byte("print PWNED"), 0600); err != nil {
		t.Fatal(err)
	}
	before, other, shellBefore := snapshot(t, root), snapshot(t, second), snapshot(t, shellRoot)
	builtin := "--help\n--version\n-h\ncommands\ncompletion\ndoctor\nhelp\n"
	prefix := []string{"dots", "--command-dir", root, "--command-dir", second}
	cases := []struct {
		name  string
		words []string
		want  string
	}{
		{"builtin", []string{"dots", ""}, builtin},
		{"partial", []string{"dots", "do"}, "doctor\n"},
		{"matching", append(append([]string{}, prefix...), ""), builtin + "probe\n"},
		{"nested", append(append([]string{}, prefix...), "probe", ""), "child\n"},
		{"leaf", append(append([]string{}, prefix...), "probe", "child", ""), ""},
		{"argument", append(append([]string{}, prefix...), "probe", "value", ""), ""},
		{"terminator", append(append([]string{}, prefix...), "probe", "--", ""), ""},
		{"flag", append(append([]string{}, prefix...), "probe", "--help", ""), ""},
		{"root-order", []string{"dots", "--command-dir", second, "--command-dir", root, ""}, builtin},
		{"root-spelling", []string{"dots", "--command-dir", root + "/", "--command-dir", second, ""}, builtin},
		{"root-count", []string{"dots", "--command-dir", root, ""}, builtin},
		{"root-value", []string{"dots", "--command-dir", ""}, ""},
		{"bad-value", []string{"dots", "--command-dir", "--bad", ""}, ""},
		{"no-prefix-after-route", []string{"dots", "doctor", "--command-dir", root, ""}, ""},
		{"no-flag-grammar", []string{"dots", "doctor", "--"}, ""},
		{"no-shell-grammar", []string{"dots", "completion", ""}, ""},
		{"global-terminal", []string{"dots", "--version", ""}, ""},
	}
	tooMany := []string{"dots"}
	for i := 0; i < 9; i++ {
		tooMany = append(tooMany, "--command-dir", root)
	}
	cases = append(cases, struct {
		name  string
		words []string
		want  string
	}{"root-limit", append(tooMany, ""), ""})
	// Native Zsh executes the actual generated function. Capture its compadd
	// boundary here; the separate ZLE test exercises the real compadd builtin.
	driver := `source "$1"
 shift
 compadd() { shift; (( $# )) && print -rl -- "$@"; }
 words=( "$@" )
 CURRENT=$#words
 PREFIX=$words[CURRENT]
 _dots
 `
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			got := zshRun(t, shellRoot, driver, append([]string{script}, tc.words...)...)
			if got != tc.want {
				t.Fatalf("got %q want %q", got, tc.want)
			}
		})
	}
	// Quoted completion words must match the decoded literal root values.
	quoted := append([]string{}, prefix...)
	quoted[2] = shellQuote(root)
	quoted[4] = shellQuote(second)
	got := zshRun(t, shellRoot, driver, append([]string{script}, append(quoted, "probe", "")...)...)
	if got != "child\n" {
		t.Fatal("quoted context", got)
	}
	if !reflect.DeepEqual(before, snapshot(t, root)) || !reflect.DeepEqual(other, snapshot(t, second)) || !reflect.DeepEqual(shellBefore, snapshot(t, shellRoot)) {
		t.Fatal("Zsh mutated owned roots")
	}
	t.Logf("real Zsh candidate cases: %d plus quoted root context", len(cases))
}

func TestZshNativeCompletion(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("native Zsh runtime is Termux/Linux only")
	}
	bin, root := externalFixture(t)
	code, data, stderr := catalogRun(t, bin, root, "completion", "zsh")
	if code != 0 || stderr != "" {
		t.Fatal(code, stderr)
	}
	script := filepath.Join(t.TempDir(), "completion.zsh")
	if err := os.WriteFile(script, data, 0600); err != nil {
		t.Fatal(err)
	}
	shellRoot := t.TempDir()
	before := snapshot(t, shellRoot)
	// A real ZLE completion widget provides compadd's required native context.
	// Capture the builtin's filtered matches rather than terminal display layout.
	setup := fmt.Sprintf(`autoload -Uz compinit; compinit -i -D; source %s; compadd() { local -a found; builtin compadd -A found "$@"; print -r -- "MATCHES:${(j:,:)found}:END"; }; bindkey '^I' complete-word; PS1='READY>'; print SETUP_DONE`, shellQuote(script))
	driver := `zmodload zsh/zpty
 zmodload zsh/zselect
 zpty -b child "$1" -f
 zpty -w child "$2"
 local line all=''
 integer n
 for ((n=0;n<300;n++)); do
   while zpty -r child line; do all+=$line; done
   [[ $all == *SETUP_DONE*READY\>* ]] && break
   zselect -t 1
 done
 zpty -w -n child $'dots do\t'
 all=''
 for ((n=0;n<300;n++)); do
   while zpty -r child line; do all+=$line; done
   [[ $all == *MATCHES:doctor:END* ]] && break
   zselect -t 1
 done
 zpty -d child
 [[ $all == *MATCHES:doctor:END* ]] || { print -ru2 -- 'native completion missing'; exit 1; }
 print -r -- native-completion-passed
 `
	if got := zshRun(t, shellRoot, driver, os.Getenv("DOTS_ZSH_TEST_BIN"), setup); got != "native-completion-passed\n" {
		t.Fatal(got)
	}
	if !reflect.DeepEqual(before, snapshot(t, shellRoot)) {
		t.Fatal("native completion mutated root")
	}
}
