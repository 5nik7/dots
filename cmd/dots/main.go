package main

import (
	"os"

	"github.com/5nik7/dots/internal/cli"
	"github.com/5nik7/dots/internal/platform"
)

func main() {
	os.Exit(cli.Run(os.Args[1:], os.Stdout, os.Stderr, cli.Logo, platform.Inspect))
}
