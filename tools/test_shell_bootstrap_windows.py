#!/usr/bin/env python3
"""Native Windows PowerShell checkout acquisition in disposable, offline roots."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'lib/dots'))
from bootstrap_snippet import snippet

LOCATE = ROOT / 'lib/dots/shell/bootstrap/locate.ps1'


@unittest.skipUnless(os.name == 'nt', 'requires native Windows process, mutex, ACL and rename semantics')
class WindowsBootstrap(unittest.TestCase):
    def setUp(self):
        engine = os.environ.get('DOTS_TEST_POWERSHELL') or 'powershell'
        self.ps = shutil.which(engine)
        self.git = shutil.which('git.exe')
        if not self.ps or not self.git:
            self.skipTest(engine + ' and Git for Windows are required')
        temporary = tempfile.TemporaryDirectory(prefix="dots bootstrap ü & ' ")
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        self.home = self.base / 'test home'
        self.home.mkdir()
        self.source = self.base / "local źródło & % literal"
        self.target = self.base / 'missing parent' / "destination 雪 & '"
        self.source.mkdir()
        self.env = {key: os.environ[key] for key in ('SYSTEMROOT', 'WINDIR', 'PATHEXT', 'COMSPEC') if key in os.environ}
        system32 = Path(self.env['SYSTEMROOT']) / 'System32'
        self.env.update(HOME=str(self.home), USERPROFILE=str(self.home), TMP=str(self.home), TEMP=str(self.home),
                        PATH=os.pathsep.join([str(Path(self.git).parent), str(system32)]),
                        APPDATA=str(self.home/'roaming'), LOCALAPPDATA=str(self.home/'local'),
                        XDG_CONFIG_HOME=str(self.home/'config'), XDG_CACHE_HOME=str(self.home/'cache'),
                        XDG_DATA_HOME=str(self.home/'data'), XDG_STATE_HOME=str(self.home/'state'),
                        GIT_CONFIG_GLOBAL='NUL', GIT_CONFIG_NOSYSTEM='1', GIT_TERMINAL_PROMPT='0',
                        DOTS_BOOTSTRAP_SOURCE=str(self.source), DOTS_BOOTSTRAP_REF='main',
                        DOTS_BOOTSTRAP_DIR=str(self.target))
        files = {'bin/dots.ps1': '# public launcher', 'lib/dots/shell/startup.bash': '# startup marker',
                 'shells/powershell/profile.ps1': "[IO.File]::WriteAllText((Join-Path $env:HOME 'loaded'), 'ready')"}
        for name, content in files.items():
            path = self.source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding='utf-8-sig')
        for args in (['init', '-b', 'main'], ['add', '.'],
                     ['-c', 'user.name=test', '-c', 'user.email=test@localhost', 'commit', '-m', 'fixture']):
            subprocess.run([self.git, '-C', str(self.source), *args], env=self.env, cwd=self.home,
                           capture_output=True, check=True, timeout=30)

    def command(self, script=LOCATE, mode='interactive'):
        return [self.ps, '-NoLogo', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
                '-File', str(script), mode, '-Utf8']

    def run_locator(self, *, mode='interactive', script=LOCATE, env=None, timeout=20):
        return subprocess.run(self.command(script, mode), env=self.env if env is None else env,
                              cwd=self.home, capture_output=True, timeout=timeout)

    def stages(self):
        return list(self.target.parent.glob('.' + self.target.name + '.bootstrap-*'))

    def test_concurrent_unicode_clone_utf8_journal_acl_and_warm_reuse(self):
        # Ambient prompts, helpers and repository context must not alter this clone.
        env = dict(self.env, GIT_DIR=str(self.home/'invalid gitdir'), GIT_ALLOW_PROTOCOL='https',
                   GIT_CONFIG_COUNT='1', GIT_CONFIG_KEY_0='protocol.file.allow', GIT_CONFIG_VALUE_0='never')
        with subprocess.Popen(self.command(), env=env, cwd=self.home, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as first:
            with subprocess.Popen(self.command(), env=env, cwd=self.home, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as second:
                for child in (first, second):
                    out, err = child.communicate(timeout=35)
                    self.assertEqual(out.decode('utf-8').strip(), str(self.target), err)
                    self.assertEqual(child.returncode, 0, err)
        self.assertEqual(len(self.stages()), 1)
        stage, = self.stages()
        self.assertEqual(json.loads((stage/'journal.json').read_bytes())['status'], 'committed')
        self.assertEqual(json.loads((stage/'journal.json').read_bytes())['destination'], str(self.target))
        self.assertFalse((stage/'checkout').exists())
        acl = subprocess.run([self.ps, '-NoProfile', '-NonInteractive', '-Command',
            "$a=Get-Acl -LiteralPath $env:STAGE; $sid=[Security.Principal.WindowsIdentity]::GetCurrent().User; "
            "$rules=@($a.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier])); "
            "if (-not $a.AreAccessRulesProtected -or $rules.Count -ne 1 -or $rules[0].IdentityReference -ne $sid) {exit 5}"],
            cwd=self.home, env=dict(self.env, STAGE=str(stage)), capture_output=True, timeout=15)
        self.assertEqual(acl.returncode, 0, acl.stderr)
        again = self.run_locator(mode='offline', env=dict(self.env, PATH=str(self.home)))
        self.assertEqual(again.stdout.decode('utf-8').strip(), str(self.target))
        self.assertEqual(len(self.stages()), 1)

    def test_generated_rc_offline_occupied_ref_and_credential_refusal(self):
        rc = self.home/'standalone.ps1'
        rc.write_text(snippet('powershell'), encoding='utf-8-sig')
        ps = [self.ps, '-NoLogo', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-File', str(rc)]
        offline = subprocess.run(ps, env=self.env, cwd=self.home, capture_output=True, timeout=15)
        self.assertEqual(offline.returncode, 0, offline.stderr)
        self.assertEqual(offline.stdout, b'')
        self.assertFalse(self.target.parent.exists())
        for key, value in [('DOTS_BOOTSTRAP_SOURCE', 'https://reader:secret-marker@localhost/dots.git'),
                           ('DOTS_BOOTSTRAP_SOURCE', 'https://localhost/dots?token=secret-marker'),
                           ('DOTS_BOOTSTRAP_SOURCE', 'D:relative'), ('DOTS_BOOTSTRAP_REF', '--bad')]:
            rejected = self.run_locator(env=dict(self.env, **{key: value}))
            self.assertFalse(rejected.stdout.strip())
            self.assertIn(b'dots bootstrap:', rejected.stderr)
            self.assertNotIn(b'secret-marker', rejected.stderr)
            self.assertFalse(self.target.parent.exists())
        failed = self.run_locator(env=dict(self.env, DOTS_BOOTSTRAP_REF='does-not-exist'))
        self.assertFalse(failed.stdout.strip())
        self.assertFalse(self.target.exists())
        self.assertEqual([json.loads((s/'journal.json').read_bytes())['status'] for s in self.stages()], ['failed'])
        self.target.mkdir()
        marker = self.target/'keep'; marker.write_bytes(b'original')
        occupied = self.run_locator()
        self.assertIn(b'occupied', occupied.stderr)
        self.assertEqual(marker.read_bytes(), b'original')
        self.assertEqual(len(self.stages()), 1)
        missing = self.run_locator(env=dict(self.env, PATH=str(self.home), DOTS_BOOTSTRAP_DIR=str(self.base/'missing-git')))
        self.assertIn(b'Install Git', missing.stderr)
        self.assertFalse((self.base/'missing-git').exists())
        # The rc sources an existing checkout with no helper or Git access.
        warm = subprocess.run(ps, cwd=self.home, env=dict(self.env, PATH=str(self.home),
                              DOTS_BOOTSTRAP_DIR=str(self.source)), capture_output=True, timeout=15)
        self.assertEqual(warm.returncode, 0, warm.stderr)
        self.assertEqual((self.home/'loaded').read_text(), 'ready')

    def test_installed_profile_prefers_explicit_executable_pin_and_conventional(self):
        conventional = self.home/'dots'
        pinned = self.base/'pinned checkout'
        cli = self.base/'on PATH'
        for root, label in ((conventional,'conventional'), (pinned,'pinned'), (cli,'executable')):
            shutil.copytree(self.source, root)
            (root/'shells/powershell/profile.ps1').write_text("Write-Output '" + label + "'\n")
        helpers = self.home/'.local/share/dots/bootstrap'
        helpers.mkdir(parents=True)
        (helpers/'checkout').write_text(str(pinned) + '\n', encoding='utf-8')
        env = self.env.copy()
        env.pop('DOTS_BOOTSTRAP_DIR', None)
        rc = self.home/'rc.ps1'
        shutil.copyfile(ROOT/'shells/bootstrap/profile.ps1', rc)
        for label, extra in (('pinned', {}), ('executable', dict(PATH=str(cli/'bin') + os.pathsep + env['PATH'])),
                             ('conventional', dict(PATH=str(cli/'bin') + os.pathsep + env['PATH'],
                                                   DOTS_BOOTSTRAP_DIR=str(conventional)))):
            result = subprocess.run([self.ps, '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-File', str(rc)],
                                    cwd=self.home, env=dict(env, **extra), capture_output=True, text=True, timeout=15)
            self.assertEqual(result.stdout.strip(), label, result.stderr)

    def test_clone_deadline_stops_process_tree(self):
        # Replace only the duration in the test copy so this case runs in seconds.
        csc = Path(self.env['SYSTEMROOT'])/'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
        if not csc.is_file():
            csc = Path(self.env['SYSTEMROOT'])/'Microsoft.NET/Framework/v4.0.30319/csc.exe'
        if not csc.is_file():
            self.skipTest('Windows .NET Framework compiler unavailable for the test-owned Git stand-in')
        script = self.home/'short-deadline.ps1'
        original = LOCATE.read_text(encoding='utf-8')
        self.assertEqual(original.count('-ge 90000'), 1)
        script.write_text(original.replace('-ge 90000', '-ge 4000'), encoding='utf-8-sig')
        cs = self.home/'standin.cs'
        cs.write_text('''
using System;
using System.Diagnostics;
using System.IO;
using System.Threading;
class Standin {
    static void Main(string[] args) {
        string root = Environment.GetEnvironmentVariable("FIXTURE_ROOT");
        if (args.Length == 1 && args[0] == "child") {
            using (File.Open(Path.Combine(root, "child.lock"), FileMode.Create, FileAccess.Write, FileShare.None)) {
                File.WriteAllText(Path.Combine(root, "child.started"), "yes");
                Thread.Sleep(60000);
            }
        } else {
            Process.Start(new ProcessStartInfo { FileName = Process.GetCurrentProcess().MainModule.FileName,
                Arguments = "child", UseShellExecute = false });
            Thread.Sleep(60000);
        }
    }
}
''', encoding='utf-8-sig')
        fake = self.home/'git.exe'
        subprocess.run([str(csc), '/nologo', '/out:' + str(fake), str(cs)], env=self.env,
                       cwd=self.home, capture_output=True, check=True, timeout=30)
        env = dict(self.env, PATH=str(self.home) + os.pathsep + self.env['PATH'], FIXTURE_ROOT=str(self.home))
        result = self.run_locator(script=script, env=env, timeout=18)
        self.assertIn(b'timed out', result.stderr)
        self.assertTrue((self.home/'child.started').is_file())
        # Win32 refuses this rename while the fixture child holds the exclusive file.
        deadline = time.monotonic() + 3
        while True:
            try:
                (self.home/'child.lock').rename(self.home/'released')
                break
            except PermissionError:
                if time.monotonic() >= deadline:
                    raise
                time.sleep(.05)
        self.assertFalse(self.target.exists())
        self.assertEqual([json.loads((s/'journal.json').read_bytes())['status'] for s in self.stages()], ['failed'])


if __name__ == '__main__':
    unittest.main()
