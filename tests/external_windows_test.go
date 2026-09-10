package tests

import (
	"context"
	"os"
	"os/exec"
	"os/signal"
	"strconv"
	"syscall"
	"testing"
	"time"
)

// Each helper owns a new real Windows console. GenerateConsoleCtrlEvent is
// called from that console and broadcasts to wrapper and extension together.
func TestWindowsConsoleInterruption(t *testing.T) {
	for _, event := range []string{"0", "1"} {
		t.Run(map[string]string{"0": "CtrlC", "1": "CtrlBreak"}[event], func(t *testing.T) {
			bin, root := externalFixture(t)
			ctx, cancel := context.WithTimeout(context.Background(), 20*time.Second)
			defer cancel()
			self, err := os.Executable()
			if err != nil {
				t.Fatal(err)
			}
			cmd := exec.CommandContext(ctx, self, "-test.run=^TestWindowsConsoleHelper$", "-test.timeout=15s")
			cmd.Env = append(os.Environ(), "DOTS_CONSOLE_HELPER=1", "DOTS_CONSOLE_EVENT="+event, "DOTS_CONSOLE_BIN="+bin, "DOTS_CONSOLE_ROOT="+root)
			cmd.SysProcAttr = &syscall.SysProcAttr{CreationFlags: 0x10} // CREATE_NEW_CONSOLE, not CREATE_NEW_PROCESS_GROUP
			out, err := cmd.CombinedOutput()
			if err != nil {
				t.Fatalf("native console acceptance failed: %v %s", err, out)
			}
		})
	}
}
func TestWindowsConsoleHelper(t *testing.T) {
	if os.Getenv("DOTS_CONSOLE_HELPER") != "1" {
		return
	}
	events := make(chan os.Signal, 8)
	signal.Notify(events, os.Interrupt)
	defer signal.Stop(events)
	cmd, r := signalProcess(t, os.Getenv("DOTS_CONSOLE_BIN"), os.Getenv("DOTS_CONSOLE_ROOT"))
	_ = readyPID(t, r)
	event, err := strconv.Atoi(os.Getenv("DOTS_CONSOLE_EVENT"))
	if err != nil {
		t.Fatal(err)
	}
	ok, _, err := syscall.NewLazyDLL("kernel32.dll").NewProc("GenerateConsoleCtrlEvent").Call(uintptr(event), 0)
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
