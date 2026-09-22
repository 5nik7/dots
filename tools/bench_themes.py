#!/usr/bin/env python3
"""Sequential theme measurements in owned roots; optional preserved legacy script."""
import argparse
import json
import os
from pathlib import Path
import shutil
import statistics
import subprocess
import tempfile
import time
from test_themes import Themes, BASH, ZSH, NVIM, REPO


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--samples', type=int, default=10)
    parser.add_argument('--baseline-script', type=Path)
    args = parser.parse_args()
    if args.samples < 1:
        parser.error('samples must be positive')
    fixture = Themes()
    fixture.setUp()
    results = {'samples': args.samples, 'platform': 'native Termux' if 'com.termux/' in BASH or 'com.termux/' in str(Path(BASH).resolve()) or 'com.termux/' in os.environ.get('PREFIX', '') else 'native ' + os.uname().sysname,
               'scope': 'isolated theme engine and minimal editor, not full LazyVim startup'}

    def timed(command, env=None):
        start = time.perf_counter()
        p = subprocess.run(command, cwd=fixture.home, env=env or fixture.env,
                           stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=90)
        if p.returncode:
            raise RuntimeError(p.stderr.decode())
        return time.perf_counter() - start

    def measure(command, env=None):
        cold = timed(command, env)
        samples = [timed(command, env) for _ in range(args.samples)]
        return {'first_seconds': cold, 'warm_median_seconds': statistics.median(samples),
                'warm_seconds': samples}

    try:
        if args.baseline_script:
            baseline = fixture.root / 'catppuccin-baseline'
            shutil.copy2(args.baseline_script, baseline)
            env = {**fixture.env, 'XDG_CACHE_HOME': str(fixture.home / 'baseline-cache')}
            results['legacy_init'] = measure([BASH, str(baseline), 'init'], env)
        command = [BASH, str(fixture.repo / 'themes/bin/catppuccin'), 'init']
        results['new_init'] = measure(command)
        fixture.dots('themes', 'set', 'catppuccin')
        results['selected_init'] = measure([BASH, str(fixture.repo / 'bin/dots-themes-init')])
        if ZSH:
            p = fixture.shell('''typeset -A themes; themes[root]=$DOTS/themes
source "$DOTS/themes/bin/theme"
set_theme
zmodload zsh/datetime
local start=$EPOCHREALTIME
repeat 10000; do _dots_theme_precmd; done
print -r -- $(( (EPOCHREALTIME-start)/10000 ))
''', ZSH)
            results['unchanged_prompt_seconds_per_call'] = float(p.stdout.strip())
        plugin = Path(os.environ['HOME']) / '.local/share/nvim/lazy/catppuccin'
        if NVIM and plugin.is_dir():
            shutil.copytree(plugin, fixture.root / 'catppuccin', ignore=shutil.ignore_patterns('.git'))
            lua = fixture.root / 'lua/util'
            lua.mkdir(parents=True)
            shutil.copy2(REPO / 'configs/nvim/lua/util/dots_theme.lua', lua / 'dots_theme.lua')
            shutil.copy2(REPO / 'configs/nvim/lua/util/dots_theme_adapters.lua', lua / 'dots_theme_adapters.lua')
            script = fixture.root / 'bench.lua'
            script.write_text('''local root=vim.env.HOME.."/.."
vim.opt.rtp:prepend(root); vim.opt.rtp:prepend(root.."/catppuccin")
local opts={flavour="mocha",default_integrations=false,auto_integrations=false,integrations={}}
if vim.env.DOTS_BENCH_BRIDGE ~= "0" then opts=require("util.dots_theme").options(opts) end
require("catppuccin").setup(opts)
if vim.env.DOTS_BENCH_BRIDGE == "2" then require("util.dots_theme").startup()
else vim.cmd.colorscheme("catppuccin-nvim") end
''')
            for name, enabled in [('nvim_without_bridge', '0'), ('nvim_with_bridge', '1'), ('nvim_with_startup', '2')]:
                env = {**fixture.env, 'DOTS_BENCH_BRIDGE': enabled,
                       'XDG_CACHE_HOME': str(fixture.home / ('cache-' + name))}
                results[name] = measure([NVIM, '--headless', '-u', 'NONE', '-i', 'NONE', '-l', str(script)], env)
        results['tokyonight_init'] = measure([BASH, str(fixture.repo / 'bin/dots-themes-init')],
            {**fixture.env, 'DOTS_THEME_SELECTION': 'tokyonight-night'})
        fixture.dots('themes', 'set', 'tokyonight')
        results['tokyonight_selected_init'] = measure([BASH, str(fixture.repo / 'bin/dots-themes-init')])
        out = Path(tempfile.mkdtemp(prefix='dots-theme-bench-')) / 'results.json'
        out.write_text(json.dumps(results, indent=2) + '\n')
        print(out)
        print(out.read_text())
    finally:
        fixture.doCleanups()


if __name__ == '__main__':
    main()
