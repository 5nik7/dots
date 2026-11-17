<picture>
  <source media="(prefers-color-scheme: dark)" srcset="media/logo/white/DOTS_white_2048x562.png">
  <source media="(prefers-color-scheme: light)" srcset="media/logo/black/DOTS_black_2048x562.png">
  <img src="media/logo/black/DOTS_black_2048x562.png" alt="dots" width="480">
</picture>

# dots

Manage dotfiles, shells, themes and your development environment through one command family. Dots keeps configuration in the checkout, previews managed changes, and records recovery information.

**[Read the Dots wiki](https://github.com/5nik7/dots/wiki)** · [Installation](https://github.com/5nik7/dots/wiki/Installation) · [Command reference](https://github.com/5nik7/dots/wiki/Command-reference) · [Configuration](https://github.com/5nik7/dots/wiki/Configuration)

Dots provides Bash entry points for Termux, Linux and WSL, and native PowerShell for Windows. Termux is the primary local development target; application capabilities and native verification vary. See [platform support](https://github.com/5nik7/dots/wiki/Platforms) for current limits.

## Get started

The checkout instructions below assume Git and Python 3.11+ are available. Use Bash 4.4+ on Termux, Linux or WSL, or PowerShell 5.1/7 on native Windows. For a fresh machine or missing prerequisites, follow [fresh-machine bootstrap](https://github.com/5nik7/dots/wiki/Installation#fresh-machine-bootstrap); it reviews checkout acquisition and runtime preparation before making changes.

Clone the repository into a new directory, then preview setup. If you already have a checkout, open its root and skip the clone and `cd` steps.

**Termux, Linux and WSL:**

```sh
git clone https://github.com/5nik7/dots.git
cd dots
./install.sh --dry-run
./install.sh
```

**Windows PowerShell:**

```powershell
git clone https://github.com/5nik7/dots.git
cd dots
./install.ps1 -DryRun
./install.ps1
```

Run the installer after reviewing the preview. Interactive setup lets you review components and managed changes before applying them. Existing configuration is classified and protected by the applicable backup and recovery workflow. Packages, fonts and patched Leaf are optional; additional requirements depend on your selections. See the [installation guide](https://github.com/5nik7/dots/wiki/Installation) for component choices, dependencies, updates and uninstall.

## First commands

Open a new shell after setup to load the installed shell integration, then explore:

```sh
dots                 # Discover command families
dots menu            # Browse common workflows
dots help files      # Read help for managed files
dots wiki browse     # Read current guides offline
```

The [wiki](https://github.com/5nik7/dots/wiki) contains detailed workflows, configuration options, troubleshooting and platform notes. The [source documentation index](docs/README.md) is available in this checkout too.

## Contributing

Start with [AGENTS.md](AGENTS.md) and the [documentation guide](agents/guides/documentation.md). Canonical documentation lives in this repository; the wiki is generated from it. Preserve existing configuration and unrelated work, and use isolated tests.
