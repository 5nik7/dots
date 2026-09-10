package tests

import (
	"bytes"
	"context"
	"io"
	"os"
	"os/exec"
	"os/signal"
	"path/filepath"
	"strconv"
	"strings"
	"syscall"
	"testing"
	"time"
)

var testKernel = syscall.NewLazyDLL("kernel32.dll")

// The helper is blocked on stdin until it belongs to this test-owned job.
// All subsequent wrapper/fixture children inherit job membership. Terminating
// the job cleans up descendants even if the helper or wrapper already exited.
func consoleRun(t *testing.T, event, stall string) (string, error, time.Duration) {
	t.Helper()
	bin, root := externalFixture(t)
	job, _, err := testKernel.NewProc("CreateJobObjectW").Call(0, 0)
	if job == 0 {
		t.Fatal("CreateJobObjectW", err)
	}
	terminate := func() {
		ok, _, e := testKernel.NewProc("TerminateJobObject").Call(job, 94)
		if ok == 0 {
			t.Errorf("TerminateJobObject: %v", e)
		}
	}
	defer syscall.CloseHandle(syscall.Handle(job))
	defer terminate()
	ctx, cancel := context.WithTimeout(context.Background(), 12*time.Second)
	defer cancel()
	self, err := os.Executable()
	if err != nil {
		t.Fatal(err)
	}
	cmd := exec.CommandContext(ctx, self, "-test.run=^TestWindowsConsoleHelper$", "-test.timeout=11s")
	cmd.Env = append(os.Environ(), "DOTS_CONSOLE_HELPER=1", "DOTS_CONSOLE_EVENT="+event, "DOTS_CONSOLE_STALL="+stall, "DOTS_CONSOLE_BIN="+bin, "DOTS_CONSOLE_ROOT="+root)
	cmd.SysProcAttr = &syscall.SysProcAttr{CreationFlags: 0x10} // real new console; no new process group
	cmd.WaitDelay = 500 * time.Millisecond                      // bound copier waits on inherited output pipes
	var output bytes.Buffer
	cmd.Stdout = &output
	cmd.Stderr = &output
	gate, err := cmd.StdinPipe()
	if err != nil {
		t.Fatal(err)
	}
	defer gate.Close()
	start := time.Now()
	if err = cmd.Start(); err != nil {
		t.Fatal(err)
	}
	// Ensure the immediate child is reaped on every early failure, too.
	defer func() { terminate(); _ = cmd.Process.Kill(); _ = cmd.Wait() }()
	handle, err := syscall.OpenProcess(0x100|0x1, false, uint32(cmd.Process.Pid)) // SET_QUOTA | TERMINATE
	if err != nil {
		t.Fatal(err)
	}
	ok, _, assignErr := testKernel.NewProc("AssignProcessToJobObject").Call(job, uintptr(handle))
	syscall.CloseHandle(handle)
	if ok == 0 {
		t.Fatal("AssignProcessToJobObject", assignErr)
	}
	if _, err = io.WriteString(gate, "go"); err != nil {
		t.Fatal(err)
	}
	_ = gate.Close()
	var fixture syscall.Handle
	if stall != "" {
		// Open a stable handle while the known fixture is alive; checking a PID
		// after cleanup could mistake reuse for a surviving process.
		deadline := time.Now().Add(3 * time.Second)
		for time.Now().Before(deadline) {
			data, readErr := os.ReadFile(filepath.Join(root, "fixture.pid"))
			if readErr == nil {
				pid, parseErr := strconv.ParseUint(string(data), 10, 32)
				if parseErr == nil {
					fixture, err = syscall.OpenProcess(0x100000, false, uint32(pid))
					if err != nil {
						t.Fatal(err)
					}
					break
				}
			} else if !os.IsNotExist(readErr) {
				t.Fatal(readErr)
			}
			time.Sleep(10 * time.Millisecond)
		}
		if fixture == 0 {
			t.Fatal("fixture never published its test-only process identity")
		}
		defer syscall.CloseHandle(fixture)
	}
	err = cmd.Wait()
	terminate()
	if fixture != 0 {
		status, waitErr := syscall.WaitForSingleObject(fixture, 2000)
		if waitErr != nil || status != syscall.WAIT_OBJECT_0 {
			t.Fatalf("fixture still running after cleanup: status=%d err=%v", status, waitErr)
		}
	}
	return output.String(), err, time.Since(start)
}

func TestWindowsConsoleInterruption(t *testing.T) {
	for _, event := range []string{"0", "1"} {
		t.Run(map[string]string{"0": "CtrlC", "1": "CtrlBreak"}[event], func(t *testing.T) {
			out, err, _ := consoleRun(t, event, "")
			if err != nil {
				t.Fatalf("native console acceptance failed: %v %s", err, out)
			}
		})
	}
}

func TestWindowsConsoleFailureCleanup(t *testing.T) {
	for _, stall := range []string{"stall-ready", "stall-interrupt"} {
		t.Run(stall, func(t *testing.T) {
			out, err, elapsed := consoleRun(t, "0", stall)
			expected := "readiness"
			if stall == "stall-interrupt" {
				expected = "signal not handled"
			}
			if err == nil || !strings.Contains(out, expected) || !strings.Contains(out, "i/o timeout") {
				t.Fatalf("did not fail at bounded pipe read: %v %s", err, out)
			}
			// Less than the fixture's independent eight-second watchdog: job cleanup,
			// not waiting for self-expiry, must release the inherited pipes and process.
			if elapsed >= 6*time.Second {
				t.Fatalf("failure cleanup exceeded six-second deadline: %v", elapsed)
			}
			t.Logf("%s failed and fixture handle signaled within %v", stall, elapsed)
		})
	}
}

func TestWindowsConsoleHelper(t *testing.T) {
	if os.Getenv("DOTS_CONSOLE_HELPER") != "1" {
		return
	}
	token, err := io.ReadAll(os.Stdin)
	if err != nil || string(token) != "go" {
		t.Fatal("job startup gate", err)
	}
	events := make(chan os.Signal, 8)
	signal.Notify(events, os.Interrupt)
	defer signal.Stop(events)
	mode := os.Getenv("DOTS_CONSOLE_STALL")
	if mode == "" {
		mode = "wait"
	}
	root := os.Getenv("DOTS_CONSOLE_ROOT")
	cmd, r := signalProcess(t, os.Getenv("DOTS_CONSOLE_BIN"), root, "DOTS_FIXTURE_MODE="+mode, "DOTS_FIXTURE_PID_FILE="+filepath.Join(root, "fixture.pid"))
	_ = readyPID(t, r)
	event, err := strconv.Atoi(os.Getenv("DOTS_CONSOLE_EVENT"))
	if err != nil {
		t.Fatal(err)
	}
	ok, _, err := testKernel.NewProc("GenerateConsoleCtrlEvent").Call(uintptr(event), 0)
	if ok == 0 {
		t.Fatal("GenerateConsoleCtrlEvent", err)
	}
	interruptedExit(t, cmd, r)
	select {
	case <-events:
	case <-time.After(2 * time.Second):
		t.Fatal("helper did not receive console broadcast")
	}
}
