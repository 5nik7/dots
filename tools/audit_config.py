#!/usr/bin/env python3
"""Read-only candidate inventory; never execute or import inspected sources."""
import argparse
import hashlib
import json
from pathlib import Path
import re

ROOTS = ('default', 'profiles', 'config', 'shells', 'bin', 'scripts', 'lib', 'tools', 'plugins')
SKIP = {'.git', '__pycache__', 'node_modules', 'vendor', '.cache', 'cache', 'dist', 'build',
        'target', 'fixtures', 'testdata', 'tests', 'secrets'}
SUFFIXES = {'', '.py', '.lua', '.go', '.sh', '.bash', '.zsh', '.fish', '.ps1', '.nu', '.xsh',
            '.json', '.toml', '.conf', '.ini', '.yaml', '.yml', '.tpl', '.tsv'}
SENSITIVE = re.compile(r'(?i)(password|secret|credential|private.key|api.key|access.token|auth.token)')
PATTERNS = {
    'color': re.compile(r'#[0-9a-fA-F]{6}\b|\b(?:fg|bg|foreground|background|colour|color|highlight)\b', re.I),
    'icon': re.compile(r'[\ue000-\uf8ff\U000f0000-\U000ffffd\U00100000-\U0010fffd]|\b(?:icon|glyph|symbol|marker|pointer)\b', re.I),
    'formatting': re.compile(r'\b(?:indent|indentation|padding|spacing|alignment|align|label_gap|tabstop|shiftwidth|expandtab|separator|margin|layout|height|width|placement|statusline|status.format)\b', re.I),
    'option': re.compile(r'\b(?:DEFAULT_OPTS|default_location|timeout|ttl|max_stale|units|wrap|number|relativenumber|autoformat|animate|scrolloff|cmdheight)\b', re.I),
}


def scan(root, profiles=()):
    root = Path(root).resolve()
    excluded = []
    source = root / '.dots/sources.json'
    if source.is_file() and not source.is_symlink():
        for row in json.loads(source.read_text()).get('sources', []):
            if row.get('excluded') and isinstance(row.get('path'), str):
                candidate = root / row['path']
                if candidate.is_relative_to(root): excluded.append(candidate)
    result = dict(schema=1, root=str(root), coverage={}, findings=[], skipped={})
    def skip(reason): result['skipped'][reason] = result['skipped'].get(reason, 0) + 1
    for section in ROOTS:
        directory = root / section
        coverage = dict(files=0, findings=0, available=directory.is_dir())
        result['coverage'][section] = coverage
        pending = [directory] if directory.is_dir() and not directory.is_symlink() else []
        while pending:
            parent = pending.pop()
            for path in sorted(parent.iterdir(), reverse=True):
                relative = path.relative_to(root)
                if path.is_symlink(): skip('symlink'); continue
                if any(path == p or p in path.parents for p in excluded): skip('excluded-source'); continue
                if path.name in SKIP or path.name.startswith('test_') or path.name.startswith('.env') or SENSITIVE.search(path.name):
                    skip('excluded-name'); continue
                if profiles and relative.parts[0] == 'profiles' and len(relative.parts) > 1 and relative.parts[1] not in profiles:
                    skip('unselected-profile'); continue
                if path.is_dir(): pending.append(path); continue
                if not path.is_file() or path.suffix not in SUFFIXES: skip('non-source'); continue
                if path.stat().st_size > 1024 * 1024: skip('size-limit'); continue
                try: text = path.read_text(encoding='utf-8')
                except (UnicodeError, OSError): skip('unreadable'); continue
                if '\0' in text: skip('binary'); continue
                coverage['files'] += 1
                for line, value in enumerate(text.splitlines(), 1):
                    if SENSITIVE.search(value): continue
                    for kind, pattern in PATTERNS.items():
                        matches = pattern.findall(value)
                        if not matches: continue
                        # Never emit arbitrary source text or configuration values.
                        tokens = sorted({('U+%04X' % ord(m)) if len(m) == 1 and ord(m) >= 0xe000 else m.lower() for m in matches})
                        identity = '%s:%s:%s:%s' % (relative.as_posix(), line, kind, ','.join(tokens))
                        declaration = path.name in ('icons.toml', 'colors.toml', 'profile.json') or section == 'default'
                        result['findings'].append(dict(id=hashlib.sha256(identity.encode()).hexdigest()[:16],
                            path=relative.as_posix(), line=line, kind=kind, tokens=tokens,
                            review='declaration' if declaration else 'candidate'))
                        coverage['findings'] += 1
    result['findings'].sort(key=lambda r: (r['path'], r['line'], r['kind']))
    result['limitations'] = ['Candidates require consumer/ownership review; matches do not prove missing integration.',
                            'Excluded, binary, oversized and symlinked inputs are reported, never followed or executed.',
                            'Active external application files require an explicitly scoped owning-adapter review.']
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--profile', action='append', default=[], help='Restrict profile directories; default: all')
    args = parser.parse_args()
    if not args.root.is_dir(): parser.error('root must be an existing directory')
    if any(not re.fullmatch(r'[a-z][a-z0-9_-]*', p) for p in args.profile): parser.error('invalid profile ID')
    print(json.dumps(scan(args.root, args.profile), ensure_ascii=True, indent=2))


if __name__ == '__main__': main()
