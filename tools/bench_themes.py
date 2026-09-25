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
        plugin = Path(os.environ.get('ANODIZE_NVIM_DIR') or Path.home() / 'repos/Anodize.nvim')
        if NVIM and (plugin / 'lua/anodize/init.lua').is_file():
            from nvim_theme_fixture import install, PRELUDE
            install(fixture)
            script = fixture.root / 'bench.lua'
            script.write_text(PRELUDE + '''
if vim.env.DOTS_BENCH_BRIDGE == "0" then
 spec.opts.source=false
 spec.config(spec,spec.opts)
 vim.cmd.colorscheme("anodize")
else bridge.startup() end
''')
            for name, enabled in [('nvim_anodize_standalone', '0'), ('nvim_anodize_dots', '1')]:
                env = {**fixture.env, 'DOTS_BENCH_BRIDGE': enabled,
                       'XDG_CACHE_HOME': str(fixture.home / ('cache-' + name))}
                results[name] = measure([NVIM, '--headless', '-u', 'NONE', '-i', 'NONE', '-n', '--noplugin', '-l', str(script)], env)
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
