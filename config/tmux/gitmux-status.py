#!/usr/bin/env python3
"""Bound Git status/host metadata and keep names literal in tmux formats."""
import json
import os
from pathlib import Path
import re
import selectors
import signal
import subprocess
import sys
import time
from widget_cache import Cache, age, read


def compact_fields(output):
    """Normalize only Dots-styled metrics/divergence, never arbitrary Git names."""
    parts = re.split(r'((?<!#)#\[[^\]]*\])', output)
    for index in range(1, len(parts) - 3, 2):
        style, text, next_style, next_text = parts[index:index + 4]
        if ('@dots-gitmux-added}' in style and re.fullmatch(r'.*[0-9]+ ', text)
                and '@dots-gitmux-deleted}' in next_style and re.fullmatch(r'.*[0-9]+ ?', next_text)):
            parts[index + 1] = text[:-1]
        elif ('@dots-gitmux-ahead}' in style and re.fullmatch(r'.*[0-9]+', text)
              and '@dots-gitmux-behind}' in next_style and re.fullmatch(r'.*[0-9]+ ?', next_text)):
            parts[index] = style.replace('@dots-gitmux-ahead}', '@dots-gitmux-conflict}')
            parts[index + 2] = next_style.replace('@dots-gitmux-behind}', '@dots-gitmux-conflict}')
    return ''.join(parts)


def literal_names(output):
    """Git refs cannot contain '[', so only configured styles can open '#['."""
    output = output.rstrip('\n')
    if any(ord(char) < 32 or 127 <= ord(char) < 160 for char in output):
        raise ValueError('control character in gitmux output')
    parts = re.split(r'((?<!#)#\[[^\]]*\])', output)
    return ''.join(part if index % 2 else part.replace('#', '##')
                   for index, part in enumerate(parts))


def collect(directory, snapshot, timeout=1):
    """Independent providers share one deadline, with no persistent metadata."""
    # Both providers change cwd; keep a relative legacy argument from being
    # resolved a second time by gitmux. Joining preserves symlink/.. semantics.
    directory = os.path.join(os.getcwd(), directory)
    generated = Path(os.environ.get('XDG_STATE_HOME', str(Path.home()/'.local/state')))/'dots/current/theme/gitmux.conf'
    config = generated if generated.is_file() else Path.home()/'.gitmux.conf'
    commands = {'gitmux': (['gitmux', '-cfg', str(config),
                            '-timeout', str(timeout)+'s', directory], 16384)}
    if snapshot:
        commands['icon'] = (['git-it', 'info', '--json'], 65536)
    processes, buffers, finished = {}, {}, set()
    deadline = time.monotonic() + timeout
    env = dict(os.environ, GIT_OPTIONAL_LOCKS='0', GIT_TERMINAL_PROMPT='0')
    try:
        with selectors.DefaultSelector() as selector:
            for name, (command, _) in commands.items():
                try:
                    process = subprocess.Popen(command, cwd=directory, env=env,
                                               stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                               stderr=subprocess.DEVNULL, start_new_session=True)
                except OSError:
                    continue
                processes[name], buffers[name] = process, bytearray()
                selector.register(process.stdout, selectors.EVENT_READ, name)
            while selector.get_map():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                for key, _ in selector.select(remaining):
                    name = key.data
                    chunk = os.read(key.fileobj.fileno(), 4096)
                    if not chunk:
                        selector.unregister(key.fileobj)
                        finished.add(name)
                    elif len(buffers[name]) + len(chunk) > commands[name][1]:
                        selector.unregister(key.fileobj)
                        try:
                            os.killpg(processes[name].pid, signal.SIGKILL)
                        except ProcessLookupError:
                            pass
                    else:
                        buffers[name].extend(chunk)
        output = {}
        for name, process in processes.items():
            if name not in finished:
                continue
            try:
                if process.wait(timeout=max(.001, deadline - time.monotonic())) == 0:
                    output[name] = buffers[name].decode('utf-8')
            except (UnicodeError, subprocess.TimeoutExpired):
                pass
        return output
    finally:
        for process in processes.values():
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()
            process.stdout.close()


def remote_icon(raw):
    info = json.loads(raw)
    if (isinstance(info, dict) and isinstance(info.get('remote'), str) and info['remote']
            and isinstance(info.get('icon'), str) and len(info['icon']) <= 64
            and all(ord(c)>=32 and not 127<=ord(c)<160 and c not in '#|' for c in info['icon'])):
        return info['icon']
    return ''


