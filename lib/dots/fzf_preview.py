"""On-demand, shell-independent FZF file and completion previews."""
import codecs
from itertools import islice
import mimetypes
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent / 'files'))
from config_values import value
from fzf_config import validate_previewers
from markdown_viewer import plain, rendered_bytes
from resources import clean
from themes.file_preview import run_renderer

TEXT_LIMIT = 128 * 1024
MEDIA_LIMIT = 32 * 1024 * 1024
FONT_EXTENSIONS = {'.ttf', '.otf', '.ttc', '.otc', '.woff', '.woff2'}
MARKDOWN_EXTENSIONS = {'.md', '.markdown', '.mdown', '.mkdn', '.mkd'}
KITTY_GRAPHICS = re.compile(rb'(\x1b_G[a-zA-Z0-9,=+/;:_-]+\x1b\\)')


def extent(key, default, limit):
    try:
        return max(1, min(limit, int(os.environ.get(key, default))))
    except ValueError:
        return default


def file_data(path):
    """Classify a hovered path once. Only read samples from regular files."""
    info = path.stat()
    if stat.S_ISDIR(info.st_mode):
        return 'directory', info, b''
    if not stat.S_ISREG(info.st_mode):
        return 'special', info, b''
    suffix = path.suffix.lower()
    if suffix in FONT_EXTENSIONS:
        return 'font', info, b''
    # Built-in suffixes avoid loading the host's MIME database/registry per hover.
    mime = mimetypes.types_map.get(suffix, '')
    if mime.startswith('image/'):
        return 'image', info, b''
    flags = os.O_RDONLY | getattr(os, 'O_NONBLOCK', 0) | getattr(os, 'O_BINARY', 0)
    with os.fdopen(os.open(path, flags), 'rb') as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            return 'special', info, b''
        data = stream.read(TEXT_LIMIT)
    if data.startswith((b'\x89PNG\r\n\x1a\n', b'\xff\xd8\xff', b'GIF87a', b'GIF89a')) or (
            data[:4] == b'RIFF' and data[8:12] == b'WEBP'):
        return 'image', info, b''
    if data.startswith((b'OTTO', b'wOFF', b'wOF2', b'ttcf', b'\x00\x01\x00\x00')):
        return 'font', info, b''
    if b'\0' not in data:
        try:
            decoded = codecs.getincrementaldecoder('utf-8-sig')().decode(data, final=info.st_size <= len(data))
            if suffix in MARKDOWN_EXTENSIONS:
                return 'markdown', info, plain(decoded)
            return 'text', info, plain(decoded.expandtabs(8))
        except UnicodeDecodeError:
            pass
    return 'binary', info, b''


def metadata(path, kind, info):
    return (clean(path.name or str(path)) + '\n' + kind.capitalize() + ' · ' +
            str(info.st_size) + ' bytes\n').encode('utf-8', 'replace')


def execute(command, data, color):
    executable = shutil.which(command[0])
    if not executable:
        return None
    # Batch launchers reparse arguments through cmd.exe even with shell=False.
    if os.name == 'nt' and Path(executable).suffix.lower() in ('.cmd', '.bat'):
        return None
    env = dict(os.environ, PAGER='cat', GIT_PAGER='cat')
    if not color:
        env['NO_COLOR'] = '1'
    output = run_renderer([executable, *command[1:]], data, env)
    if output and output.strip():
        return rendered_bytes(output, color)
    return None


def command_for(renderer, path, width, height, color):
    color_mode = 'always' if color else 'never'
    if renderer == 'eza':
        icons = 'never' if os.environ.get('DOTS_ICONS') == 'never' else 'always'
        return ['eza', '-a', '-1', '--group-directories-first', '--color=' + color_mode, '--icons=' + icons, '--', str(path)]
    if renderer == 'highlight':
        return ['highlight', '-O', 'ansi', '--syntax=' + (path.suffix[1:] or 'txt')]
    if renderer == 'bat':
        return ['bat' if shutil.which('bat') else 'batcat', '--paging=never', '--style=numbers',
                '--color=' + color_mode, '--file-name', str(path), '--', '-']
    if renderer == 'chafa':
        return ['chafa', '--probe=off', '--animate=off', '--format=symbols', '--size=' + str(width) + 'x' + str(height),
                *([] if color else ['--colors=none']), '--', str(path)]
    if renderer == 'font-info':
        return ['fc-scan', '--format', '%{family} · %{style}\n', '--', str(path)]
    return ['file', '--brief', '--dereference', '--', str(path)]


