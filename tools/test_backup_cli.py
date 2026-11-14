#!/usr/bin/env python3
"""Backup entry points, native data transport and effective profile preferences."""
import base64
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import test_profile_config as fixtures


@unittest.skipIf(os.name == 'nt', 'POSIX entry points; use NativeBackupCLI on Windows')
class BackupCLI(unittest.TestCase):
    def setUp(self):
        fixtures.ProfileConfig.setUp(self)
        shutil.copytree(fixtures.ROOT / 'default', self.root / 'default')
        for path in [*fixtures.ROOT.glob('bin/dots-bak*'), fixtures.ROOT / 'bin/bak']:
            shutil.copy2(path, self.root / 'bin' / path.name)
        self.env['DOTS_PROGRESS'] = 'never'

    def run_bak(self, *args, code=0, native=False, direct=False, **env):
        if native:
            encoded = base64.b64encode(json.dumps(list(args)).encode()).decode()
            command = [sys.executable, '-B', str(self.root / 'lib/dots/native.py'), 'bak', encoded]
        elif direct:
            command = [str(self.root / 'bin/bak'), *args]
        else:
            command = [shutil.which('bash'), str(self.root / 'bin/dots'), 'bak', *args]
        result = subprocess.run(command, env=dict(self.env, **env), text=True, capture_output=True, timeout=30, cwd=self.home)
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        return result

    def source(self, name='source', text='original'):
        source = self.home / name
        source.write_text(text)
        return source

    def test_data_literal_native_move_and_retained_restore(self):
        source = self.source('雪 space "quotes"')
        result = self.run_bak('create', str(source), '--json', native=True, DOTS_COLOR='always', DOTS_ICONS='always')
        data = json.loads(result.stdout)
        self.assertNotIn('\x1b', result.stdout)
        self.assertFalse(source.exists())
        record = data['items'][0]
        self.assertTrue(Path(record['path']).is_file())
        self.run_bak('restore', record['id'], '--json')
        self.assertEqual(source.read_text(), 'original')
        self.assertTrue(Path(record['path']).exists())

    def test_quiet_copy_and_command_name_operand(self):
        source = self.source('list')
        result = self.run_bak('--copy','-q','--','list')
        self.assertEqual(result.stdout, '')
        self.assertEqual(result.stderr, '')
        self.assertEqual(source.read_text(), 'original')
        rows = json.loads(self.run_bak('list','--json').stdout)['items']
        self.assertEqual(len(rows), 1)
        self.run_bak('--quiet', '--', 'absent', code=1)

    def test_preview_help_and_list_are_inert(self):
        source = self.source()
        self.run_bak(str(source),'--dry-run','--json')
        self.run_bak('--help')
        self.run_bak(direct=True)
        self.run_bak('list','--json')
        self.assertTrue(source.exists())
        self.assertFalse((self.home / '.bakstore').exists())
        self.assertFalse((self.home / 'state').exists())

    def test_delete_requires_explicit_noninteractive_approval(self):
        row = json.loads(self.run_bak(str(self.source()),'--json').stdout)['items'][0]
        self.run_bak('delete',row['id'],'--json',code=1)
        self.run_bak('delete',row['id'],'--dry-run','--json')
        self.assertTrue(Path(row['path']).exists())
        self.run_bak('delete',row['id'],'--yes','--json')
        self.assertFalse(Path(row['path']).exists())

    def test_profile_preferences_and_flag_overrides(self):
        profile = json.loads(self.path.read_text())
        profile['apps'] = {'bak': {'mode': 'copy', 'location': 'store', 'store': str(self.home / 'custom backups')}}
        self.path.write_text(json.dumps(profile))
        source = self.source()
        row = json.loads(self.run_bak(str(source),'--json').stdout)['items'][0]
        self.assertTrue(source.exists())
        self.assertIn('custom backups', row['path'])
        row = json.loads(self.run_bak('--move','--in-place',str(source),'--json').stdout)['items'][0]
        self.assertFalse(source.exists())
        self.assertEqual(Path(row['path']).parent, source.parent)

    def test_standalone_ignores_stale_checkout_and_empty_path_refused(self):
        source = self.source()
        result = self.run_bak(str(source),'--json',direct=True,DOTS=str(self.home / 'stale'))
        self.assertEqual(json.loads(result.stdout)['status'], 'complete')
        self.run_bak('create','','--json',code=1)

    def test_browser_cancel_and_declined_restore_are_inert(self):
        from unittest.mock import patch
        sys.path.insert(0,str(fixtures.ROOT/'lib/dots'))
        import bak_cli
        from menus import Entry
        from interaction import SelectionEnded
        record=json.loads(self.run_bak(str(self.source()),'--json').stdout)['items'][0]
        before={p: p.read_bytes() for p in self.home.rglob('*') if p.is_file() and not p.is_symlink()}
        with patch.dict(os.environ,self.env), patch('bak_cli.terminal',return_value=True):
            with patch('menus.choose',return_value=None): bak_cli.main(['browse'])
            with patch('menus.choose',side_effect=[Entry(record['id'],'Source'),Entry('restore','Restore')]), patch('bak_cli.gum_confirm',return_value=False):
                with self.assertRaises(SelectionEnded) as caught: bak_cli.main(['browse'])
                self.assertEqual(caught.exception.status,130)
        self.assertEqual(before,{p:p.read_bytes() for p in self.home.rglob('*') if p.is_file() and not p.is_symlink()})


