"""Receipt-led migration of retired application installations into Dots.

Discovery is bounded to known installer layouts. Receipts identify candidates;
their paths never grant arbitrary deletion authority. Store owns all mutation.
"""
import hashlib
import json
import os
from pathlib import Path
import stat

from transactions import exists, digest, parents_safe


LIMIT = 4 * 1024 * 1024


def read(path):
    parents_safe(path)
    if not stat.S_ISREG(path.lstat().st_mode) or path.stat().st_size > LIMIT:
        raise ValueError('legacy receipt must be a bounded regular file: ' + str(path))
    return json.loads(path.read_text(encoding='utf-8'))


def matches(path, expected):
    parents_safe(path)
    return (exists(path) and stat.S_ISREG(path.lstat().st_mode)
            and hashlib.sha256(path.read_bytes()).hexdigest() == expected)


class Migration:
    def __init__(self, installation):
        self.installation = installation
        self.home = Path.home()
        self.prefixes = [self.home / '.local']
        if installation.platform == 'termux':
            prefix = Path(os.environ.get('PREFIX', '/data/data/com.termux/files/usr'))
            if not prefix.is_absolute() or '..' in prefix.parts:
                raise ValueError('Termux PREFIX must be an absolute normalized path')
            if prefix not in self.prefixes:
                self.prefixes.append(prefix)
        elif installation.platform in ('linux', 'wsl'):
            self.prefixes.append(Path('/usr/local'))
        self.verified = set()
        self.retired = set()

    def note(self, path, reason, status='retained'):
        self.installation.item('legacy:applications', status, path, reason=reason)

    def conflict(self, path, reason):
        self.note(path, reason, 'conflict')

    def inventory(self):
        """Report bounded wiring/recovery candidates without running a shell."""
        seen = set()
        directories = [Path(p) for p in os.environ.get('PATH', '').split(os.pathsep)[:128]
                       if p and Path(p).is_absolute()]
        directories += [p / 'bin' for p in self.prefixes]
        for directory in directories:
            for name in ('dots', 'anodize', 'blastoff', 'pkgs'):
                path = directory / name
                if str(path) in seen or not exists(path): continue
                seen.add(str(path))
                self.note(path, 'Command candidate; ' + ('links to ' + os.readlink(path) if path.is_symlink() else 'regular executable path'), 'unchanged')
        for path in (self.home / '.config/blastoff', self.home / '.config/pkgs',
                     self.installation.root / 'scripts/pkgs.old'):
            if exists(path): self.note(path, 'Application data or historical source; retained')
        startup = [self.home / name for name in ('.profile', '.bashrc', '.bash_profile', '.zshrc', '.zprofile')]
        startup += [self.home / '.config/fish/conf.d/pkgs.fish']
        retired_roots = [str(prefix / suffix) for prefix in self.prefixes
                         for suffix in ('lib/pkgs', 'share/blastoff')]
        for path in startup:
            if path.is_file() and path.stat().st_size <= LIMIT:
                text = path.read_text(encoding='utf-8', errors='replace')
                if any(root in text for root in retired_roots):
                    self.conflict(path, 'Startup references a legacy payload; reconcile this custom integration first')
                elif any(name in text.lower() for name in ('blastoff', 'pkgs', 'anodize')):
                    self.note(path, 'Application startup reference retained; no profile execution or rewriting')

    def verify(self, path, expected):
        self.installation.guard(path)
        if not matches(path, expected):
            raise ValueError('legacy file changed or disappeared: ' + str(path))
        self.verified.add(str(path))

    def blastoff(self, prefix):
        root = prefix / 'share/blastoff'
        receipt = root / 'install.json'
        if not exists(receipt):
            if exists(root): self.note(root, 'No supported installation receipt; retained')
            return
        self.installation.guard(receipt)
        doc = read(receipt)
        if doc.get('format') not in (1, 2) or not isinstance(doc.get('files'), dict):
            raise ValueError('unsupported Blastoff installation receipt: ' + str(receipt))
        external = {prefix / 'bin/blastoff', prefix / 'share/man/man1/blastoff.1',
                    prefix / 'share/bash-completion/completions/blastoff',
                    prefix / 'share/zsh/site-functions/_blastoff',
                    prefix / 'share/zsh/functions/Completion/Unix/_blastoff',
                    prefix / 'share/fish/vendor_completions.d/blastoff.fish'}
        files = set()
        for value, expected in doc['files'].items():
            path = Path(value)
            if (not path.is_absolute() or '..' in path.parts or str(path) != value
                    or not (path in external or root / 'versions' in path.parents)):
                raise ValueError('Blastoff receipt claims an unsupported destination: ' + value)
            if not isinstance(expected, str) or len(expected) != 64:
                raise ValueError('invalid legacy file checksum')
            self.verify(path, expected)
            files.add(path)
        integration = doc.get('integration', {})
        if integration.get('files') or integration.get('profiles') or doc.get('backups'):
            raise ValueError('Blastoff has additional integration or backup ownership; manual reconciliation required')
        if prefix / 'bin/blastoff' not in files:
            raise ValueError('Blastoff receipt does not own its launcher')
        payload = {p for p in root.rglob('*') if p.is_file() or p.is_symlink()}
        if payload <= files | {receipt}:
            self.retired.add(root)
            self.installation.guard(root)
        else:
            self.retired.update(p for p in files if root in p.parents)
            self.retired.add(receipt)
            for p in sorted(payload - files - {receipt}):
                self.note(p, 'Unrecorded legacy payload retained')
        self.retired.update(files & external)

    def pkgs(self, prefix):
        root = prefix / 'lib/pkgs'
        receipt = root / 'install.json'
        if not exists(receipt):
            if exists(root): self.note(root, 'No supported installation receipt; retained')
            return
        self.installation.guard(receipt)
        doc = read(receipt)
        source = self.installation.root / 'plugins/pkgs'
        sums = source / 'SHA256SUMS'
        self.installation.guard(sums)
        if (doc.get('marker') != 'pkgs-user-install-v1'
                or doc.get('version') != (source / 'VERSION').read_text().strip()):
            raise ValueError('unsupported pkgs installation identity: ' + str(receipt))
        self.installation.guard(root / 'SHA256SUMS')
        recorded = {name: value for value, name in
                    (line.split(maxsplit=1) for line in (root / 'SHA256SUMS').read_text().splitlines())}
        supported = {name: value for value, name in
                     (line.split(maxsplit=1) for line in sums.read_text().splitlines())}
        alternatives = source / 'legacy-checksums.json'
        self.installation.guard(alternatives)
        old = read(alternatives)['alternatives']
        if set(recorded) != set(supported) or any(
                value != supported[name] and value not in old.get(name, []) for name, value in recorded.items()):
            raise ValueError('pkgs release checksums differ from supported imported releases')
        files = {receipt, root / 'SHA256SUMS'}
        for name, expected in recorded.items():
            name = name.lstrip('*')
            relative = Path(name)
            if relative.is_absolute() or '..' in relative.parts:
                raise ValueError('invalid pkgs release path')
            path = root / relative
            self.verify(path, expected)
            files.add(path)
        for target, destination in ((prefix / 'bin/pkgs', root / 'pkgs'),
                                    (prefix / 'share/man/man1/pkgs.1', root / 'docs/pkgs.1')):
            self.installation.guard(target)
            if exists(target):
                if not target.is_symlink() or target.resolve() != destination.resolve():
                    raise ValueError('legacy pkgs link changed: ' + str(target))
                self.verified.add(str(target)); self.retired.add(target)
        payload = {p for p in root.rglob('*') if p.is_file() or p.is_symlink()}
        if payload <= files:
            self.installation.guard(root)
            self.retired.add(root)
        else:
            self.retired.update(files)
            for p in sorted(payload - files): self.note(p, 'Unrecorded legacy payload retained')

    def completions(self):
        state = Path(os.environ.get('XDG_STATE_HOME') or self.home / '.local/state') / 'pkgs/completions.json'
        if not exists(state): return
        self.installation.guard(state)
        doc = read(state)
        if doc.get('format') != 1 or not isinstance(doc.get('shells'), dict):
            raise ValueError('unsupported pkgs completion receipt')
        data = Path(os.environ.get('XDG_DATA_HOME') or self.home / '.local/share')
        config = Path(os.environ.get('XDG_CONFIG_HOME') or self.home / '.config')
        allowed = {
            'bash': {data / 'bash-completion/completions/pkgs'},
            'zsh': {data / 'zsh/site-functions/_pkgs'},
            'fish': {config / 'fish/completions/pkgs.fish'},
        }
        for prefix in self.prefixes:
            allowed['bash'].add(prefix / 'share/bash-completion/completions/pkgs')
            allowed['zsh'].add(prefix / 'share/zsh/site-functions/_pkgs')
        source = self.installation.root / 'plugins/pkgs/completions'
        for shell, row in doc['shells'].items():
            path = Path(row.get('file', ''))
            if shell not in allowed or path not in allowed[shell]:
                raise ValueError('unsupported legacy completion destination: ' + str(path))
            if path.is_symlink() and path.resolve() == (source / ('pkgs.' + shell)).resolve():
                self.note(path, 'Current Dots completion; stale legacy ownership superseded', 'unchanged')
                continue
            self.installation.guard(path)
            if not exists(path):
                self.note(path, 'Missing legacy completion; stale ownership superseded', 'skipped')
                continue
            self.verify(path, row.get('hash'))
            # A receipt alone cannot authenticate an arbitrary file at this path.
            if path.read_bytes() != (source / ('pkgs.' + shell)).read_bytes():
                raise ValueError('legacy completion differs from the imported source: ' + str(path))
            self.retired.add(path)
        self.retired.add(state)

    def plan(self):
        self.inventory()
        for prefix in self.prefixes:
            for inspect in (self.blastoff, self.pkgs):
                try: inspect(prefix)
                except (ValueError, OSError, KeyError, TypeError) as error:
                    self.conflict(prefix, str(error))
        try: self.completions()
        except (ValueError, OSError, KeyError, TypeError) as error:
            self.conflict(self.home, str(error))
        self.installation.legacy_verified = self.verified
        self.installation.plan_bundled_apps(self.home)
        destinations = {op['path'] for op in self.installation.operations}
        for path in sorted(self.retired, key=str):
            if str(path) not in destinations:
                self.installation.retire('legacy:applications', path)
        # Existing recovery material and user data are inventoried, never retired.
        for prefix in self.prefixes:
            for path in sorted((prefix / 'lib').glob('pkgs.backup-*')):
                self.note(path, 'Existing installation backup retained')
        for directory in (self.home / '.config', self.home / '.local/share/bash-completion/completions',
                          self.home / '.local/share/zsh/site-functions',
                          self.home / '.config/fish/completions', self.home / '.config/fish/conf.d'):
            for pattern in ('.blastoff-edit-*', '*pkgs-backup-*'):
                for path in sorted(directory.glob(pattern)):
                    self.note(path, 'Existing recovery file retained')


def plan(installation):
    Migration(installation).plan()
