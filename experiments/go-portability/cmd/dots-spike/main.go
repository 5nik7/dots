package main

import (
	"os"

	"dots.local/portability/internal/cli"
	"dots.local/portability/internal/platform"
)

func main() {
	os.Exit(cli.Run(os.Args[1:], os.Stdout, os.Stderr, cli.Logo, platform.Inspect))
}
