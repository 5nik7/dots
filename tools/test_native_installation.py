#!/usr/bin/env python3
"""Native Windows full-checkout wrappers; every destination is fixture-owned.

Run separately with DOTS_TEST_POWERSHELL=powershell and pwsh. The copied
discovery payload binds $PROFILE to owned paths; real KnownFolders discovery
and desktop activation are deliberately separate acceptance gates.
"""
import base64
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = os.environ.get('DOTS_TEST_POWERSHELL')
ENGINE = shutil.which(REQUIRED or 'pwsh')
if REQUIRED and not ENGINE:
    raise SystemExit('required PowerShell engine unavailable: ' + REQUIRED)


@unittest.skipUnless(os.name == 'nt', 'native Windows full-checkout wrappers')
class NativeInstallation(unittest.TestCase):
    def setUp(self):
        self.assertTrue(ENGINE, 'select an installed native PowerShell engine')
        self.engines = [shutil.which(name) for name in ('powershell', 'pwsh')]
        self.assertTrue(all(self.engines), 'both native PowerShell engines are required')
        self.go = shutil.which('go')
        self.git = shutil.which('git')
        self.assertTrue(self.go and self.git, 'preinstalled native Go and Git are required')
        self.tmp = tempfile.TemporaryDirectory(prefix='dots native full 雪 - ')
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name).resolve()
        self.repo = self.base/'checkout'
        self.home = self.base/'home'
        self.repo.mkdir()
        self.home.mkdir()
        # Start with a bounded environment, never ambient Dots/app/startup inputs.
        self.env = {k: os.environ[k] for k in ('SystemRoot', 'WINDIR', 'COMSPEC',
                    'OS', 'PROCESSOR_ARCHITECTURE') if k in os.environ}
        self.env.update(PATH=os.pathsep.join(dict.fromkeys(str(Path(p).parent) for p in
                        (sys.executable, self.go, self.git, *self.engines))),
            PATHEXT='.COM;.EXE;.BAT;.CMD', HOME=str(self.home), USERPROFILE=str(self.home),
            DOTS=str(self.repo), DOTS_COLOR='never', DOTS_ICONS='never', DOTS_PROGRESS='never',
            TERM='dumb', PYTHONDONTWRITEBYTECODE='1', PYTHONNOUSERSITE='1',
            PYTHONUTF8='1', PYTHONIOENCODING='utf-8', LANG='C.UTF-8',
            POWERSHELL_TELEMETRY_OPTOUT='1', POWERSHELL_UPDATECHECK='Off',
            DOTNET_MultiCoreJitNoProfileGather='1', PYTHON_MANAGER_AUTOMATIC_INSTALL='false',
            GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull, GIT_ALLOW_PROTOCOL='file',
            GIT_TERMINAL_PROMPT='0', GCM_INTERACTIVE='Never',
            GOENV='off', GOWORK='off', GOTOOLCHAIN='local', GOPROXY='off', GOSUMDB='off',
            GOVCS='*:off', CGO_ENABLED='0')
        for key, relative in {
            'APPDATA':'home/AppData/Roaming', 'LOCALAPPDATA':'home/AppData/Local',
            'XDG_CONFIG_HOME':'home/config', 'XDG_DATA_HOME':'home/data',
            'XDG_STATE_HOME':'home/state', 'XDG_CACHE_HOME':'home/cache',
            'XDG_RUNTIME_DIR':'runtime', 'TEMP':'tmp', 'TMP':'tmp', 'TMPDIR':'tmp',
            'CODEX_HOME':'home/codex', 'PI_CODING_AGENT_DIR':'home/pi',
            'PSModulePath':'runtime/modules', 'GIT_TEMPLATE_DIR':'runtime/git-template',
            'GOPATH':'build/go', 'GOCACHE':'build/cache', 'GOMODCACHE':'build/modules',
            'GOTMPDIR':'build/tmp', 'DOTS_TEST_PROFILE_ROOT':'redirected Documents 雪',
        }.items():
            path = self.base/relative
            path.mkdir(parents=True, exist_ok=True)
            self.env[key] = str(path)
        self.env['HOMEDRIVE'], self.env['HOMEPATH'] = os.path.splitdrive(str(self.home))
        self.env['PSModuleAnalysisCachePath'] = str(self.base/'runtime/module-analysis')
        hooks = self.base/'runtime/hooks'
        hooks.mkdir()
        self.env.update(GIT_CONFIG_COUNT='5', GIT_CONFIG_KEY_0='core.hooksPath',
            GIT_CONFIG_VALUE_0=str(hooks), GIT_CONFIG_KEY_1='commit.gpgsign', GIT_CONFIG_VALUE_1='false',
            GIT_CONFIG_KEY_2='tag.gpgsign', GIT_CONFIG_VALUE_2='false',
            GIT_CONFIG_KEY_3='gc.auto', GIT_CONFIG_VALUE_3='0',
            GIT_CONFIG_KEY_4='maintenance.auto', GIT_CONFIG_VALUE_4='false')
        self.copy_public_sources()
        # Bind both the launching engine and real child engines, without replacing
        # enumeration, ProcessStartInfo, timeout, encoding, version or JSON logic.
        self.binding = ('$fixtureFolder = if ($PSVersionTable.PSEdition -eq "Desktop") '
            '{ "WindowsPowerShell" } else { "PowerShell" }; '
            '$PROFILE.CurrentUserAllHosts = [IO.Path]::Combine('
            '$env:DOTS_TEST_PROFILE_ROOT, $fixtureFolder, "profile.ps1"); ')
        helper = self.repo/'lib/dots/files/powershell_profiles.ps1'
        original = helper.read_text(encoding='utf-8')
        needle = "$scriptText = '"
        self.assertEqual(original.count(needle), 1)
        helper.write_text(original.replace(needle, needle+self.binding), encoding='utf-8')
        self.original_profiles = {}
        for folder in ('WindowsPowerShell', 'PowerShell'):
            path = Path(self.env['DOTS_TEST_PROFILE_ROOT'])/folder/'profile.ps1'
            path.parent.mkdir()
            data = ('# Original owned '+folder+' profile; never execute\n').encode()
            path.write_bytes(data)
            self.original_profiles[str(path)] = data
        # One unambiguous owned consumer installation; no application is launched.
        (Path(self.env['LOCALAPPDATA'])/'Packages/Microsoft.WindowsTerminalPreview_8wekyb3d8bbwe/LocalState').mkdir(parents=True)
        self.original_sources = self.files(self.repo)
        probe = self.base/'link-capability'
        probe.symlink_to(self.repo/'install.ps1')
        probe.unlink()  # A missing privilege is a failed native prerequisite.

    def copy_public_sources(self):
        result = subprocess.run([self.git, '-C', str(ROOT), 'ls-files', '--stage', '-z'],
                                env=self.env, capture_output=True, check=True, timeout=30)
        links = []
        for row in result.stdout.split(b'\0'):
            if not row:
                continue
            info, name = row.split(b'\t', 1)
            mode, _, stage = info.decode().split()
            self.assertEqual(stage, '0', 'unmerged source index')
            if mode == '160000':
                continue  # Optional/private repositories are never copied.
            name = name.decode('utf-8')
            source, target = ROOT/name, self.repo/name
            target.parent.mkdir(parents=True, exist_ok=True)
            if mode == '120000':
                link = os.readlink(source) if source.is_symlink() else source.read_text(encoding='utf-8')
                if os.path.isabs(link) or PurePosixPath(link).is_absolute():
                    continue  # External platform-local compatibility links.
                self.assertTrue(Path(os.path.abspath(source.parent/link)).is_relative_to(ROOT), name)
                self.assertTrue((source.parent/link).resolve().is_relative_to(ROOT.resolve()), name)
                links.append((target, str(Path(link)), (source.parent/link).resolve().is_dir()))
            else:
                self.assertFalse(source.is_symlink(), name)
                self.assertTrue(source.resolve().is_relative_to(ROOT.resolve()), name)
                shutil.copy2(source, target)
        for target, link, directory in links:
            target.symlink_to(link, target_is_directory=directory)

    @staticmethod
    def files(root):
        return {str(p.relative_to(root)): ('link', os.readlink(p)) if p.is_symlink() else
                ('file', hashlib.sha256(p.read_bytes()).hexdigest())
                for p in root.rglob('*') if p.is_symlink() or p.is_file()}

    def invoke(self, text, engine=ENGINE, timeout=600):
        encoded = base64.b64encode(('[Console]::OutputEncoding = New-Object Text.UTF8Encoding($false); '
                                  + self.binding + text).encode('utf-16le')).decode()
        return subprocess.run([engine, '-NoLogo', '-NoProfile', '-NonInteractive', '-EncodedCommand', encoded],
            env=self.env, cwd=self.base, stdin=subprocess.DEVNULL, capture_output=True,
            text=True, encoding='utf-8', timeout=timeout)

    def wrapper(self, name, *args, ok=True):
        quote = lambda s: "'"+str(s).replace("'", "''")+"'"
        result = self.invoke('& '+quote(self.repo/name)+' '+' '.join(args)+'; exit $LASTEXITCODE')
        self.assertEqual(result.returncode == 0, ok, result.stderr+'\n'+result.stdout)
        self.assertNotIn('\x1b', result.stdout)
        doc = json.loads(result.stdout)
        for row in doc['items']:
            if row.get('target'):
                target = Path(row['target'])
                self.assertTrue(target.is_absolute() and target.is_relative_to(self.base)
                                and target.resolve().is_relative_to(self.base), row)
        return doc

    def home_snapshot(self):
        # PowerShell can create these exact native runtime files with -NoProfile.
        # Reuse the existing adapter fixture's narrow type/reparse-aware allowance.
        from test_installation_adapters import Adapters
        return Adapters.nonruntime_home_paths(self)

    def receipt(self):
        return json.loads((Path(self.env['XDG_STATE_HOME'])/'dots/installation.json').read_text())

    def test_default_install_repeat_drift_and_restore(self):
        for engine in self.engines:
            result = self.invoke('Import-Module Microsoft.PowerShell.Management,Microsoft.PowerShell.Utility; '
                                 '$PSVersionTable.PSVersion.ToString()', engine, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            print('Native engine:', engine, result.stdout.strip())
        before = self.home_snapshot()
        preview = self.wrapper('install.ps1', '-DryRun', '-Offline', '-Json')
        self.assertEqual(preview['platform'], 'windows')
        self.assertEqual(preview['status'], 'preview')
        self.assertEqual(set(preview['components']), {'core','files','themes','anodize','blastoff','pkgs'})
        profiles = {row['target'] for row in preview['items'] if row['id'] == 'dots:powershell-profile'}
        self.assertEqual({Path(p) for p in profiles}, {Path(p) for p in self.original_profiles})
        self.assertEqual(self.home_snapshot(), before)
        self.assertEqual(self.files(self.repo), self.original_sources)
        for path, data in self.original_profiles.items():
            self.assertEqual(Path(path).read_bytes(), data)
        telemetry = Path(self.env['APPDATA'])/'go/telemetry'
        telemetry.mkdir(parents=True)
        (telemetry/'mode').write_text('off\n', encoding='utf-8')
        installed = self.wrapper('install.ps1', '-Yes', '-Offline', '-Json')
        self.assertEqual(installed['status'], 'complete')
        first = self.receipt()
        for target in first['entries']:
            self.assertTrue(Path(target).is_relative_to(self.base)
                            and Path(target).resolve().is_relative_to(self.base), target)
        for path in self.original_profiles:
            self.assertTrue(Path(path).is_symlink(), path)
        binary = self.repo/'plugins/anodize/engine/.build/anodize-engine.exe'
        self.assertTrue(binary.is_file())
        self.assertEqual(binary.read_bytes()[:2], b'MZ')
        active = Path(self.env['XDG_STATE_HOME'])/'dots/current/theme'
        self.assertTrue(active.is_symlink())
        for template in (self.repo/'default/themed').glob('*.tpl'):
            self.assertTrue((active/template.name[:-4]).is_file(), template.name)
        for row in installed['items']:
            if row['id'].startswith('theme:') and row.get('target') and Path(row['target']).is_symlink():
                self.assertTrue(Path(row['target']).exists(), row)
        repeated = self.wrapper('install.ps1', '-Yes', '-Offline', '-Json')
        changes = [r for r in repeated['items'] if r['status'] not in ('unchanged', 'skipped')]
        self.assertEqual(repeated['status'], 'unchanged', json.dumps(changes, indent=2))
        self.assertEqual(self.receipt(), first)
        for app in ('blastoff', 'pkgs'):
            assets = [r for r in repeated['items'] if r['id'].startswith('dots:'+app+':')]
            self.assertIn('dots:'+app+':command', {r['id'] for r in assets})
            self.assertTrue(all(r['status'] == 'unchanged' for r in assets), assets)
        launcher = self.home/'.local/bin/dots.ps1'
        self.assertFalse(launcher.is_symlink())
        original = launcher.read_bytes()
        launcher.write_bytes(original+b'\n# Owned post-install drift\n')
        drift = self.wrapper('uninstall.ps1', '-DryRun', '-Json')
        self.assertEqual(drift['status'], 'preview')
        preserved = next(r for r in drift['items'] if r['id'] == 'dots:command')
        self.assertEqual(preserved['status'], 'preserved')
        self.assertEqual(preserved['reason'], 'target changed after installation')
        self.assertEqual(launcher.read_bytes(), original+b'\n# Owned post-install drift\n')
        self.assertEqual(self.receipt(), first)
        launcher.write_bytes(original)  # Restore only this test's injected drift.
        self.wrapper('uninstall.ps1', '-Yes', '-Json')
        self.assertFalse(self.receipt()['entries'])
        for path, data in self.original_profiles.items():
            self.assertFalse(Path(path).is_symlink(), path)
            self.assertEqual(Path(path).read_bytes(), data)
        self.assertFalse(launcher.exists())
        self.assertFalse(active.exists())
        self.assertFalse(binary.exists())
        self.assertEqual(self.files(self.repo), self.original_sources)
        for name in ('config/nvim', 'secrets', 'shells/powershell/Modules/catppuccin',
                     'profiles/windows/rainmeter/5ui7e'):
            self.assertFalse((self.repo/name/'.git').exists())


if __name__ == '__main__':
    unittest.main()
