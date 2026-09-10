// Disposable verifier fixture. Never installed or used as a product command.
package main

import (
	"encoding/json"
	"fmt"
	"io"
	"os"
	"os/signal"
	"strconv"
	"time"
)

func main() {
	// Last-resort lifetime bound even if the test supervisor dies.
	time.AfterFunc(8*time.Second, func() { os.Exit(92) })
	mode := os.Getenv("DOTS_FIXTURE_MODE")
	switch mode {
	case "noop":
		return
	case "wait", "stall-ready", "stall-interrupt":
		signals := make(chan os.Signal, 2)
		signal.Notify(signals, os.Interrupt)
		additionalSignals(signals)
		if path := os.Getenv("DOTS_FIXTURE_PID_FILE"); path != "" {
			if err := os.WriteFile(path, []byte(strconv.Itoa(os.Getpid())), 0600); err != nil {
				os.Exit(93)
			}
		}
		if mode == "stall-ready" {
			select {}
		}
		fmt.Println(os.Getpid())
		<-signals
		if mode == "stall-interrupt" {
			select {}
		}
		// The wrapper must keep waiting, including after a console broadcast.
		time.Sleep(150 * time.Millisecond)
		fmt.Println("interrupted")
		os.Exit(23)
	default:
		input, err := io.ReadAll(os.Stdin)
		if err != nil {
			os.Exit(90)
		}
		cwd, err := os.Getwd()
		if err != nil {
			os.Exit(91)
		}
		json.NewEncoder(os.Stdout).Encode(struct {
			Args                 []string
			Input, Cwd, Sentinel string
		}{os.Args[1:], string(input), cwd, os.Getenv("DOTS_FIXTURE_SENTINEL")})
		fmt.Fprint(os.Stderr, "fixture stderr\n")
		code, _ := strconv.Atoi(os.Getenv("DOTS_FIXTURE_EXIT"))
		os.Exit(code)
	}
}
