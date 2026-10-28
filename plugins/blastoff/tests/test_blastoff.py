"""Offline contract and data-loss regression tests. All writes use temp roots."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest

ROOT = Path(__file__).resolve().parent.parent
CORE = ROOT/'lib/blastoff.py'
spec = importlib.util.spec_from_file_location('core', CORE)
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)

class Harness(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name)
        self.store = self.home/'store'
        self.config = self.home/'config/starship.toml'
        self.env = dict(os.environ, HOME=str(self.home), USERPROFILE=str(self.home), BLASTOFF_HOME=str(self.store), STARSHIP_CONFIG=str(self.config), NO_COLOR='1', PYTHONPATH='', BLASTOFF_PYTHON=sys.executable)
        self.env.update(XDG_CONFIG_HOME=str(self.home/'xdg-config'),
                        XDG_STATE_HOME=str(self.home/'state'), XDG_CACHE_HOME=str(self.home/'cache'),
                        XDG_DATA_HOME=str(self.home/'data'), APPDATA=str(self.home/'Roaming'),
                        LOCALAPPDATA=str(self.home/'Local'), DOTS_COLOR='auto', DOTS_ICONS='never',
                        DOTS_MENU_CAPTURE='')
        self.env['PATH'] = '' # Prove local operations never require Starship.
    def tearDown(self):
        self.temp.cleanup()
    def invoke(self, *args, code=0, entry=None):
        proc = subprocess.run([sys.executable, '-I', str(entry or CORE), *args], env=self.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
        self.assertEqual(proc.returncode, code, proc.stderr)
        return proc
    def write(self, p, content):
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
        return p
    def theme(self, n='purple', content='[directory]\nstyle = "purple"\n'):
        return self.write(self.store/'themes'/(n+'.toml'), content)
    def snapshots(self):
        return sorted((self.store/'backups').glob('*.toml'))
class Contract(Harness):
    def test_read_only_missing_dependencies(self):
        for args in [('--help',),('--version',),('--list',),('current',),('doctor','--json'),('module','list'),('backup','list'),('completion','bash')]:
            self.invoke(*args)
        self.assertFalse(self.store.exists())
        self.assertFalse(self.config.parent.exists())
    def test_list_never_changes_theme_or_generates_presets(self):
        p = self.theme()
        before = p.read_bytes()
        result = json.loads(self.invoke('--list','--json').stdout)
        self.assertEqual(result['themes'], ['purple'])
        self.assertEqual(p.read_bytes(), before)
        self.assertEqual(list(p.parent.iterdir()), [p])
    def test_new_custom_config_path_honored(self):
        self.theme()
        self.invoke('--theme','purple')
        self.assertTrue(self.config.is_file())
        self.assertFalse((self.home/'.config/starship.toml').exists())
    def test_apply_backup_and_noop(self):
        old = '[character]\nsuccess_symbol = "OLD"\n'
        self.write(self.config, old)
        self.theme()
        self.invoke('theme','apply','purple')
        self.assertEqual(self.snapshots()[0].read_text(), old)
        self.invoke('theme','apply','purple')
        self.assertEqual(len(self.snapshots()), 1)
    def test_invalid_theme_leaves_config_and_backups_unchanged(self):
        self.write(self.config, 'format = "$all"\n')
        self.theme(content='[bad\n')
        self.invoke('-t','purple', code=1)
        self.assertEqual(self.config.read_text(), 'format = "$all"\n')
        self.assertFalse((self.store/'backups').exists())
    def test_save_copy_delete_and_recover(self):
        self.write(self.config, '[directory]\nstyle = "red"\n')
        self.invoke('theme','save','work')
        self.invoke('theme','copy','work','copy')
        self.invoke('theme','delete','copy', code=2)
        self.invoke('theme','delete','copy','--force')
        snapshot = self.snapshots()[0]
        self.invoke('theme','import',str(snapshot),'recovered')
        self.assertEqual((self.store/'themes/work.toml').read_bytes(), (self.store/'themes/recovered.toml').read_bytes())
    def test_collision_and_force_backup(self):
        self.theme('work', '[directory]\nstyle="old"\n')
        self.write(self.config, '[directory]\nstyle="new"\n')
        self.invoke('theme','save','work', code=1)
        self.invoke('theme','save','work','--force')
        self.assertIn('old', self.snapshots()[0].read_text())
    def test_path_traversal_and_device_names(self):
        for bad in ['../escape','a/b','C:foo','CON','lpt1','--oops','space name']:
            self.invoke('theme','save',bad, code=2)
        self.assertFalse(self.store.exists())
    @unittest.skipIf(os.name=='nt', 'symlink privilege not guaranteed on Windows')
    def test_symlink_config_explicit_replace_preserves_target(self):
        target = self.theme()
        old = target.read_bytes()
        self.config.parent.mkdir()
        self.config.symlink_to(target)
        self.theme('new', '[directory]\nstyle="new"\n')
        self.invoke('-t','new', code=1)
        self.assertTrue(self.config.is_symlink())
        self.invoke('-t','new','--replace-link')
        self.assertFalse(self.config.is_symlink())
        self.assertEqual(target.read_bytes(), old)
        metadata = json.loads(next((self.store/'backups').glob('*.json')).read_text())
        self.assertEqual(metadata['symlink_target'], str(target))
    @unittest.skipIf(os.name=='nt', 'symlink privilege not guaranteed on Windows')
    def test_delete_active_symlink_target_refused(self):
        target = self.theme()
        self.config.parent.mkdir()
        self.config.symlink_to(target)
        self.invoke('theme','delete','purple','--force', code=1)
        self.assertTrue(target.exists())
    @unittest.skipIf(os.name=='nt', 'FIFO is POSIX only')
    def test_fifo_input_fails_without_hanging(self):
        self.store.mkdir()
        os.mkfifo(self.store/'pipe.toml')
        self.invoke('theme','import',str(self.store/'pipe.toml'),'bad', code=1)
    @unittest.skipIf(os.name=='nt', 'symlink privilege not guaranteed on Windows')
    def test_storage_root_link_preserved(self):
        destination = self.home/'outside'; destination.mkdir()
        self.store.symlink_to(destination, target_is_directory=True)
        self.write(self.config, '[directory]\nstyle="red"\n')
        self.invoke('theme','save','linked')
        self.assertEqual((destination/'themes/linked.toml').read_bytes(), self.config.read_bytes())
        self.write(self.config, '[directory]\nstyle="old"\n')
        self.invoke('theme','apply','linked')
        self.assertEqual(self.config.read_bytes(), (destination/'themes/linked.toml').read_bytes())
        self.assertIn('old', self.snapshots()[0].read_text())
        self.assertTrue(self.store.is_symlink())
        self.assertEqual(self.store.resolve(), destination)
    @unittest.skipIf(os.name=='nt', 'symlink privilege not guaranteed on Windows')
    def test_delete_refuses_symlinked_storage_children(self):
        self.store.mkdir()
        for command, directory in [('theme','themes'), ('module','modules')]:
            with self.subTest(command=command):
                outside = self.home/('outside-'+directory)
                victim = self.write(outside/'victim.toml', '[directory]\nstyle="keep"\n')
                (self.store/directory).symlink_to(outside, target_is_directory=True)
                self.invoke(command,'delete','victim','--force', code=1)
                self.assertEqual(victim.read_text(), '[directory]\nstyle="keep"\n')
                self.assertFalse((self.store/'backups').exists())

    def test_module_load_detects_edits_during_merge(self):
        from unittest.mock import patch
        self.write(self.store/'modules/new.toml', '[directory]\nstyle="new"\n')
        merge = core.merge_module
        for existed in (False, True):
            with self.subTest(existed=existed):
                if existed:
                    self.write(self.config, 'format="$all"\n[directory]\nstyle="old"\n')
                outside = 'format="$git_branch"\n[directory]\nstyle="external"\n'
                def edit_during_merge(active, snippet):
                    self.write(self.config, outside)
                    return merge(active, snippet)
                with patch.dict(os.environ, self.env, clear=True), patch.object(core, 'merge_module', side_effect=edit_during_merge):
                    with self.assertRaises(core.Failure):
                        core.run(['module','load','new'])
                self.assertEqual(self.config.read_text(), outside)
                self.assertFalse((self.store/'backups').exists())
                self.config.unlink()

    def test_backup_restore_checksum_and_preserve_current(self):
        old = 'format = "$all"\n'
        self.write(self.config, old)
        ident = json.loads(self.invoke('backup','create','--json').stdout)['backup']
        self.write(self.config, 'format = "$directory"\n')
        self.invoke('backup','restore',ident)
        self.assertEqual(self.config.read_text(), old)
        self.assertEqual(len(self.snapshots()), 2)
        (self.store/'backups'/(ident+'.toml')).write_text('tampered=true\n')
        self.invoke('backup','restore',ident, code=1)
        self.assertEqual(self.config.read_text(), old)
    def test_stale_lock_never_broken(self):
        self.theme()
        (self.store/'.operation.lock').mkdir()
        self.invoke('-t','purple', code=1)
        self.assertFalse(self.config.exists())
        self.assertTrue((self.store/'.operation.lock').exists())
    def test_json_errors_are_parseable(self):
        p = self.invoke('--json','theme','apply', code=2)
        self.assertEqual(json.loads(p.stderr)['code'], 2)
        self.assertEqual(p.stdout, '')
    def test_no_color_and_pipeline_clean(self):
        self.theme()
        result = self.invoke('--list','--color','always')
        self.assertIn('\x1b', result.stdout)
        self.assertNotIn('\x1b', self.invoke('--list','--color','auto').stdout)
        del self.env['NO_COLOR']
        self.assertNotIn('\x1b', self.invoke('--list').stdout)
        self.assertIn('\x1b', self.invoke('--list','--color=always').stdout)
    def test_module_save_load_preserves_unrelated_values_and_text(self):
        original = '# root\nformat = "$all"\n\n[directory]\nstyle = "old"\n[directory.substitutions]\n"long name" = "short"\n\n[git_branch]\n# keep this exact comment\nstyle = "green"\n'
        self.write(self.config, original)
        self.invoke('module','save','directory','compact')
        self.write(self.config, original.replace('style = "old"', 'style = "changed"'))
        self.invoke('module','load','compact')
        current = self.config.read_text()
        self.assertEqual(tomllib.loads(current), tomllib.loads(original))
        self.assertIn('[git_branch]\n# keep this exact comment\nstyle = "green"\n', current)
        self.assertEqual(len(self.snapshots()), 1)
    def test_custom_module_and_missing_active_config(self):
        self.write(self.config, '[custom.clock]\ncommand="date"\nwhen="true"\n[custom.other]\ncommand="echo hi"\n')
        self.invoke('module','save','custom.clock','clock')
        self.config.unlink()
        self.invoke('module','load','clock')
        self.assertEqual(tomllib.loads(self.config.read_text()), {'custom':{'clock':{'command':'date','when':'true'}}})
    def test_module_handles_multiline_strings_arrays_and_quoted_headers(self):
        original = 'format="""\n[fake.table]\n$all\n"""\n\n["directory"]\nstyle="purple"\n[git_branch]\nformat="""\n[directory.fake]\n"""\n'
        self.write(self.config, original)
        self.invoke('module','save','directory','sample')
        self.invoke('module','load','sample')
        self.assertEqual(tomllib.loads(self.config.read_text()), tomllib.loads(original))
        snippet = b'[directory]\nthings = [\n [1, 2],\n [3, 4]\n]\n'
        self.assertEqual(core.extract_module(snippet, ('directory',)), snippet)
    def test_inline_module_refused_without_change(self):
        original = 'directory = {style="old"}\n'
        self.write(self.config, original)
        self.invoke('module','save','directory', code=1)
        self.write(self.store/'modules/new.toml', '[directory]\nstyle="new"\n')
        self.invoke('module','load','new', code=1)
        self.assertEqual(self.config.read_text(), original)
        self.assertFalse((self.store/'backups').exists())
    def test_stored_module_cannot_change_unrelated_root(self):
        self.write(self.config, '[directory]\nstyle="old"\n')
        self.write(self.store/'modules/bad.toml', 'format="changed"\n[directory]\nstyle="new"\n')
        self.invoke('module','load','bad', code=1)
        self.assertIn('old', self.config.read_text())
    def test_migrate_collision_preflight_and_preserve_sources(self):
        source = self.home/'legacy'
        self.write(source/'one.toml', '[directory]\nstyle="one"\n')
        self.write(source/'two.toml', '[directory]\nstyle="two"\n')
        self.invoke('migrate',str(source))
        self.assertTrue((source/'one.toml').exists())
        self.assertFalse(self.config.exists())
        self.invoke('migrate',str(source), code=1)
    @unittest.skipIf(os.name=='nt', 'POSIX modes only')
    def test_permissions_under_restrictive_umask(self):
        self.theme()
        previous = os.umask(0o077)
        try:
            self.invoke('-t','purple')
        finally:
            os.umask(previous)
        self.assertEqual(self.config.stat().st_mode & 0o777, 0o600)
    def test_apply_preserves_existing_file_mode(self):
        if os.name=='nt': self.skipTest('POSIX modes only')
        self.write(self.config, 'old=true\n'); self.config.chmod(0o640)
        self.theme(); self.invoke('-t','purple')
        self.assertEqual(self.config.stat().st_mode & 0o777, 0o640)
    def test_staging_detects_external_edit(self):
        self.write(self.config, 'old=true\n')
        before = core.fingerprint(self.config)
        self.config.write_text('outside=true\n')
        with self.assertRaises(core.Failure):
            core.atomic(self.config, b'new=true\n', before)
        self.assertEqual(self.config.read_text(), 'outside=true\n')
        self.assertEqual(list(self.config.parent.iterdir()), [self.config])
    def test_atomic_replace_failure_leaves_original(self):
        from unittest.mock import patch
        self.write(self.config, 'old=true\n')
        before = core.fingerprint(self.config)
        with patch.object(core.os, 'replace', side_effect=OSError('injected failure')):
            with self.assertRaises(OSError):
                core.atomic(self.config, b'new=true\n', before)
        self.assertEqual(self.config.read_text(), 'old=true\n')
        self.assertEqual(list(self.config.parent.iterdir()), [self.config])
    def test_picker_noninteractive_refused(self):
        self.invoke('pick', code=2)
        self.assertFalse(self.store.exists())
    @unittest.skipIf(os.name=='nt', 'POSIX executable fixture')
    def test_presets_dont_hide_colliding_local_theme(self):
        fakebin = self.home/'fakebin'; fakebin.mkdir()
        fake = fakebin/'starship'
        fake.write_text('#!'+sys.executable+'\nimport sys\nif sys.argv[1:] == ["preset","--list"]: print("same\\nother")\nelif sys.argv[1:] == ["preset","same"]: print("[directory]\\nstyle=\\\"preset\\\"")\nelse: sys.exit(1)\n')
        fake.chmod(0o755); self.env['PATH'] = str(fakebin)
        self.theme('same', '[directory]\nstyle="local"\n')
        listing = json.loads(self.invoke('--list','--json').stdout)
        self.assertEqual(listing['themes'], ['same'])
        self.assertEqual(listing['presets'], ['other','same'])
        self.invoke('-t','same'); self.assertIn('local', self.config.read_text())
        self.invoke('-t','preset:same'); self.assertIn('preset', self.config.read_text())
        self.assertEqual((self.store/'themes/same.toml').read_text(), '[directory]\nstyle="local"\n')
    def test_version_consistency(self):
        self.assertEqual((ROOT/'VERSION').read_text().strip(), core.VERSION)
        self.assertIn("ModuleVersion = '"+core.VERSION+"'", (ROOT/'powershell/blastoff.psd1').read_text())
        # Root help is rendered from the same live grammar, not a stale cache.
        self.assertEqual(self.invoke('-h').stdout, self.invoke('--help').stdout)
        self.assertIn('--replace-link', self.invoke('--help').stdout)
    @unittest.skipUnless(os.name == 'posix' and shutil.which('bash'), 'Native POSIX Bash required')
    def test_bash_entry_point_matches_core(self):
        for args in [('--help',),('--version',),('--list','--json'),('theme','apply','missing','--json')]:
            baseline = subprocess.run([sys.executable,'-I',str(CORE),*args],env=self.env,capture_output=True,timeout=5)
            actual = subprocess.run([shutil.which('bash'),str(ROOT/'bin/blastoff'),*args],env=self.env,capture_output=True,timeout=5)
            self.assertEqual((actual.returncode,actual.stdout,actual.stderr),(baseline.returncode,baseline.stdout,baseline.stderr))
    @unittest.skipUnless(os.name == 'posix' and shutil.which('bash'), 'Native POSIX Bash required')
    def test_bash_completion_reads_names_without_runtime(self):
        self.theme('purple')
        script = 'source "$1"; COMP_WORDS=(blastoff theme apply p); COMP_CWORD=3; _blastoff; printf "%s\\n" "${COMPREPLY[@]}"'
        result = subprocess.run([shutil.which('bash'),'-c',script,'completion',str(ROOT/'completions/blastoff.bash')],env=self.env,capture_output=True,text=True,timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(set(result.stdout.splitlines()), {'purple', 'preset:'})
    def test_header_marker_name_is_not_confused_with_the_marker(self):
        snippet = b'[__blastoff_header_marker__]\nstyle="purple"\n'
        self.assertEqual(core.snippet_route(snippet), ('__blastoff_header_marker__',))
        self.assertEqual(core.extract_module(snippet, ('__blastoff_header_marker__',)), snippet)

class Lifecycle(Harness):
    def setUp(self):
        super().setUp()
        self.env['PATH'] = os.environ.get('PATH', '')
    def test_install_dry_run_install_uninstall_and_tamper(self):
        prefix = self.home/'prefix with spaces'
        script = ROOT/'scripts/install.py'
        self.invoke('install','--prefix',str(prefix),'--dry-run', entry=script)
        self.assertFalse(prefix.exists())
        self.invoke('install','--prefix',str(prefix), code=2, entry=script)
        self.invoke('install','--prefix',str(prefix),'--yes', entry=script)
        manifest = prefix/'share/blastoff/install.json'
        doc = json.loads(manifest.read_text())
        self.assertTrue((prefix/'share/blastoff/versions'/core.VERSION/'lib/blastoff.py').exists())
        if os.name == 'posix' and shutil.which('bash'):
            result = subprocess.run([str(prefix/'bin/blastoff'),'--version'],env=self.env,capture_output=True,text=True,timeout=5)
            self.assertEqual((result.returncode,result.stdout),(0,'blastoff '+core.VERSION+'\n'))
        owned = prefix/'completely-unrelated'; owned.write_text('keep me')
        exe = prefix/'share/blastoff/versions'/core.VERSION/'lib/blastoff.py'
        original = exe.read_bytes(); exe.write_bytes(original+b'# user edit\n')
        self.invoke('uninstall','--prefix',str(prefix),'--yes', code=1, entry=script)
        self.assertTrue(manifest.exists())
        exe.write_bytes(original)
        self.invoke('uninstall','--prefix',str(prefix),'--yes', entry=script)
        self.assertEqual(owned.read_text(), 'keep me')
        self.assertFalse(manifest.exists())
        self.assertTrue(all(not Path(p).exists() for p in doc['files']))
    def test_install_refuses_unowned_destination(self):
        prefix = self.home/'prefix'
        # This destination is installed on every host, even Windows without Bash.
        original = self.write(prefix/'share/man/man1/blastoff.1', 'do not overwrite\n')
        self.invoke('install','--prefix',str(prefix),'--yes', code=1, entry=ROOT/'scripts/install.py')
        self.assertEqual(original.read_text(), 'do not overwrite\n')
    def test_install_refuses_corrupt_source_before_writes(self):
        source = self.home/'copied source'
        shutil.copytree(ROOT, source, ignore=shutil.ignore_patterns('.git','__pycache__'))
        (source/'man/blastoff.1').write_text('tampered source\n')
        prefix = self.home/'not-installed'
        self.invoke('install','--prefix',str(prefix),'--yes',code=1,entry=source/'scripts/install.py')
        self.assertFalse(prefix.exists())

if __name__ == '__main__':
    unittest.main()
