"""Bounded directory and optional bat rendering for inert theme-file previews."""
import itertools
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import threading

from file_platform import check_object
from transactions import parents_safe

DIRECTORY_LIMIT = 200
RENDER_LIMIT = 1024 * 1024
RENDER_TIMEOUT = 5
SGR = re.compile(r'\x1b\[[0-9;]*m')


def resource_span(ui, path, display=None, kind=None):
    text = ui.clean(ui.path(path) if display is None else display)
    style = None
    if ui.human and (ui.color or ui.icons):
        _, icon, style = ui.resources.describe(path, kind)
        if ui.icons: text = icon + ' ' + text
    return (text, style)


def directory_view(ui, path, fallback=False):
    path = Path(path)
    parents_safe(path)
    check_object(path)
    if not stat.S_ISDIR(path.lstat().st_mode):
        raise ValueError('directory preview requires a real directory')
    # No recursion and no child dereferences, including cache links.
    with os.scandir(path) as iterator:
        entries = sorted(itertools.islice(iterator, DIRECTORY_LIMIT + 1), key=lambda e: e.name)
    ui.heading_spans([('Directory: ', '1;96'), resource_span(ui, path, kind='dir')])
    if fallback: ui.detail('Source', 'No editable source; showing the generated directory.')
    if not entries: ui.detail('Contents', 'Empty directory')
    for entry in entries[:DIRECTORY_LIMIT]:
        info = entry.stat(follow_symlinks=False)
        kind = 'symlink' if stat.S_ISLNK(info.st_mode) else 'dir' if stat.S_ISDIR(info.st_mode) else 'file' if stat.S_ISREG(info.st_mode) else 'special'
        display = entry.name + ('/' if kind == 'dir' else '')
        spans = [resource_span(ui, entry.path, display, kind), ('  ' + kind, '90')]
        if kind == 'symlink': spans.append((' -> ' + os.readlink(entry.path), '90'))
        ui._spans(spans, '  ', continuation_prefix='    ')
    if len(entries) > DIRECTORY_LIMIT:
        ui.detail('Contents', 'Listing truncated at 200 entries; child directories were not traversed.')


def run_renderer(command, data, env, timeout=RENDER_TIMEOUT, limit=RENDER_LIMIT):
    """Drain stdout concurrently with input; cap memory and wall time on every OS."""
    proc = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL, env=env)
    output = bytearray()
    failed = threading.Event()
    def stop():
        failed.set()
        try: proc.kill()
        except OSError: pass
    def feed():
        try:
            proc.stdin.write(data)
            proc.stdin.close()
        except (OSError, ValueError): stop()
    def drain():
        try:
            while True:
                chunk = proc.stdout.read(4096)
                if not chunk: break
                if len(output) + len(chunk) > limit:
                    stop(); break
                output.extend(chunk)
        except (OSError, ValueError): stop()
    threads = [threading.Thread(target=feed, daemon=True), threading.Thread(target=drain, daemon=True)]
    for thread in threads: thread.start()
    try:
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        stop(); proc.wait()
    finally:
        if proc.poll() is None: stop(); proc.wait()
        for thread in threads: thread.join(timeout=1)
        if any(thread.is_alive() for thread in threads): failed.set()
        # Renderer is bat with paging/config disabled, not an arbitrary shell pipeline.
        if not any(thread.is_alive() for thread in threads):
            proc.stdin.close(); proc.stdout.close()
    return bytes(output) if not failed.is_set() and proc.returncode == 0 else None


def highlight(ui, data, filename, generation):
    if not ui.stream.isatty() or not ui.color:
        return None
    executable = shutil.which('bat') or shutil.which('batcat')
    if not executable: return None
    cache = Path(generation) / 'bat-cache'
    try:
        for name in ('themes.bin', 'syntaxes.bin'):
            path = cache / name
            parents_safe(path); check_object(path)
            if not stat.S_ISREG(path.lstat().st_mode): return None
        # Bat may read optional metadata too; refuse links/special objects there.
        metadata = cache / 'metadata.yaml'
        if os.path.lexists(metadata) and not stat.S_ISREG(metadata.lstat().st_mode): return None
        name = Path(filename).name.removesuffix('.tpl')
        args = [executable, '--paging=never', '--style=plain', '--color=always', '--wrap=character',
                '--terminal-width', str(ui.width), '--file-name', name, '--theme=Dots']
        if name.endswith('.tmTheme') or name == 'tmtheme.xml': args += ['--language=XML']
        env = {k: v for k, v in os.environ.items() if not k.startswith('BAT_')}
        env.update(BAT_CONFIG_PATH=os.devnull, BAT_CACHE_PATH=str(cache), BAT_THEME='Dots')
        output = run_renderer([*args, '-'], data, env)
        if output is None: return None
        text = output.decode('utf-8')
        plain = SGR.sub('', text)
        if any(not c.isprintable() and c not in '\n\r\t' for c in plain): return None
        return text
    except (OSError, ValueError, RuntimeError):
        return None


def text_view(ui, data, filename, generation):
    # Escape input controls before bat sees them; only renderer-owned SGR survives.
    text = '\n'.join(ui.clean(line) for line in data.decode('utf-8').splitlines())
    if data.endswith(b'\n'): text += '\n'
    rendered = highlight(ui, text.encode('utf-8'), filename, generation)
    if rendered is not None:
        ui.stream.write(rendered)
        if rendered and not rendered.endswith('\n'): ui.stream.write('\n')
    else:
        for line in text.splitlines(): ui.emit(line)