def kitty_image(path, width, height, color):
    if not color or not (os.environ.get('KITTY_WINDOW_ID') or os.environ.get('GHOSTTY_RESOURCES_DIR')
                         or os.environ.get('TERM') == 'xterm-kitty'):
        return None
    kitten = shutil.which('kitten')
    kitty = shutil.which('kitty')
    if not kitten and not kitty:
        return None
    command = [kitten, 'icat'] if kitten else [kitty, '+kitten', 'icat']
    output = run_renderer([*command, '--transfer-mode=stream', '--unicode-placeholder', '--stdin=no',
                           '--place=' + str(width) + 'x' + str(height) + '@0x0', '--', str(path)],
                          b'', dict(os.environ))
    if output and KITTY_GRAPHICS.search(output):
        return b''.join(part if KITTY_GRAPHICS.fullmatch(part) else rendered_bytes(part, True)
                        for part in KITTY_GRAPHICS.split(output))
    return None


def render_candidate(word, *, path=None, description='', group=''):
    width = extent('FZF_PREVIEW_COLUMNS', 80, 600)
    height = extent('FZF_PREVIEW_LINES', 24, 300)
    color_mode = os.environ.get('DOTS_COLOR', 'auto')
    color = color_mode == 'always' or (color_mode == 'auto' and not os.environ.get('NO_COLOR')
                                       and os.environ.get('TERM', '') != 'dumb')
    kind, info, data = 'completion', None, b''
    if path is not None:
        try:
            path = Path(path).expanduser().absolute()
            kind, info, data = file_data(path)
        except (OSError, ValueError, RuntimeError):
            path = None

    fallback = {'completion': 'description', 'text': 'plain', 'markdown': 'plain', 'directory': 'listing'}.get(kind, 'metadata')
    def basic(renderer):
        if renderer == 'description':
            # fzf-tab descriptions may contain ANSI completion styling.
            rows = dict.fromkeys(part for part in (word, group, description) if part)
            return rendered_bytes('\n'.join(rows).encode('utf-8', 'replace'), False)
        if renderer == 'plain':
            return data
        if renderer == 'listing':
            with os.scandir(path) as iterator:
                entries = sorted(islice(iterator, 201), key=lambda entry: entry.name)
            names = [clean(entry.name) + ('/' if entry.is_dir(follow_symlinks=False) else '') for entry in entries[:200]]
            if len(entries) > 200:
                names.append('…')
            return '\n'.join(names).encode('utf-8', 'replace')
        return metadata(path, kind, info)

    if kind == 'special':
        return basic('metadata')
    renderers = value('apps.fzf.previewers.' + kind, [fallback])
    validate_previewers(kind, renderers)
    if not renderers:
        return b''
    fields = {'{path}': str(path) if path is not None else '', '{word}': word, '{description}': description,
              '{width}': str(width), '{height}': str(height)}
    for renderer in renderers:
        try:
            if isinstance(renderer, list):
                # Only argument slots are substituted. Executable names are literal.
                result = execute([renderer[0], *(fields.get(arg, arg) for arg in renderer[1:])], data, color)
            elif renderer in ('description', 'listing', 'plain', 'metadata'):
                return basic(renderer)
            elif renderer == 'wiki':
                from wiki_presentation import document
                result = document(data, SimpleNamespace(width=width, color=color), fallback=False)
            elif renderer == 'kitty':
                result = kitty_image(path, width, height, color) if info.st_size <= MEDIA_LIMIT else None
            elif renderer == 'font-sample':
                if info.st_size > MEDIA_LIMIT:
                    continue
                from fonts.preview import render_sample
                result = render_sample(path, color, quiet=True).encode()
            else:
                if renderer in ('chafa', 'font-info') and info.st_size > MEDIA_LIMIT:
                    continue
                command = command_for(renderer, path, width, height, color)
                result = execute(command, data if renderer in ('highlight', 'bat') else b'', color)
            if result:
                return result
        except (OSError, ValueError, RuntimeError, subprocess.SubprocessError):
            continue
    return basic(fallback)


def main(arguments):
    if len(arguments) == 2 and arguments[0] == '--selection':
        # FZF writes the hovered item into a temporary file. Candidate text
        # never appears in a shell command, including on native Windows.
        with Path(arguments[1]).open('rb') as stream:
            line = stream.read(65537)
        if len(line) > 65536:
            raise ValueError('selection too large')
        candidate = os.fsdecode(line.removesuffix(b'\0') if line.endswith(b'\0') else line.removesuffix(b'\n'))
        return render_candidate(candidate, path=candidate if candidate else None)
    if len(arguments) == 5 and arguments[0] == '--completion':
        _, word, path, description, group = arguments
        return render_candidate(word, path=path or None, description=description, group=group)
    if len(arguments) == 1:
        return render_candidate(arguments[0], path=arguments[0] or None)
    raise ValueError('expected a file or completion candidate')


if __name__ == '__main__':
    try:
        output = main(sys.argv[1:])
        if output:
            sys.stdout.buffer.write(output if output.endswith(b'\n') else output + b'\n')
    except BrokenPipeError:
        pass
    except (OSError, ValueError, RuntimeError) as error:
        print('Preview unavailable: ' + clean(error), file=sys.stderr)
        sys.exit(1)
