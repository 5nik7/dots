#!/usr/bin/env python3
"""Disposable public Zsh fixture. Never source the developer's startup files."""
import json
import os
from pathlib import Path
import shutil
import statistics
import subprocess
import tempfile
import time

REPO = Path(__file__).resolve().parents[1]
ZSH = shutil.which('zsh')


def fixture(source=REPO, plugins=True):
    root = Path(tempfile.mkdtemp(prefix='dots-zsh-'))
    home = root / 'home'
    home.mkdir()
    repo = home / 'dots'
    repo.mkdir()
    for name in ('shells/zsh', 'themes', 'configs/starship', 'configs/vivid'):
        shutil.copytree(source / name, repo / name, symlinks=True)
    for name in ('bin/util', 'bin/colors.env', 'bin/box', 'dot.env', 'ruby/ruby.env',
                 'shells/shells.env', 'scripts/preview.zsh', 'scripts/batman', 'scripts/batpipe'):
        dest = repo / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        original = source / name
        if name == 'bin/box' and not original.exists():
            original = REPO / name
        shutil.copy2(original, dest)
    # Preserve module presence/order, without reading private or platform-local values.
    for name in ('androidots/termux.env', 'windots/win.env', 'secrets/secrets.env', 'secrets/secrets.sh'):
        dest = repo / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text('# synthetic optional module\n')
    for name in ('.cache', '.config', '.local/share', '.local/state', '.local/bin', 'bin', '.atuin/bin'):
        (home / name).mkdir(parents=True, exist_ok=True)
    (home / '.atuin/bin/env').write_text(':\n')
    for name in ('zshenv', 'zshrc'):
        (home / ('.' + name)).symlink_to(repo / 'shells/zsh' / name)
    commands = root / 'bin'
    commands.mkdir()
    for name in ('fzf', 'tv', 'usage'):
        exe = shutil.which(name)
        if exe:
            (commands / name).symlink_to(exe)
    (home / '.fzf.zsh').write_text('source <(fzf --zsh)\n')
    # Fixture Git cannot download plugins or contact remotes.
    git = shutil.which('git')
    if git:
        import shlex
        wrapper = commands / 'git'
        wrapper.write_text('#!' + ZSH + '\nfor arg; do\n'
                           '  case $arg in clone|fetch|pull|push|ls-remote) exit 97;; esac\n'
                           'done\nexec ' + shlex.quote(git) + ' "$@"\n')
        wrapper.chmod(0o700)
    if plugins:
        installed = Path(os.environ['HOME']) / '.local/share/zinit'
        target = home / '.local/share/zinit'
        for name in ('zinit.git', 'plugins/Aloxaf---fzf-tab',
                     'plugins/zdharma-continuum---fast-syntax-highlighting',
                     'plugins/zsh-users---zsh-autosuggestions',
                     'plugins/zsh-users---zsh-completions',
                     'plugins/zsh-users---zsh-history-substring-search'):
            if not (installed / name).is_dir():
                raise RuntimeError('Required installed public plugin missing: ' + name)
            shutil.copytree(installed / name, target / name,
                            ignore=shutil.ignore_patterns('.git', '*.zwc'), symlinks=False)
        (target / 'zinit.git/.git').mkdir()
    env = {
        'HOME': str(home), 'ZDOTDIR': str(home), 'DOTS': str(repo),
        'XDG_CONFIG_HOME': str(home / '.config'), 'XDG_CACHE_HOME': str(home / '.cache'),
        'XDG_DATA_HOME': str(home / '.local/share'), 'XDG_STATE_HOME': str(home / '.local/state'),
        'TMPDIR': str(root), 'SHELL': ZSH, 'TERM': 'xterm-256color',
        'PATH': str(commands) + os.pathsep + str(Path(ZSH).parent) + ':/usr/bin:/bin',
        'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': os.devnull,
        'GIT_TERMINAL_PROMPT': '0', 'MISE_TRUSTED_CONFIG_PATHS': str(root),
    }
    for key in ('PREFIX', 'TERMUX_VERSION', 'TERMUX__PREFIX', 'LANG', 'LD_PRELOAD'):
        if key in os.environ:
            env[key] = os.environ[key]
    return root, repo, env


def run(env, code=':', interactive=True, timeout=90):
    return subprocess.run([ZSH, '-d' + ('i' if interactive else '') + 'c', code],
                          env=env, cwd=env['HOME'], text=True, capture_output=True, timeout=timeout)


def benchmark(source=REPO, samples=10):
    root, repo, env = fixture(source)
    start = time.perf_counter()
    proc = run(env)
    cold = time.perf_counter() - start
    (root / 'startup.stderr').write_text(proc.stderr)
    timings = []
    for _ in range(samples):
        start = time.perf_counter()
        run(env)
        timings.append(time.perf_counter() - start)
    noninteractive = []
    for _ in range(samples):
        start = time.perf_counter()
        run(env, interactive=False)
        noninteractive.append(time.perf_counter() - start)
    result = {'fixture': str(root), 'cold_application_cache_seconds': cold,
              'warm_seconds': timings, 'warm_median_seconds': statistics.median(timings),
              'noninteractive_median_seconds': statistics.median(noninteractive),
              'startup_returncode': proc.returncode}
    (root / 'timings.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    return root


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=REPO)
    parser.add_argument('--samples', type=int, default=10)
    args = parser.parse_args()
    benchmark(args.source.resolve(), args.samples)
