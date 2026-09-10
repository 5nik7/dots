//go:build unix

package tests

import (
	"os"
	"syscall"
	"testing"
	"time"
)

func TestUnixNativeInterruption(t *testing.T) {
	for _, sig := range []os.Signal{os.Interrupt, syscall.SIGTERM} {
		t.Run(sig.String(), func(t *testing.T) {
			bin, root := externalFixture(t)
			cmd, r := signalProcess(t, bin, root)
			timer := time.AfterFunc(10*time.Second, func() { _ = cmd.Process.Kill() })
			defer timer.Stop()
			if pid := readyPID(t, r); pid != cmd.Process.Pid {
				t.Fatal("Unix dispatcher did not replace its process", pid, cmd.Process.Pid)
			}
			if err := cmd.Process.Signal(sig); err != nil {
				t.Fatal(err)
			}
			interruptedExit(t, cmd, r)
		})
	}
}
