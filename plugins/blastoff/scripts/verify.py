#!/usr/bin/env python3
"""Verify source payload against CHECKSUMS.json. No writes or dependency downloads."""
import hashlib
import json
from pathlib import Path
import shlex
import sys
ROOT = Path(__file__).resolve().parent.parent

# Share this boundary with package.py: never scan arbitrary checkout files,
# credentials or live agent logs into a distributable archive.
SOURCE_PATHS = ('AGENTS.md', 'README.md', 'LICENSE', 'VERSION', 'CHANGELOG.md',
                '.gitignore', 'install.sh', 'uninstall.sh', 'install.ps1', 'uninstall.ps1',
                'assets', 'bin', 'completions', 'docs', 'lib',
                'man', 'powershell', 'scripts', 'tests', '.pi/settings.json',
                '.pi/prompts', '.pi/skills', '.local/src', '.local/logo')

def source_files(root=ROOT):
    files = []
    def visit(p):
        if p.name == '__pycache__' or p.suffix in {'.pyc', '.pyo'}:
            return
        if p.is_symlink():
            raise ValueError('Symlink in source inventory: ' + str(p.relative_to(root)))
        if p.is_dir():
            for child in sorted(p.iterdir()):
                visit(child)
        elif p.is_file():
            files.append(p)
        elif p.exists():
            raise ValueError('Non-regular source path: ' + str(p.relative_to(root)))
    for relative in SOURCE_PATHS:
        visit(root/relative)
    return sorted(files)

def _verify(root):
    manifest = root/'CHECKSUMS.json'
    if manifest.is_symlink():
        raise ValueError('Checksum manifest is a symlink')
    values = json.loads(manifest.read_text())
    if not isinstance(values, dict) or not isinstance(values.get('files'), dict):
        raise ValueError('Invalid CHECKSUMS.json: expected a version and file checksum mapping')
    version_changed = values.get('version') != (root/'VERSION').read_text().strip()
    actual = {p.relative_to(root).as_posix() for p in source_files(root)}
    expected = set(values['files'])
    added = sorted(actual - expected)
    missing = sorted(expected - actual)
    changed = []
    for relative, checksum in sorted(values['files'].items()):
        candidate = Path(relative)
        if candidate.is_absolute() or '..' in candidate.parts:
            raise ValueError('Unsafe checksum path: '+relative)
        if relative not in actual:
            continue
        file = root/candidate
        if file.is_symlink() or not file.is_file():
            raise ValueError('Not a regular source file: '+relative)
        if hashlib.sha256(file.read_bytes()).hexdigest() != checksum:
            changed.append(relative)
    if version_changed or added or missing or changed:
        details = ['Checksum manifest version differs from VERSION'] if version_changed else []
        if added or missing:
            details.append('Source file inventory differs from CHECKSUMS.json')
        details.extend('Added: ' + json.dumps(path, ensure_ascii=False) for path in added)
        details.extend('Missing: ' + json.dumps(path, ensure_ascii=False) for path in missing)
        details.extend('Checksum mismatch: ' + path for path in changed)
        details.append('Restore missing or unexpectedly changed files; review unexpected added files before proceeding.')
        details.append('Only after reviewing intentional edits, rebuild from the source root, then review the dry-run:')
        details.append('  cd -- ' + shlex.quote(str(root.resolve())) + ' && bash scripts/build.sh')
        details.append('  cd -- ' + shlex.quote(str(root.resolve())) + ' && bash install.sh --dry-run')
        raise ValueError('\n'.join(details))
    return len(values['files'])

def verify(root=ROOT):
    try:
        return _verify(root)
    except (OSError, ValueError, KeyError, TypeError) as error:
        message = str(error)
        if 'bash scripts/build.sh' not in message:
            message += ('\nRestore missing/unsafe files from a trusted source and review all intentional edits first.'
                        '\nThen rebuild and preview from the source root:'
                        '\n  cd -- '+shlex.quote(str(root.resolve()))+' && bash scripts/build.sh'
                        '\n  cd -- '+shlex.quote(str(root.resolve()))+' && bash install.sh --dry-run')
        raise ValueError(message) from error


if __name__ == '__main__':
    try:
        print('Verified '+str(verify())+' source files.')
    except (OSError, ValueError, KeyError) as e:
        print('blastoff verification: '+str(e), file=sys.stderr)
        raise SystemExit(1)