REQUESTED_POWERSHELL = os.environ.get('DOTS_TEST_POWERSHELL')
NATIVE_POWERSHELL = shutil.which(REQUESTED_POWERSHELL) if REQUESTED_POWERSHELL else None
if REQUESTED_POWERSHELL and not NATIVE_POWERSHELL:
    raise SystemExit('required PowerShell engine unavailable: ' + REQUESTED_POWERSHELL)


@unittest.skipUnless(os.name == 'nt' and NATIVE_POWERSHELL,
                     'native Windows requires explicit DOTS_TEST_POWERSHELL')
class NativeBackupCLI(unittest.TestCase):
    """Real PowerShell bridges, owned consumers, no Bash or personal startup."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='dots-native-bak-')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.home = self.base / 'home 雪'
        self.home.mkdir()
        # Native shells create standard AppData directories before script entry.
        # Supply those empty, owned directories before taking no-write snapshots.
        for name in ('AppData/Roaming', 'AppData/Local/Microsoft/PowerShell',
                     'AppData/Local/Microsoft/Windows/PowerShell'):
            (self.home / name).mkdir(parents=True, exist_ok=True)
        self.root = self.base / "checkout space ü ' [literal]"
        for name in ('lib/dots', 'default'):
            shutil.copytree(fixtures.ROOT / name, self.root / name,
                            ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        (self.root / 'bin').mkdir()
        for path in [fixtures.ROOT / 'bin/dots.ps1', fixtures.ROOT / 'bin/dots-link',
                     *fixtures.ROOT.glob('bin/dots-bak*')]:
            shutil.copy2(path, self.root / 'bin' / path.name)
        (self.root / 'scripts').mkdir()
        shutil.copy2(fixtures.ROOT / 'scripts/bak.ps1', self.root / 'scripts/bak.ps1')
        profile = self.root / 'profiles/windows'
        profile.mkdir(parents=True)
        (profile / 'profile.json').write_text(json.dumps(
            dict(schema=1, id='windows', settings={}, files={})), encoding='utf-8')
        self.runtime = self.base / 'runtime'
        self.runtime.mkdir()
        self.env = {key: os.environ[key] for key in
                    ('SystemRoot', 'WINDIR', 'COMSPEC', 'PATHEXT') if key in os.environ}
        self.env.update(HOME=str(self.home), USERPROFILE=str(self.home), OS='Windows_NT',
            DOTS=str(self.root), PATH=str(Path(sys.executable).parent),
            APPDATA=str(self.home / 'AppData/Roaming'), LOCALAPPDATA=str(self.home / 'AppData/Local'),
            XDG_CONFIG_HOME=str(self.home / 'config'), XDG_DATA_HOME=str(self.home / 'data'),
            XDG_STATE_HOME=str(self.home / 'state'), XDG_CACHE_HOME=str(self.home / 'cache'),
            CODEX_HOME=str(self.home / 'codex'), PSModulePath=str(self.runtime / 'modules'),
            PSModuleAnalysisCachePath=str(self.runtime / 'ModuleAnalysisCache'),
            TEMP=str(self.runtime), TMP=str(self.runtime), TMPDIR=str(self.runtime),
            POWERSHELL_TELEMETRY_OPTOUT='1', POWERSHELL_UPDATECHECK='Off',
            # Disable .NET's shell startup profiling writes, not Dots caches.
            DOTNET_MultiCoreJitNoProfileGather='1',
            PYTHONUTF8='1', PYTHONIOENCODING='utf-8', PYTHONDONTWRITEBYTECODE='1',
            PYTHON_MANAGER_AUTOMATIC_INSTALL='false',
            TERM='dumb', DOTS_COLOR='never', DOTS_ICONS='never', DOTS_PROGRESS='never')

    @staticmethod
    def literal(value):
        return "'" + str(value).replace("'", "''") + "'"

    def command(self, *args, code=0, standalone=False, family='bak'):
        if standalone and family != 'bak':
            raise ValueError('this fixture enrolls only the standalone Bak bridge')
        entry = self.root / ('scripts/bak.ps1' if standalone else 'bin/dots.ps1')
        forwarded = list(args) if standalone else [family, *args]
        script = "$ProgressPreference='SilentlyContinue'; $forwarded=@(" + ','.join(
            self.literal(value) for value in forwarded) + '); & ' + self.literal(
                entry) + ' @forwarded; exit $LASTEXITCODE'
        encoded = base64.b64encode(script.encode('utf-16le')).decode('ascii')
        result = subprocess.run([NATIVE_POWERSHELL, '-NoLogo', '-NoProfile',
            '-NonInteractive', '-EncodedCommand', encoded], cwd=self.home, env=self.env,
            stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding='utf-8', timeout=30)
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        return result

    def snapshot(self):
        # PowerShell's separately owned runtime cache is not a Dots consumer.
        # Include every home/config/state/data/cache member, including directories.
        # .NET Framework ignores Core's profiling switch. Its one known startup
        # profile remains allowed, as in test_native_cli's read-only acceptance.
        legacy_cache = self.home / 'AppData/Local/Microsoft/Windows/PowerShell'
        legacy_profile = legacy_cache / 'StartupProfileData-NonInteractive'
        result = {}
        for path in self.home.rglob('*'):
            info = path.lstat()
            if path == legacy_profile:
                self.assertTrue(path.is_file(), str(path))
                self.assertFalse(path.is_symlink(), str(path))
                self.assertFalse(getattr(info, 'st_file_attributes', 0) & 0x400, str(path))
                continue
            value = ('link', os.readlink(path)) if path.is_symlink() else (
                ('directory',) if path.is_dir() else ('file', path.read_bytes()))
            modified = 0 if path == legacy_cache and path.is_dir() else info.st_mtime_ns
            result[str(path.relative_to(self.home))] = (info.st_mode, modified, value)
        return result

    def source(self, name="-snow 雪 ' [a];literal.txt", data=b'original\x00bytes\r\n'):
        path = self.home / name
        path.write_bytes(data)
        return path

    def assert_home_unchanged(self, before):
        after = self.snapshot()
        changed = sorted(key for key in before.keys() | after.keys()
                         if before.get(key) != after.get(key))
        self.assertEqual(changed, [], 'changed owned home paths: ' + repr(changed))

    def test_move_restore_retains_backup_and_preserves_occupied_target(self):
        self.env.update(DOTS_COLOR='always', DOTS_ICONS='always')
        source = self.source()
        before = source.read_bytes()
        result = self.command('create', '--json', '--', source.name, standalone=True)
        self.assertEqual(result.stderr, '')
        self.assertNotIn('\x1b', result.stdout)
        row = json.loads(result.stdout)['items'][0]
        self.assertEqual(row['original'], str(source))
        self.assertFalse(source.exists())
        payload = Path(row['path'])
        self.assertTrue(payload.is_relative_to(self.home))
        self.assertEqual(payload.read_bytes(), before)
        source.write_bytes(b'occupied target')
        self.command('restore', row['id'], '--json')
        self.assertEqual(source.read_bytes(), before)
        self.assertEqual(payload.read_bytes(), before)
        rows = json.loads(self.command('list', '--json').stdout)['items']
        self.assertEqual(len(rows), 2)
        other = next(item for item in rows if item['id'] != row['id'])
        self.assertEqual(Path(other['path']).read_bytes(), b'occupied target')

    def test_preview_help_list_and_empty_operand_do_not_write(self):
        source = self.source()
        before = self.snapshot()
        legacy_cache = self.home / 'AppData/Local/Microsoft/Windows/PowerShell'
        unexpected = legacy_cache / 'unrelated-dots-cache'
        unexpected.write_bytes(b'not a PowerShell runtime profile')
        with self.assertRaises(AssertionError):
            self.assert_home_unchanged(before)
        unexpected.unlink()
        invalid = legacy_cache / 'StartupProfileData-NonInteractive'
        invalid.mkdir()
        with self.assertRaises(AssertionError):
            self.snapshot()
        invalid.rmdir()
        self.assert_home_unchanged(before)
        for standalone in (False, True):
            self.command('create', '--dry-run', '--json', '--', str(source), standalone=standalone)
            self.command('--help', standalone=standalone)
            self.command('list', '--json', standalone=standalone)
            self.command('create', '', '--json', code=1, standalone=standalone)
            self.assert_home_unchanged(before)

    def test_quiet_copy_literal_command_operand_and_missing_path(self):
        source = self.source('list')
        before = source.read_bytes()
        result = self.command('--copy', '--quiet', '--', 'list', standalone=True)
        self.assertEqual((result.stdout, result.stderr), ('', ''))
        self.assertEqual(source.read_bytes(), before)
        rows = json.loads(self.command('list', '--json').stdout)['items']
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['original'], str(source))
        snapshot = self.snapshot()
        self.command('create', '--json', '--', 'absent', code=1)
        self.assert_home_unchanged(snapshot)

    def test_changed_payload_restore_and_delete_refuse_without_writes(self):
        source = self.source()
        row = json.loads(self.command('create', '--json', '--', str(source)).stdout)['items'][0]
        Path(row['path']).write_bytes(b'changed backup')
        before = self.snapshot()
        for args in (('restore', row['id'], '--json'), ('delete', row['id'], '--yes', '--json')):
            result = self.command(*args, code=1)
            self.assertIn('missing or changed', result.stderr)
            self.assert_home_unchanged(before)

    def test_delete_requires_approval_and_preview_preserves_snapshot(self):
        source = self.source()
        row = json.loads(self.command('create', '--json', '--', str(source)).stdout)['items'][0]
        before = self.snapshot()
        self.command('delete', row['id'], '--json', code=1)
        self.command('delete', row['id'], '--dry-run', '--json')
        self.assert_home_unchanged(before)
        self.command('delete', row['id'], '--yes', '--json', standalone=True)
        self.assertFalse(Path(row['path']).exists())

    def test_absolute_and_relative_links_repeat_without_new_backups(self):
        source = self.source()
        original = source.read_bytes()
        source_info = source.stat()
        for number, relative in enumerate((False, True), 1):
            target = self.home / ('relative target' if relative else 'absolute target')
            target.write_bytes(b'occupied target')
            args = [str(source), str(target), '--json', *(['--relative'] if relative else [])]
            first = json.loads(self.command(*args, family='link').stdout)
            self.assertEqual(first['status'], 'complete')
            self.assertTrue(target.is_symlink())
            self.assertEqual(target.resolve(), source.resolve())
            link_text = os.readlink(target)
            self.assertEqual(os.path.isabs(link_text), not relative)
            before = self.snapshot()
            again = json.loads(self.command(*args, family='link').stdout)
            self.assertEqual(again['status'], 'unchanged')
            self.assertEqual(os.readlink(target), link_text)
            self.assert_home_unchanged(before)
            rows = json.loads(self.command('list', '--json').stdout)['items']
            self.assertEqual(len(rows), number)
            self.assertTrue(all(Path(row['path']).read_bytes() == b'occupied target' for row in rows))
            self.assertEqual(source.read_bytes(), original)
            self.assertEqual((source.stat().st_mode, source.stat().st_mtime_ns),
                             (source_info.st_mode, source_info.st_mtime_ns))


if __name__ == '__main__': unittest.main()
