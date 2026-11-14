"""On-demand Bak grammar and bounded ID completion; never inspect payloads."""
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bak_commands import COMMANDS, COMMON, OPTIONS
from completion_records import candidate_record, requested


def complete(words, shell='bash', *, display_types=False):
    current = words[-1] if words else ''
    action = ''; positional = []; pending = None; literal = False
    all_options = {row[0]: row for rows in [COMMON, *OPTIONS.values()] for row in rows}
    aliases = {row[1]: row[0] for row in all_options.values() if row[1]}
    for word in words[:-1]:
        if pending:
            pending = None
        elif not literal and word == '--':
            literal = True
        elif not literal and word.startswith('-'):
            flag, equal, _ = word.partition('='); flag = aliases.get(flag, flag)
            if flag not in all_options: return
            if all_options[flag][2] != 'flag' and not equal: pending = flag
        elif not action and not positional and not literal and word in COMMANDS:
            action = word
        else:
            positional.append(word)
    lead = ''
    if not literal and current.startswith('--') and '=' in current:
        pending, _, current = current.partition('='); lead = pending + '='
    def emit(value, description='', role='value'):
        if value.startswith(current) and not any(ord(c) < 32 or 127 <= ord(c) < 160 for c in value):
            description = ''.join(c if ord(c) >= 32 and not 127 <= ord(c) < 160 else ' ' for c in description)
            print('\t'.join(candidate_record(lead + value, description, role, display_types=display_types)))
    def paths(kind):
        if shell not in ('nu', 'xonsh'):
            print(kind + '\t' + lead + '\t'); return
        # Native adapters consume literal candidates and own shell escaping.
        prefix = current.rsplit(os.sep, 1)[0] + os.sep if os.sep in current else ''
        directory = Path(os.path.expanduser(prefix or '.'))
        try:
            with os.scandir(directory) as entries:
                for index, entry in enumerate(entries):
                    if index >= 4096: break
                    if entry.name.startswith('.') and not Path(current).name.startswith('.'): continue
                    is_dir = entry.is_dir()
                    if kind == 'directory' and not is_dir: continue
                    emit(prefix + entry.name + (os.sep if is_dir else ''), 'Directory' if is_dir else 'File')
        except OSError: pass
    options = COMMON + OPTIONS.get(action or 'create', [])
    if pending:
        row = next((r for r in options if r[0] == pending), None)
        if not row: return
        kind = row[2]
        if kind in ('file', 'directory'): paths(kind)
        elif kind.startswith('choice:'):
            for choice in kind[7:].split(','): emit(choice)
        return
    if current.startswith('-') and not literal:
        for flag, short, _, description in options:
            emit(flag, description, 'option')
            if short: emit(short, description, 'option')
        emit('--help', 'Show help', 'option'); return
    if not action or action in ('create', 'import'):
        if not action and not positional and not literal:
            for key, row in COMMANDS.items():
                if key: emit(key, row[0], 'command')
        paths('file'); return
    if action not in ('show', 'restore', 'delete') or positional and action != 'delete': return
    from files.file_platform import state_root
    sys.path.insert(0, str(Path(__file__).resolve().parent / 'files'))
    from backup_catalog import bounded_json, ID
    doc = bounded_json(state_root() / 'bak/catalog.json', {'schema': 1, 'entries': {}})
    if not isinstance(doc, dict) or doc.get('schema') != 1 or not isinstance(doc.get('entries'), dict): return
    home = str(Path.home())
    for identity, record in doc['entries'].items():
        if not ID.fullmatch(identity) or identity in positional or not isinstance(record, dict): continue
        if record.get('id') != identity: continue
        original = record.get('original') or record.get('path') or ''
        if not isinstance(original, str): continue
        if original == home or original.startswith(home + os.sep): original = '~' + original[len(home):]
        emit(identity, original)


if __name__ == '__main__':
    try: complete(sys.argv[2:], shell=sys.argv[1], display_types=requested())
    except (ValueError, OSError, KeyError, TypeError): pass
