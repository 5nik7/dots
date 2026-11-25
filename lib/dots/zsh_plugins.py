"""Acquire the fixed public Zsh integrations into Zinit's cache on first use."""
import argparse
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tarfile
import tempfile
import time

from bootstrap import publish_checkout

MANAGER = 'zdharma-continuum/zinit'
DEJA = 'Giammarco-Ferranti/deja'
BINARY = 'dots-deja-binary'
ENTRY = {
    MANAGER: 'zinit.zsh',
    'zsh-users/zsh-completions': 'zsh-completions.plugin.zsh',
    'Aloxaf/fzf-tab': 'fzf-tab.plugin.zsh',
    'zdharma-continuum/fast-syntax-highlighting': 'fast-syntax-highlighting.plugin.zsh',
    'zsh-users/zsh-autosuggestions': 'zsh-autosuggestions.plugin.zsh',
    'zsh-users/zsh-history-substring-search': 'zsh-history-substring-search.plugin.zsh',
    'jeffreytse/zsh-vi-mode': 'zsh-vi-mode.plugin.zsh',
    'kutsan/zsh-system-clipboard': 'zsh-system-clipboard.plugin.zsh',
    DEJA: 'deja.plugin.zsh',
    BINARY: 'deja',
}


def run(args, work, deadline):
    # Ignore per-user Git/Curl/SSH configuration, credentials, hooks and templates.
    env = {key: os.environ[key] for key in ('PATH', 'LANG', 'TMPDIR', 'PREFIX', 'LD_PRELOAD',
           'SSL_CERT_FILE', 'SSL_CERT_DIR', 'SYSTEMROOT') if key in os.environ}
    env.update(HOME=str(work), XDG_CONFIG_HOME=str(work), GIT_CONFIG_GLOBAL=os.devnull,
               GIT_CONFIG_NOSYSTEM='1', GIT_CEILING_DIRECTORIES=str(work.parent), GIT_TERMINAL_PROMPT='0', GIT_ALLOW_PROTOCOL='https',
               GIT_LFS_SKIP_SMUDGE='1', GCM_INTERACTIVE='Never')
    remaining = min(30, deadline - time.monotonic())
    if remaining <= 0:
        raise ValueError('acquisition time limit reached')
    watchdog = shutil.which('timeout', path=env.get('PATH'))
    if not watchdog:
        raise ValueError('the timeout utility is required for bounded acquisition')
    # This watchdog also outlives a killed Python worker. Git transport helpers
    # share its process group, so closing the shell cannot leave an unbounded fetch.
    with subprocess.Popen([watchdog, '-k', '2', str(remaining), *args], cwd=work, env=env,
                          start_new_session=True, stdin=subprocess.DEVNULL,
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) as proc:
        try:
            status = proc.wait(timeout=remaining)
        except BaseException:
            with contextlib.suppress(ProcessLookupError):
                os.killpg(proc.pid, signal.SIGKILL)
            raise
    if status:
        raise ValueError(f'{Path(args[0]).name} failed (exit {status})')


def release(work, stage, platform, arch, deadline):
    arch = {'x86_64': 'amd64', 'amd64': 'amd64', 'aarch64': 'arm64', 'arm64': 'arm64'}.get(arch)
    if platform not in ('linux', 'wsl') or not arch:
        raise ValueError('Deja Linux releases require Linux/WSL x86-64 or ARM64')
    limit = 32 * 1024 * 1024

    def download(url, target, size):
        run(['curl', '--disable', '--fail', '--silent', '--location', '--proto', '=https',
             '--proto-redir', '=https', '--max-redirs', '4', '--max-time', '25', '--max-filesize',
             str(size), '--output', str(target), url], work, deadline)
        if target.stat().st_size > size:
            raise ValueError('release exceeds size limit')

    metadata = work / 'release.json'
    download(f'https://api.github.com/repos/{DEJA}/releases/latest', metadata, 1024 * 1024)
    result = json.loads(metadata.read_bytes())
    tag = result['tag_name']
    import re
    if not isinstance(tag, str) or not re.fullmatch(r'v?[0-9][0-9A-Za-z.\-]{0,63}', tag):
        raise ValueError('unexpected Deja release tag')
    filename = f'deja_{tag.removeprefix("v")}_linux_{arch}.tar.gz'
    if not any(asset.get('name') == filename for asset in result['assets']):
        raise ValueError('Deja release has no matching Linux executable')
    archive = work / 'deja.tar.gz'
    relative = f'/{DEJA}/releases/download/{tag}/{filename}'
    download('https://github.com' + relative, archive, limit)
    import gzip
    with gzip.open(archive) as source:
        payload = source.read(2 * limit + 1)
    if len(payload) > 2 * limit:
        raise ValueError('Deja release exceeds unpacked size limit')
    with tarfile.open(fileobj=io.BytesIO(payload), mode='r:') as files:
        candidates = [m for m in files if m.isfile() and Path(m.name).name == 'deja']
        if len(candidates) != 1 or not 0 < candidates[0].size <= 2 * limit:
            raise ValueError('Deja release lacks an unambiguous executable')
        stage.mkdir()
        with files.extractfile(candidates[0]) as src, (stage / 'deja').open('xb') as dst:
            shutil.copyfileobj(src, dst)
    (stage / 'deja').chmod(0o755)
    # Keep Zinit's native release identity for explicit zinit update.
    metadata = stage / '._zinit'
    metadata.mkdir()
    (metadata / 'is_release').write_text(relative + '\n')
    (metadata / 'url').write_text('https://github.com' + relative + '\n')


