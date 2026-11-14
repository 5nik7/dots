"""Literal FZF option editing and explicit journaled application-file writes."""
import json
import os
from pathlib import Path
import shlex
import sys

from utility_commands import FZF_OPTIONS, FZF_COLORS, USAGE


def publish_text(target, text, action):
    """Publish one owner-selected file; never follow a managed source link."""
    sys.path.insert(0, str(Path(__file__).resolve().parent / 'files'))
    from transactions import Store, digest
    from file_platform import state_root
    target = Path(target).absolute()
    if target.is_symlink() or getattr(target, 'is_junction', lambda: False)():
        raise ValueError('target is a managed link; edit its owning source instead: ' + str(target))
    before = digest(target)
    if target.is_file() and target.read_bytes() == text.encode('utf-8'):
        return None
    result = Store(state_root()).apply(action, [dict(path=str(target), text=text)],
                                      {str(target): before}, retain=True)
    return result.get('id')


def option_words(value):
    if value.startswith('"') and value.endswith('"'):
        value = value[1:-1]
    return shlex.split(value, posix=True)


def split_entries(value):
    """Keep commas inside FZF action parentheses and escaped commas literal."""
    result = []; start = depth = 0; escaped = False
    for index, char in enumerate(value):
        if escaped: escaped = False; continue
        if char == '\\': escaped = True; continue
        if char == '(': depth += 1
        elif char == ')' and depth: depth -= 1
        elif char == ',' and not depth: result.append(value[start:index]); start = index + 1
    result.append(value[start:])
    return [item for item in result if item]


def get_option(words, key):
    for index, word in enumerate(words):
        if word == '--' + key:
            return words[index + 1] if index + 1 < len(words) else ''
        if word.startswith('--' + key + '='):
            return word.partition('=')[2]
    return ''


def set_option(words, key, value):
    result = []; index = 0; inserted = False
    while index < len(words):
        word = words[index]
        if word == '--' + key or word.startswith('--' + key + '='):
            if not inserted and value is not None:
                result.append('--' + key + '=' + value); inserted = True
            if word == '--' + key and index + 1 < len(words) and not words[index + 1].startswith('--'):
                index += 1
        else: result.append(word)
        index += 1
    if not inserted and value is not None: result.append('--' + key + '=' + value)
    return result


def edit(value, arguments):
    words = option_words(value); arguments = list(arguments)
    while arguments:
        key = arguments.pop(0)
        if key in ('color', 'bind'):
            if len(arguments) < 2: raise ValueError(key + ' requires KEY VALUE')
            item, setting = arguments[:2]; del arguments[:2]
            if key == 'color' and item not in FZF_COLORS: raise ValueError('unknown FZF color key: ' + item)
            entries = split_entries(get_option(words, key))
            entries = [part for part in entries if part.partition(':')[0] != item]
            entries.append(item + ':' + setting)
            words = set_option(words, key, ','.join(entries))
        elif key in ('uncolor', 'unbind'):
            removals = []
            while arguments and arguments[0] not in ('color', 'bind', 'uncolor', 'unbind'):
                item = arguments.pop(0)
                if key == 'uncolor' and item not in FZF_COLORS:
                    print('fzopt: unknown color key ignored: ' + item, file=sys.stderr)
                else: removals.append(item)
            if not removals: raise ValueError(key + ' requires at least one supported key')
            base = 'color' if key == 'uncolor' else 'bind'
            entries = [part for part in split_entries(get_option(words, base)) if part.partition(':')[0] not in removals]
            words = set_option(words, base, ','.join(entries) if entries else None)
        else:
            base = key[3:] if key.startswith('no-') else key
            if base not in FZF_OPTIONS: raise ValueError('unknown FZF option: ' + key)
            if not arguments: raise ValueError(key + ' requires a value')
            words = set_option(words, key, arguments.pop(0))
    return ' '.join(shlex.quote(word) for word in words)


def emit(environment=None, output=''):
    if os.environ.get('DOTS_UTILITY_TRANSPORT') == 'powershell':
        print(json.dumps(dict(environment=environment, output=output), ensure_ascii=True))
    elif output:
        print(output, end='')


def main(arguments):
    if not arguments or arguments[0] in ('help', '-h', '--help'):
        emit(output='Usage: ' + USAGE['fzopt'] + '\nSession changes update FZF_DEFAULT_OPTS. write-rc journals ~/.fzfrc; it does not activate a profile.\n')
        return 0
    original = os.environ.get('FZF_DEFAULT_OPTS', '')
    if not original:
        print('fzopt: FZF_DEFAULT_OPTS is empty', file=sys.stderr)
        return 1
    try:
        if arguments[0] == 'dump':
            emit(output=original.replace(' --', '\n--') + '\n')
        elif arguments[0] == 'write-rc':
            target = Path.home() / '.fzfrc'
            record = publish_text(target, original.replace(' --', '\n--') + '\n', 'fzopt-write-rc')
            message = 'fzopt: ' + ('wrote ' if record else 'unchanged ') + str(target) + '\n'
            if record: message += 'Recovery transaction ' + record + '\n'
            emit(output=message)
        else:
            emit(environment=edit(original, arguments))
        return 0
    except (ValueError, OSError) as error:
        print('fzopt: ' + str(error), file=sys.stderr)
        return 1
