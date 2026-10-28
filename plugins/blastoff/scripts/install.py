#!/usr/bin/env python3
"""Offline lifecycle: inspect, plan, then apply verified owned changes."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import stat
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent.parent


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


core = module('blastoff_core', ROOT/'lib/blastoff.py')
integration = module('blastoff_integration', ROOT/'scripts/integration.py')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def native_termux():
    return core.ui_module('host_platform').detect()['environment'] == 'termux'


def default_prefix(platform=None):
    termux = platform['environment'] == 'termux' if platform else native_termux()
    if termux:
        value = os.environ.get('PREFIX')
        if not value:
            raise core.Failure('Native Termux requires PREFIX; set it or pass --prefix PATH.', 2)
        return integration.absolute(core, value)
    if os.name == 'nt' and os.environ.get('LOCALAPPDATA'):
        return integration.absolute(core, os.environ['LOCALAPPDATA'])/'Programs/Blastoff'
    return Path.home()/'.local'


def manifest_path(prefix):
    return prefix/'share/blastoff/install.json'


def version_tuple(version):
    if not isinstance(version, str) or not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', version):
        raise core.Failure('Invalid installed release version; preserve/review the ownership manifest.')
    return tuple(int(part) for part in version.split('.'))


def empty_manifest():
    return {'format': 2, 'version': None, 'files': {}, 'integration': None, 'backups': {}}


def validate_manifest(doc, prefix):
    if not isinstance(doc, dict) or doc.get('format') not in (1, 2) or not isinstance(doc.get('files'), dict):
        raise core.Failure('Unknown ownership manifest format; preserve it and use a compatible installer.')
    version_tuple(doc.get('version'))
    integration.validate(core, doc.get('integration'))
    external = {item['path'] for item in (doc.get('integration') or {}).get('files', {}).values()}
    for value, checksum in doc['files'].items():
        entry = integration.absolute(core, value)
        if (not entry.is_relative_to(prefix) and value not in external) or entry == manifest_path(prefix):
            raise core.Failure('Unsafe path in ownership manifest: '+value)
        if not isinstance(checksum, str) or not re.fullmatch('[0-9a-f]{64}', checksum):
            raise core.Failure('Invalid manifest checksum: '+value)
    for item in (doc.get('integration') or {}).get('files', {}).values():
        if doc['files'].get(item['path']) != item['sha256']:
            raise core.Failure('Integration ownership checksum disagrees with file ownership')
    for value, checksum in doc.get('backups', {}).items():
        entry = integration.absolute(core, value)
        if not entry.is_relative_to(prefix/'share/blastoff/profile-backups') or not re.fullmatch('[0-9a-f]{64}', checksum):
            raise core.Failure('Unsafe profile backup ownership')
    migration = doc.get('migration')
    if migration:
        legacy = Path.home()/'.local'
        if migration.get('prefix') != str(legacy) or legacy == prefix or migration.get('state') != 'cleanup':
            raise core.Failure('Unsafe pending migration record')
        old = migration.get('manifest')
        if not isinstance(old, dict) or old.get('migration'):
            raise core.Failure('Invalid nested migration record')
        validate_manifest(old, legacy)
    return doc


def load_manifest(path, prefix):
    integration.inspect(core, path)
    if not core.exists(path):
        return empty_manifest()
    return validate_manifest(json.loads(core.read(path)), prefix)


def payload(prefix):
    """The immutable runtime plus conventional public support destinations."""
    version_root = prefix/'share/blastoff/versions'/core.VERSION
    pending = {}
    for directory in ('bin', 'lib', 'powershell', 'completions', 'man', 'scripts'):
        for source in sorted((ROOT/directory).rglob('*')):
            if '__pycache__' in source.parts or source.suffix in ('.pyc', '.pyo'):
                continue
            if source.is_file():
                pending[version_root/source.relative_to(ROOT)] = (core.read(source), 0o755 if source.suffix == '.sh' or source == ROOT/'bin/blastoff' else 0o644)
    for name in ('install.sh', 'uninstall.sh', 'install.ps1', 'uninstall.ps1'):
        pending[version_root/name] = (core.read(ROOT/name), 0o755)
    if os.name != 'nt':
        bash = shutil.which('bash')
        if not bash:
            raise core.Failure('Bash is required for the Bash command; install Bash and retry.', 3)
        if any(c in bash for c in '\r\n '):
            raise core.Failure('Bash executable path cannot contain whitespace in its shebang')
        executable = version_root/'bin/blastoff'
        pending[prefix/'bin/blastoff'] = (('#!'+bash+'\nexec '+shlex.quote(bash)+' '+shlex.quote(str(executable))+' "$@"\n').encode(), 0o755)
    for suffix, location in [('bash', 'share/bash-completion/completions/blastoff'),
                             ('zsh', 'share/zsh/site-functions/_blastoff'),
                             ('fish', 'share/fish/vendor_completions.d/blastoff.fish')]:
        pending[prefix/location] = (core.read(ROOT/'completions'/('blastoff.'+suffix)), 0o644)
    pending[prefix/'share/man/man1/blastoff.1'] = (core.read(ROOT/'man/blastoff.1'), 0o644)
    return pending, version_root


class Plan:
    def __init__(self, action, prefix, doc, *, manifest=None, lock=None, backup_root=None):
        self.action, self.prefix, self.doc = action, prefix, doc
        self.current = doc['version'] or 'not installed'
        self.manifest = manifest if manifest is not None else manifest_path(prefix)
        self.backup_root = backup_root if backup_root is not None else prefix/'share/blastoff/profile-backups'
        self.writes = {}
        self.removes = set()
        self.expected = {}
        self.profiles = set()
        self.notes = []
        self.rows = []
        self.locks = {lock if lock is not None else prefix/'share/blastoff/.install.lock'}
        self.migration = None
        self.new_doc = None
        self.skip = False
        self.observe(self.manifest)

    def observe(self, path):
        if path not in self.expected:
            integration.inspect(core, path)
            self.expected[path] = core.fingerprint(path)
        return self.expected[path]

    def write(self, path, data, mode, reason):
        self.observe(path)
        if core.exists(path) and core.read(path) == data and stat.S_IMODE(path.stat().st_mode) == mode:
            return
        self.writes[path] = (data, mode)
        self.rows.append((reason, path))

    def remove(self, path, reason):
        if self.observe(path) is not None:
            self.removes.add(path)
            self.rows.append((reason, path))


def verify_owned(plan, doc, skip_files=(), skip_profiles=False):
    for name, checksum in {**doc['files'], **doc.get('backups', {})}.items():
        if name in skip_files:
            continue
        target = Path(name)
        if plan.observe(target) is not None and digest(core.read(target)) != checksum:
            raise core.Failure('Owned file has changed; preserve it and resolve before proceeding: '+name)
    for item in (() if skip_profiles else (doc.get('integration') or {}).get('profiles', {}).values()):
        target = Path(item['path'])
        if plan.observe(target) is not None:
            integration.remove_blocks(core, core.read(target), item)


def backup_profile(plan, path, data):
    if not core.exists(path) or core.read(path) == data:
        return
    before = core.read(path)
    if not before:
        return
    key = digest(str(path).encode())[:16]+'-'+digest(before)
    backup = plan.backup_root/(key+'.bak')
    known = plan.doc.get('backups', {})
    serial = 0
    while core.exists(backup) and known.get(str(backup)) != digest(before):
        # Uninstall deliberately retains recovery backups but removes its
        # manifest. Never adopt/overwrite such an unowned retained file.
        serial += 1
        backup = backup.with_name(key+'-'+str(serial)+'.bak')
    plan.write(backup, before, 0o600, 'back up profile')
    if plan.new_doc is not None:
        plan.new_doc.setdefault('backups', {})[str(backup)] = digest(before)


def profile_edits(plan, edits):
    for path, data in edits.items():
        plan.observe(path)
        plan.profiles.add(path)
        plan.locks.add(path.with_name('.'+path.name+'.blastoff.lock'))
        backup_profile(plan, path, data)
        if data is None:
            plan.remove(path, 'remove owned profile')
        else:
            mode = stat.S_IMODE(path.stat().st_mode) if core.exists(path) else 0o644
            plan.write(path, data, mode, 'update owned profile block')


def inspect_shadowing(plan, retired):
    if os.name == 'nt':
        return
    target = plan.prefix/'bin/blastoff'
    directories = os.environ.get('PATH', '').split(os.pathsep)
    reached = False
    for directory in directories:
        if not directory:
            continue
        candidate = Path(directory)/'blastoff'
        if candidate == target:
            reached = True
            break
        if core.exists(candidate) and os.access(candidate, os.X_OK):
            if str(candidate) in retired:
                plan.notes.append('Migrate shadowing owned command: '+str(candidate))
            else:
                raise core.Failure('Command shadowing by unrelated '+str(candidate)+
                                   '; preserve it, put '+str(target.parent)+' first on PATH, and retry.')
    if not reached:
        plan.notes.append('Selected bin directory needs activation in fresh shells: '+str(target.parent))
    exported = [key for key in os.environ if key.startswith('BASH_FUNC_blastoff')]
    if exported:
        raise core.Failure('An exported blastoff shell function shadows the command; remove it from your session manually and retry.')


def make_plan(action, prefix, public=False):
    doc = load_manifest(manifest_path(prefix), prefix)
    plan = Plan(action, prefix, doc)
    verify_owned(plan, doc)
    if action == 'uninstall':
        if doc.get('migration'):
            raise core.Failure('Migration cleanup is pending; rerun bash install.sh --prefix '+shlex.quote(str(prefix))+' before uninstalling.')
        if doc['version'] is None:
            plan.notes.append('Not installed; nothing to remove.')
            return plan
        _, profiles, _, notes, _ = integration.plan(core, prefix, None, doc.get('integration'), 'uninstall')
        plan.notes.extend(notes)
        profile_edits(plan, profiles)
        for name in doc['files']:
            plan.remove(Path(name), 'remove owned file')
        if doc.get('backups'):
            plan.notes.append('Profile recovery backups are retained under '+str(prefix/'share/blastoff/profile-backups'))
        return plan
    if doc['version'] and version_tuple(doc['version']) > version_tuple(core.VERSION):
        plan.skip = True
        plan.notes.append('Newer installed version; skip all changes (no downgrade).')
        return plan

    legacy = Path.home()/'.local'
    legacy_doc = None
    if doc.get('migration'):
        legacy_doc = doc['migration']['manifest']
        current_legacy = load_manifest(manifest_path(legacy), legacy)
        if current_legacy['version'] is not None and current_legacy != legacy_doc:
            raise core.Failure('Legacy ownership changed during pending migration; review both manifests before retrying.')
    elif public and legacy != prefix and core.exists(manifest_path(legacy)):
        legacy_doc = load_manifest(manifest_path(legacy), legacy)
    if legacy_doc:
        if doc['version'] is None:
            plan.current = legacy_doc['version']+' at '+str(legacy)+' (migration source)'
        if legacy.is_relative_to(prefix) or prefix.is_relative_to(legacy):
            raise core.Failure('Overlapping legacy and destination prefixes cannot be migrated safely.')
        if legacy_doc.get('migration'):
            raise core.Failure('Legacy installation has a pending migration; finish it first.')
        if version_tuple(legacy_doc['version']) > version_tuple(core.VERSION):
            plan.skip = True
            plan.notes.append('Newer legacy installation; skip all changes (no downgrade).')
            return plan
        verify_owned(plan, legacy_doc, skip_files=doc['files'] if doc.get('migration') else (),
                     skip_profiles=bool(doc.get('migration')))
        plan.observe(manifest_path(legacy))
        plan.locks.add(legacy/'share/blastoff/.install.lock')
        plan.migration = legacy_doc
        plan.notes.append('MIGRATION '+str(legacy)+' -> '+str(prefix)+'; only verified owned files will be retired.')
        if legacy_doc.get('integration') and doc.get('integration') and not doc.get('migration'):
            raise core.Failure('Both prefixes own integration; preserve and uninstall the old integration explicitly before migrating.')

    pending, version_root = payload(prefix)
    previous_integration = doc.get('integration') or (legacy_doc or {}).get('integration')
    files, profiles, record, notes, activation = integration.plan(
        core, prefix, version_root, previous_integration, 'install', enabled=public)
    if legacy_doc and previous_integration:
        if any(Path(item['path']) not in profiles for item in previous_integration.get('profiles', {}).values()):
            raise core.Failure('Cannot migrate integration for an unavailable shell; restore the shell or remove its owned integration before retrying.')
        for data in profiles.values():
            if data and str(legacy/'share/blastoff/integration').encode() in data:
                raise core.Failure('A legacy integration could not be migrated; restore its shell or remove the owned block manually before retrying.')
    pending.update(files)
    plan.notes.extend(notes)
    plan.notes.extend(activation)
    ownership = dict(doc['files'])
    old_files = {**(legacy_doc or {}).get('files', {}), **ownership}
    if public:
        inspect_shadowing(plan, (legacy_doc or {}).get('files', {}))
    for target, (data, mode) in pending.items():
        present = plan.observe(target) is not None
        if present and str(target) not in old_files:
            raise core.Failure('Refusing an unowned existing destination: '+str(target)+'; preserve/move it and retry.')
        if present and target.is_relative_to(version_root) and core.read(target) != data:
            raise core.Failure('Release version is immutable; bump VERSION and matching release identities before changing an installed version: '+str(target)+
                               '; then run bash scripts/build.sh and bash install.sh --dry-run.')
        plan.write(target, data, mode, 'refresh' if present else 'install')
        ownership[str(target)] = digest(data)
    # Retained hooks (including temporarily unavailable shells) must transfer
    # their file ownership too; do not delete a file still named by integration.
    for item in (record or {}).get('files', {}).values():
        name, checksum = item['path'], item['sha256']
        if name not in ownership:
            if old_files.get(name) != checksum:
                raise core.Failure('Cannot transfer unverified integration ownership: '+name)
            ownership[name] = checksum
    plan.new_doc = {'format': 2, 'version': core.VERSION, 'files': ownership, 'integration': record,
                    'backups': dict(doc.get('backups', {}))}
    if legacy_doc:
        plan.new_doc['migration'] = {'prefix': str(legacy), 'state': 'cleanup', 'manifest': legacy_doc}
        for name in legacy_doc['files']:
            if name not in ownership:
                plan.remove(Path(name), 'retire legacy owned file')
    profile_edits(plan, profiles)
    validate_manifest(plan.new_doc, prefix)
    return plan


def document_bytes(doc):
    return (json.dumps(doc, indent=2, sort_keys=True)+'\n').encode()


def recheck(plan):
    for path, expected in plan.expected.items():
        integration.inspect(core, path)
        if core.fingerprint(path) != expected:
            raise core.Failure('Destination changed after planning; retry after reviewing: '+str(path))


def replace(path, data, mode, expected):
    core.atomic(path, data, expected)
    os.chmod(path, mode)


def preflight(plan):
    """Read-only conflict checks shared by both public lifecycle frontends."""
    if plan.writes or plan.removes or plan.migration:
        for lock in plan.locks:
            if core.exists(lock):
                raise core.Failure('Another operation or stale lock exists: '+str(lock)+'; inspect before removing it.')
        for path in set(plan.writes) | plan.removes | {plan.manifest}:
            parent = path.parent
            while not core.exists(parent):
                parent = parent.parent
            if not os.access(parent, os.W_OK | os.X_OK):
                raise core.Failure('Destination parent is not writable: '+str(parent)+'; choose a writable destination or fix permissions.')


def apply(plan):
    if plan.skip or (plan.action == 'uninstall' and plan.doc['version'] is None):
        return
    # Avoid creating locks or touching mtimes for a genuinely identical install.
    if plan.action == 'install' and not plan.writes and not plan.removes and not plan.migration and plan.new_doc == plan.doc:
        return
    with core.locks(plan.locks):
        recheck(plan)
        changed = []
        try:
            for path, (data, mode) in plan.writes.items():
                before = core.read(path) if core.exists(path) else None
                previous_mode = stat.S_IMODE(path.stat().st_mode) if before is not None else None
                # Track before writing so a chmod failure also rolls back content.
                changed.append((path, before, previous_mode))
                replace(path, data, mode, plan.expected[path])
            if plan.action == 'install':
                core.atomic(plan.manifest, document_bytes(plan.new_doc), plan.expected[plan.manifest])
        except Exception:
            for path, before, mode in reversed(changed):
                if core.exists(path) and core.read(path) != plan.writes[path][0]:
                    # Do not undo another writer's work while rolling back.
                    continue
                if before is None:
                    if core.exists(path):
                        path.unlink()
                else:
                    replace(path, before, mode, core.fingerprint(path))
            raise
        # Target commit is durable before legacy cleanup. On failure, ownership
        # metadata keeps the exact cleanup inventory for the next invocation.
        for path in sorted(plan.removes, key=str):
            integration.inspect(core, path)
            if core.fingerprint(path) != plan.expected[path]:
                raise core.Failure('Owned file changed before removal; preserve/review and retry: '+str(path))
            path.unlink()
        if plan.action == 'uninstall':
            if core.fingerprint(plan.manifest) != plan.expected[plan.manifest]:
                raise core.Failure('Ownership manifest changed during uninstall; review before retrying.')
            plan.manifest.unlink()
        elif plan.migration:
            legacy_manifest = manifest_path(Path.home()/'.local')
            if core.exists(legacy_manifest):
                if core.fingerprint(legacy_manifest) != plan.expected[legacy_manifest]:
                    raise core.Failure('Legacy manifest changed during cleanup; review before retrying.')
                legacy_manifest.unlink()
            completed = dict(plan.new_doc)
            completed.pop('migration')
            core.atomic(plan.manifest, document_bytes(completed), core.fingerprint(plan.manifest))


class Output:
    def __init__(self, color):
        self.color = 'NO_COLOR' not in os.environ and (color == 'always' or
                     (color == 'auto' and sys.stdout.isatty() and os.environ.get('TERM') != 'dumb'))

    def row(self, label, value):
        name = ('\033[35m'+label+'\033[0m') if self.color else label
        print('  '+name+' '*(10-len(label))+str(value))

    def show(self, plan, dry, platform=None):
        print('Blastoff '+plan.action)
        self.row('VERSION', core.VERSION)
        if platform:
            self.row('SYSTEM', platform['label'])
        self.row('PREFIX', plan.prefix)
        if dry:
            self.row('DRY RUN', 'preview only; no files will change')
        self.row('CURRENT', plan.current)
        for note in plan.notes:
            self.row('PLAN', note)
        # Keep internal payload inventories out of ordinary human output.
        grouped = {}
        for reason, path in plan.rows:
            marker = next((parent for parent in path.parents if parent.parent.name == 'versions' and parent.parent.parent.name == 'blastoff'), None)
            if marker:
                grouped[(reason, marker)] = grouped.get((reason, marker), 0)+1
            else:
                self.row('PLAN', reason+' '+str(path))
        for (reason, path), count in grouped.items():
            self.row('PLAN', f'{reason} runtime {path.name} ({count} files, including artwork and lifecycle helpers)')
        if not plan.rows and not plan.notes:
            self.row('PLAN', 'already current; no changes needed')


def run(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    shell, shell_os = 'python', ''
    if argv[:1] == ['--_bash-host-v1']:
        if len(argv) < 3:
            raise core.Failure('Invalid Bash lifecycle host context', 3)
        shell, shell_os = 'bash', argv[1]
        argv = argv[2:]
    elif argv[:1] == ['--_powershell-argv-v1']:
        try:
            argv, _ = core.ui_module('argv_transport').decode(argv, aliases=False)
        except ValueError as error:
            raise core.Failure(str(error), 3) from error
        shell = 'powershell'
    public = len(argv) >= 2 and argv[0] in ('install', 'uninstall') and argv[1] == '--public'
    parser = argparse.ArgumentParser(prog='bash '+argv[0]+'.sh' if public else None,
                                     description='Offline Blastoff lifecycle; themes and Starship configuration are preserved.')
    if public:
        parser.set_defaults(action=argv[0], public=True)
        argv = argv[2:]
    else:
        parser.add_argument('action', choices=['install', 'uninstall'])
        parser.set_defaults(public=False)
    parser.add_argument('--prefix', help='destination: native Termux PREFIX, otherwise a writable user prefix')
    parser.add_argument('--yes', action='store_true', help=argparse.SUPPRESS if public else 'approve legacy entry-point operations')
    parser.add_argument('-v', '--verbose', action='store_true', help='detailed planned actions on stderr')
    parser.add_argument('--dry-run', action='store_true', help='preview only; no files will change')
    parser.add_argument('--version', action='version', version='blastoff '+core.VERSION)
    parser.add_argument('--color', choices=['auto', 'always', 'never'], default='auto')
    args = parser.parse_args(argv)
    try:
        platforms = core.ui_module('host_platform')
        platform = platforms.validate(platforms.detect(shell, shell_os))
    except ValueError as error:
        raise core.Failure(str(error), 3) from error
    if args.action == 'install':
        verifier = module('blastoff_verify', ROOT/'scripts/verify.py')
        verifier.verify(ROOT)
    prefix = integration.absolute(core, args.prefix) if args.prefix is not None else default_prefix(platform)
    if prefix == Path(prefix.anchor):
        raise core.Failure('Refusing filesystem root as installation prefix', 2)
    plan = make_plan(args.action, prefix, args.public)
    preflight(plan)
    if args.verbose:
        for detail in [*platform['evidence'], 'Python executable: '+platform['python']]:
            safe = ''.join(c if c.isprintable() else ascii(c)[1:-1] for c in detail)
            print('blastoff: debug: '+safe, file=sys.stderr)
        for reason, target in plan.rows:
            safe = ''.join(c if c.isprintable() else ascii(c)[1:-1] for c in str(target))
            print('blastoff: debug: '+reason+' '+safe, file=sys.stderr)
    output = Output(args.color)
    output.show(plan, args.dry_run, platform)
    if args.dry_run:
        output.row('DONE', 'preview complete; no files changed')
        return 0
    if not args.public and not args.yes:
        raise core.Failure('Legacy entry point: review --dry-run, then pass --yes; or use bash '+args.action+'.sh.', 2)
    apply(plan)
    output.row('DONE', 'no files changed' if plan.skip or (args.action == 'uninstall' and plan.doc['version'] is None)
               else args.action+' complete; user data preserved')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(run())
    except (core.Failure, OSError, ValueError, KeyError, TypeError) as error:
        print('blastoff lifecycle: '+str(error), file=sys.stderr)
        raise SystemExit(error.code if isinstance(error, core.Failure) else 1)