def status(directory, snapshot=False):
    output = collect(directory, snapshot)
    try:
        gitmux = literal_names(compact_fields(output.get('gitmux', '')))
    except ValueError:
        gitmux = ''
    if not snapshot:
        return gitmux
    try:
        icon = remote_icon(output.get('icon', ''))
    except (ValueError, RecursionError):
        icon = ''
    return icon + '|' + gitmux


def repository(directory):
    """Small filesystem identity check; never run Git on the render path."""
    directory=Path(directory).resolve(strict=True)
    identity=[str(directory),directory.stat().st_dev,directory.stat().st_ino]
    for parent in (directory,*directory.parents):
        marker=parent/'.git'
        try:
            info=marker.lstat()
        except FileNotFoundError:
            continue
        if marker.is_dir():
            gitdir=marker.resolve()
        else:
            value=read(marker,4096).decode('utf-8').strip()
            if not value.startswith('gitdir: '):raise ValueError('invalid git directory')
            gitdir=(parent/value[8:]).resolve(strict=True)
        head=read(gitdir/'HEAD',4096).decode('utf-8')
        info=gitdir.stat()
        return identity+[str(gitdir),info.st_dev,info.st_ino,head]
    return None


def cached_status(directory, token=None):
    identity=repository(directory)
    if identity is None:return '|'
    directory=identity[0]
    generated=Path(os.environ.get('XDG_STATE_HOME',str(Path.home()/'.local/state')))/'dots/current/theme/gitmux.conf'
    config=generated if generated.is_file() else Path.home()/'.gitmux.conf'
    try:
        info=config.stat();config_id=[str(config.resolve()),info.st_mtime_ns,info.st_size]
    except OSError:config_id=[str(config)]
    cache=Cache('git',[identity,config_id])
    def produce(previous):
        output=collect(directory,True,timeout=3)
        if repository(directory)!=identity:raise ValueError('repository changed')
        values={}
        for name in ('gitmux','icon'):
            old=previous.get(name,{})
            old=old if isinstance(old,dict) else {}
            try:
                raw=output[name]
                value=remote_icon(raw) if name=='icon' else raw
                if name=='gitmux' and not literal_names(compact_fields(value)):
                    raise ValueError('empty repository status')
                values[name]=dict(value=value,updated=time.time(),failed=False)
            except (KeyError,ValueError,RecursionError):
                values[name]=dict(old,failed=True)
        return values,5
    if token:
        cache.work(token,produce,5)
        return ''
    row=cache.read();values=row.get('value',{})
    cache.schedule(__file__,[directory],timeout=3)
    rendered={};stale=False
    for name in ('gitmux','icon'):
        field=values.get(name,{})
        if not isinstance(field,dict):continue
        elapsed=age(field.get('updated'))
        try:
            if elapsed<=30:
                value=field['value']
                if not isinstance(value,str):continue
                if name=='gitmux':value=literal_names(compact_fields(value))
                elif value!=remote_icon(json.dumps({'remote':'origin','icon':value})):continue
                rendered[name]=value
                stale=stale or bool(value) and bool(field.get('failed') or row.get('failed') or elapsed>8)
        except (ValueError,KeyError,RecursionError):pass
    text=rendered.get('gitmux','#[fg=#{@dots-gitmux-muted}] ?#[default]')
    if stale:text='#[fg=#{@dots-gitmux-muted}]~#[default] '+text
    return rendered.get('icon','')+'|'+text


if __name__ == '__main__':
    try:
        if len(sys.argv)==4 and sys.argv[1]=='--_worker':
            cached_status(sys.argv[3],sys.argv[2])
        elif len(sys.argv) == 3 and sys.argv[1] == '--snapshot':
            print(cached_status(sys.argv[2]))
        else:
            print(status(sys.argv[1]) if len(sys.argv) == 2 else '')
    except (OSError, ValueError, subprocess.TimeoutExpired):
        # Only a successful directory inspection can confirm a non-repository.
        # An inaccessible/replaced HEAD must not make the status vanish.
        print('|#[fg=#{@dots-gitmux-muted}] ?#[default]' if sys.argv[1:2]==['--snapshot'] else '')
