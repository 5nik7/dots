//go:build unix

package main

import (
	"os"
	"os/signal"
	"syscall"
)

func additionalSignals(c chan os.Signal) { signal.Notify(c, syscall.SIGTERM) }
