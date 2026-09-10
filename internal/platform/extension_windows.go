package platform

import (
	"errors"
	"os"
	"os/exec"
	"os/signal"
	"path/filepath"
	"strings"
	"syscall"
	"unsafe"
)

var extensionKernel = syscall.NewLazyDLL("kernel32.dll")

func extensionRootSyntax(path string) error {
	volume := filepath.VolumeName(path)
	if len(volume) != 2 || volume[1] != ':' || strings.Contains(path[2:], ":") || strings.HasPrefix(path, `\\`) {
		return errors.New("only local absolute drive paths are supported")
	}
	return nil
}

func extensionRootPolicy(path string) error {
	drive, _ := syscall.UTF16PtrFromString(filepath.VolumeName(path) + `\`)
	kind, _, _ := extensionKernel.NewProc("GetDriveTypeW").Call(uintptr(unsafe.Pointer(drive)))
	if kind != 3 {
		return errors.New("only fixed-drive command roots are supported")
	}
	f, err := os.Open(path)
	if err != nil {
		return err
	}
	defer f.Close()
	var fs [64]uint16
	ok, _, _ := extensionKernel.NewProc("GetVolumeInformationByHandleW").Call(f.Fd(), 0, 0, 0, 0, 0, uintptr(unsafe.Pointer(&fs[0])), uintptr(len(fs)))
	if ok == 0 || syscall.UTF16ToString(fs[:]) != "NTFS" {
		return errors.New("only NTFS command roots are supported")
	}
	var flags uint32
	ok, _, _ = extensionKernel.NewProc("GetFileInformationByHandleEx").Call(f.Fd(), 23, uintptr(unsafe.Pointer(&flags)), unsafe.Sizeof(flags))
	if ok == 0 || flags&1 != 0 {
		return errors.New("case-sensitive or unqueryable command directory is unsupported")
	}
	return nil
}

func extensionFilePolicy(path string, _ os.FileInfo, _ bool) error {
	ptr, err := syscall.UTF16PtrFromString(path)
	if err != nil {
		return err
	}
	attrs, err := syscall.GetFileAttributes(ptr)
	if err != nil {
		return err
	}
	if attrs&syscall.FILE_ATTRIBUTE_REPARSE_POINT != 0 {
		return errors.New("reparse command entries are unsupported")
	}
	return nil
}

func ExecuteExtension(path string, args []string) (int, error) {
	// Do not create a process group or disable Ctrl+C inheritance. Console events
	// reach both processes; consume only the wrapper's event while waiting.
	events := make(chan os.Signal, 8)
	signal.Notify(events, os.Interrupt)
	defer signal.Stop(events)
	cmd := exec.Command(path, args...)
	cmd.Stdin = os.Stdin
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	if err := cmd.Start(); err != nil {
		return 1, err
	}
	err := cmd.Wait()
	if err == nil {
		return 0, nil
	}
	var exited *exec.ExitError
	if errors.As(err, &exited) {
		return exited.ExitCode(), nil
	}
	return 1, err
}