def write_status(path, status):
    with tempfile.NamedTemporaryFile('w', dir=path.parent, delete=False) as stream:
        stream.write(status + '\n')
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(stream.name, path)


def completion_links(name, target, directory):
    # Match the shipped plugins' Zinit completion location and disabled names.
    if name == 'zsh-users/zsh-completions':
        providers = (target / 'src').glob('_*')
    elif name == 'zdharma-continuum/fast-syntax-highlighting':
        providers = [target / '_fast-theme']
    else:
        return
    directory.mkdir(exist_ok=True, parents=True)
    for provider in providers:
        if (not provider.is_file() or provider.suffix == '.zwc' or
                not provider.resolve().is_relative_to(target) or
                os.path.lexists(directory / provider.name[1:])):
            continue
        with contextlib.suppress(FileExistsError):
            (directory / provider.name).symlink_to(provider)


def acquire(name, target, state, completions, retry, platform, arch, deadline):
    import fcntl
    token = hashlib.sha256(os.fsencode(target)).hexdigest()
    receipt = state / (token + '.status')
    with (state / (token + '.lock')).open('a') as lock:
        while True:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise ValueError('another acquisition is still busy')
                time.sleep(0.1)
        if (target / ENTRY[name]).is_file():
            return
        if receipt.is_file() and not retry and receipt.read_text().strip() != 'installed':
            raise ValueError('previous acquisition incomplete; use dots-zsh-plugins retry')
        if os.path.lexists(target):
            raise ValueError('destination already occupied; check its contents')
        write_status(receipt, 'preparing')
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(prefix='.dots-plugin-', dir=target.parent) as tmp:
                work = Path(tmp)
                stage = work / 'checkout'
                if name == BINARY:
                    release(work, stage, platform, arch, deadline)
                else:
                    run(['git', '-c', 'credential.helper=', '-c', 'core.askPass=', '-c',
                         'http.followRedirects=false', 'clone', '--quiet', '--depth=1',
                         '--no-recurse-submodules', '--single-branch', '--',
                         f'https://github.com/{name}.git', str(stage)], work, deadline)
                entry = stage / ENTRY[name]
                if not entry.is_file() or not entry.resolve().is_relative_to(stage):
                    raise ValueError('download lacks the expected entry point')
                publish_checkout(stage, target)
                completion_links(name, target, completions)
        except Exception:
            write_status(receipt, 'failed')
            raise
        write_status(receipt, 'installed')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['auto', 'setup', 'retry'])
    for name in ('manager', 'plugins', 'state'):
        parser.add_argument(name, type=Path)
    parser.add_argument('--completions', type=Path)
    parser.add_argument('platform')
    parser.add_argument('arch')
    parser.add_argument('names', nargs='+', choices=ENTRY)
    args = parser.parse_args()
    completions = args.completions or args.plugins.parent / 'completions'
    if not all(p.is_absolute() for p in (args.manager, args.plugins, args.state, completions)):
        parser.error('absolute manager, plugin and state paths are required')
    os.umask(0o077)
    args.state.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + 90
    failures = 0
    for name in dict.fromkeys(args.names):
        target = args.manager if name == MANAGER else args.plugins / name.replace('/', '---')
        try:
            if time.monotonic() >= deadline:
                raise ValueError('acquisition time limit reached')
            acquire(name, target, args.state, completions, args.mode != 'auto', args.platform, args.arch, deadline)
        except (OSError, ValueError, KeyError, TypeError, tarfile.TarError, EOFError, subprocess.SubprocessError) as error:
            failures += 1
            print(f'dots: {name}: {error}', file=sys.stderr)
    return int(bool(failures))


if __name__ == '__main__':
    sys.exit(main())
