"""Read-only configuration previews. Invoked by fzf with an opaque numeric row ID."""
import importlib.util
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
sys.dont_write_bytecode = True
import tempfile
import threading
import time
import unicodedata

LIMIT = 65536
LINES = 200
TIMEOUT = 2


def clean(text):
    # Remove ALL terminal controls (including OSC/CSI introducers), bidi and
    # other invisible format characters before adding our own SGR sequences.
    return ''.join(c for c in text if c in '\n\t' or not unicodedata.category(c).startswith('C'))


def bat_output(arguments, data, env):
    """Bound the renderer pipe while concurrently feeding stdin; no pager."""
    proc = subprocess.Popen(arguments, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL, env=env)
    chunks = []
    def send():
        try:
            proc.stdin.write(data); proc.stdin.close()
        except (BrokenPipeError,OSError): pass
    def receive():
        chunks.append(proc.stdout.read(1048577))
    writer=threading.Thread(target=send,daemon=True)
    reader=threading.Thread(target=receive,daemon=True)
    deadline=time.monotonic()+TIMEOUT
    try:
        writer.start();reader.start();reader.join(TIMEOUT)
        if reader.is_alive() or (chunks and len(chunks[0])>1048576): return None
        if proc.wait(timeout=max(0.01,deadline-time.monotonic()))!=0: return None
        return chunks[0] if chunks else b''
    finally:
        if proc.poll() is None: proc.kill()
        proc.wait();writer.join(timeout=TIMEOUT);reader.join(timeout=TIMEOUT)
        proc.stdin.close();proc.stdout.close()


def highlight(text, color, executable=None):
    """Feed sanitized stdin, preserve bat configuration, disable paging; retain SGR only."""
    if executable:
        env=dict(os.environ)
        try:
            output=bat_output([executable,'--language=toml','--style=plain',
                '--paging=never','--wrap=never','--color='+('always' if color else 'never'),'-'],
                text.encode('utf-8'),env)
            if output is not None:
                rendered=output.decode('utf-8',errors='replace')
                # Preserve renderer SGR only, never OSC or cursor-control sequences.
                parts=re.split(r'(\x1b\[[0-9;]*m)',rendered)
                return ''.join((p if color else '') if re.fullmatch(r'\x1b\[[0-9;]*m',p) else clean(p) for p in parts)
        except (OSError,subprocess.TimeoutExpired): pass
    return text


def format_preview(identity, data, color, bat=None):
    source,name=identity.split(':',1)
    text=clean(data[:LIMIT].decode('utf-8',errors='replace'))
    rows=text.splitlines()
    body='\n'.join(row.expandtabs(4)[:512] for row in rows[:LINES])+'\n'
    out='CONFIGURATION PREVIEW\nName: '+name+'\nSource: '+source+'\nTOML only; no prompt commands run.\nSnapshot; selection re-reads the source.\n\n'
    out+=highlight(body,color,bat)
    if len(data)>LIMIT or len(rows)>LINES: out+='[preview truncated: 64 KiB / 200 lines]\n'
    return out


def preset_bytes(executable, name, root):
    env = dict(os.environ, STARSHIP_CACHE=str(root/'starship-cache'),
               XDG_CACHE_HOME=str(root/'xdg-cache'), STARSHIP_CONFIG=str(root/'unused.toml'))
    proc = subprocess.Popen([executable, 'preset', name], stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL, env=env)
    chunks = []
    def receive():
        chunks.append(proc.stdout.read(LIMIT+1))
    reader = threading.Thread(target=receive, daemon=True)
    deadline = time.monotonic() + TIMEOUT
    try:
        reader.start()
        reader.join(TIMEOUT)
        if reader.is_alive():
            raise ValueError('preset preview timed out (2s)')
        if chunks and len(chunks[0]) > LIMIT:
            return chunks[0]  # bounded prefix; finally terminates producer
        if proc.wait(timeout=max(0.01, deadline-time.monotonic())) != 0:
            raise ValueError('preset preview failed')
        return chunks[0] if chunks else b''
    finally:
        if proc.poll() is None:
            proc.kill()
        proc.wait()
        reader.join(timeout=TIMEOUT)
        proc.stdout.close()


def render(session, index):
    if not index.isascii() or not index.isdigit() or len(index) > 8:
        raise ValueError('invalid preview selection')
    root = Path(session)
    cache = root/(index+'.txt')
    if cache.exists():
        return cache.read_text(encoding='utf-8')
    with (root/'choices.json').open('rb') as f:
        raw = f.read(1024*1024+1)
    if len(raw) > 1024*1024:
        raise ValueError('preview inventory too large')
    doc = json.loads(raw)
    identity = doc['choices'][int(index)]
    spec = importlib.util.spec_from_file_location('preview_core', Path(__file__).with_name('blastoff.py'))
    core = importlib.util.module_from_spec(spec); spec.loader.exec_module(core)
    source, name = identity.split(':',1); core.name(name)
    try:
        if source in ('local','module','backup'):
            data = core.read(Path(doc['themes'])/(name+'.toml'))
        elif source == 'preset' and doc['starship']:
            data = preset_bytes(doc['starship'], name, root)
        else:
            raise ValueError('source unavailable')
        output = format_preview(identity, data, doc['color'], doc.get('bat'))
    except (core.Failure, OSError, ValueError, subprocess.TimeoutExpired):
        output = 'CONFIGURATION PREVIEW\nName: '+name+'\nSource: '+source+'\nPreview unavailable (unreadable, oversized, failed or timed out).\n'
    # Constant-time, conservative reservation: 64 cache slots x 256 KiB = 16 MiB.
    # Cache the first 64 visited items, not the first 64 row IDs. Never rescan files.
    guard=root/'.cache-lock'
    try: guard.mkdir()
    except FileExistsError: return output
    temporary=None
    try:
        budget=root/'cache-count'
        count=int(budget.read_text()) if budget.exists() else 0
        if count>=64 or len(output.encode('utf-8'))>262144: return output
        # Reserve before writing: interruption can waste a slot, never exceed cap.
        budget.write_text(str(count+1))
        with tempfile.NamedTemporaryFile(dir=root,delete=False,mode='w',encoding='utf-8') as f:
            temporary=f.name; f.write(output)
        os.replace(temporary,cache); temporary=None
    finally:
        if temporary is not None:
            try: os.unlink(temporary)
            except FileNotFoundError: pass
        guard.rmdir()
    return output


if __name__ == '__main__':
    # fzf terminates an old preview when focus moves; clean up a preset child.
    if hasattr(signal, 'SIGTERM'):
        def interrupted(*_):
            raise KeyboardInterrupt()
        signal.signal(signal.SIGTERM, interrupted)
    try:
        print(render(sys.argv[1], sys.argv[2]), end='')
    except KeyboardInterrupt:
        pass
    except (OSError, ValueError, KeyError, IndexError):
        print('Configuration preview unavailable.')
