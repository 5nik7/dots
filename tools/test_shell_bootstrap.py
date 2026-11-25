#!/usr/bin/env python3
"""Exercise the emitted startup code using disposable homes and a local Git source."""
import json
import os
from pathlib import Path
import select
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'lib/dots'))
from bootstrap_snippet import installed_nu_entry, snippet


@unittest.skipIf(os.name == 'nt', 'POSIX PTY and shell bootstrap fixtures')
class ShellBootstrap(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="dots bootstrap ü ' ")
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.home = self.base/'home'
        self.home.mkdir()
        self.src = self.base/'local source'
        system = str(Path(shutil.which('git')).resolve().parent)
        self.env = dict(PATH=system, HOME=str(self.home), TERM='xterm', LC_ALL='C.UTF-8',
                        DOTS_BOOTSTRAP_SOURCE=str(self.src), GIT_ALLOW_PROTOCOL='file',
                        GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM='1',
                        XDG_CONFIG_HOME=str(self.home/'config'), XDG_CACHE_HOME=str(self.home/'cache'),
                        XDG_DATA_HOME=str(self.home/'data'), XDG_STATE_HOME=str(self.home/'state'))
        for name, content in {
            'bin/dots':'#!/bin/sh\nexit 1\n','bin/dots.ps1':'# fixture\n',
            'lib/dots/shell/startup.bash':'# fixture\n',
            'shells/bash/init.bash':'export LOADED=from_bash\n',
            'shells/zsh/init.zsh':'export LOADED=from_zsh\n',
            'shells/fish/init.fish':'set -gx LOADED from_fish\n',
            'shells/xonsh/init.xsh':"$LOADED = 'from_xonsh'\n",
            'shells/nushell/init.nu':"$env.LOADED = 'from_nu'\ndef first-use [] { print 'NUSHELL_VERIFIED' }\n",
        }.items():
            path=self.src/name
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(content)
        (self.src/'bin/dots').chmod(0o755)
        for args in (['init','-b','main'],['add','.'],['-c','user.name=test','-c','user.email=test@localhost','commit','-m','fixture']):
            subprocess.run(['git','-C',str(self.src),*args],env=self.env,capture_output=True,check=True)

    def test_emitted_bash_zsh_fish_offline_and_interactive(self):
        for shell,args in (('bash',['--noprofile','--norc']), ('zsh',['-df']), ('fish',['--no-config'])):
            if not shutil.which(shell):
                continue
            with self.subTest(shell=shell):
                rc = self.base/('rc.'+shell)
                rc.write_text(snippet(shell))
                dest = self.base/('checkout '+shell)
                env = dict(self.env,DOTS_BOOTSTRAP_DIR=str(dest),RC=str(rc))
                for flags, expected in ((['-c'],''),(['-ic'],'from_'+shell)):
                    result=subprocess.run([shell,*args,*flags,'source "$RC"; echo "$LOADED"'],
                                          env=env,cwd=self.home,capture_output=True,text=True,timeout=15)
                    self.assertEqual(result.stdout.strip(),expected,result.stderr)
                    self.assertEqual(dest.exists(), bool(expected))

    def test_checkout_precedence_with_multiple_valid_roots(self):
        pinned = self.base/'pinned checkout'
        conventional = self.home/'dots'
        cli = self.base/'installed CLI'
        for source in (pinned, conventional, cli):
            shutil.copytree(self.src, source)
        helper = self.home/'.local/share/dots/bootstrap'
        helper.mkdir(parents=True)
        (helper/'checkout').write_text(str(pinned) + '\n')
        for shell, flags, extension, check in (
                ('bash', ['--noprofile', '--norc'], 'bash/init.bash', 'printf "%s" "$LOADED"'),
                ('zsh', ['-df'], 'zsh/init.zsh', 'printf "%s" "$LOADED"'),
                ('fish', ['--no-config'], 'fish/init.fish', 'printf "%s" "$LOADED"'),
                ('xonsh', ['--no-rc'], 'xonsh/init.xsh', 'print($LOADED)')):
            if not shutil.which(shell):
                continue
            for root, name in ((pinned,'pinned'),(conventional,'conventional'),(cli,'installed')):
                entry = root/'shells'/extension
                entry.write_text(entry.read_text().replace('from_'+shell, name))
            rc = self.base / ('rc.xsh' if shell == 'xonsh' else 'rc.' + shell)
            rc.write_text(snippet(shell))
            for expected, extra in (
                    ('pinned', {}),
                    ('installed', dict(PATH=str(cli/'bin') + os.pathsep + self.env['PATH'])),
                    ('conventional', dict(PATH=str(cli/'bin') + os.pathsep + self.env['PATH'],
                                          DOTS_BOOTSTRAP_DIR=str(conventional)))):
                with self.subTest(shell=shell, selected=expected):
                    code = 'source ' + json.dumps(str(rc), ensure_ascii=False) + '\n' + check
                    result = subprocess.run([shutil.which(shell), *flags, '-c', code], cwd=self.home, env=dict(self.env, **extra),
                                            capture_output=True, text=True, timeout=15)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(result.stdout.strip(), expected, result.stderr)
            # A pin can remain after only this shell's startup files went away.
            # The other checkout still supplies this shell without any acquisition.
            (pinned/'shells'/extension).unlink()
            code = 'source ' + json.dumps(str(rc), ensure_ascii=False) + '\n' + check
            stale = subprocess.run([shutil.which(shell), *flags, '-c', code], cwd=self.home, env=self.env,
                                   capture_output=True, text=True, timeout=15)
            self.assertEqual(stale.stdout.strip(), 'conventional', stale.stderr)

    @unittest.skipUnless(shutil.which('xonsh'), 'Xonsh unavailable')
    def test_xonsh_standalone_bootstrap(self):
        entry = self.base/'standalone.xsh'
        entry.write_text(snippet('xonsh'))
        dest = self.base/'explicit xonsh'
        env = dict(self.env, RC=str(entry), DOTS_BOOTSTRAP_DIR=str(dest),
                   XONSH_DATA_DIR=str(self.home/'data'), XONSH_CACHE_DIR=str(self.home/'cache'),
                   XONTRIBS_AUTOLOAD_DISABLED='*')
        result = subprocess.run([shutil.which('xonsh'), '--no-rc', '-c',
            "__xonsh__.env['XONSH_INTERACTIVE'] = True\nsource @($RC)\nprint($LOADED)"],
            env=env, cwd=self.home, capture_output=True, text=True, timeout=15)
        self.assertEqual(result.stdout.strip(), 'from_xonsh', result.stderr)

    def test_acquisition_with_concurrent_clients_and_missing_git(self):
        helper = str(ROOT/'lib/dots/shell/bootstrap/locate.sh')
        no_git = subprocess.run([shutil.which('sh'), helper, 'interactive'],
            env=dict(self.env, PATH=str(self.base/'empty')), capture_output=True, text=True)
        self.assertIn('Install Git', no_git.stderr)
        self.assertFalse((self.home/'dots').exists())
        processes = [subprocess.Popen(['sh', helper, 'interactive'], env=self.env,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for _ in range(2)]
        for process in processes:
            out, err = process.communicate(timeout=15)
            self.assertEqual(process.returncode, 0, err)
            self.assertEqual(Path(out.strip()), self.home/'dots')
        statuses = [json.loads(p.read_text())['status'] for p in self.home.glob('.dots.bootstrap-*/journal.json')]
        self.assertEqual(statuses.count('committed'), 1)

    @unittest.skipUnless(shutil.which('nu'),'Nushell unavailable')
    def test_nushell_first_prompt_can_use_newly_cloned_definitions(self):
        entry=self.base/'config.nu'
        entry.write_text(snippet('nu'))
        self.check_nu_pty(entry)
        self.check_nu_pty(entry)  # now the normal checkout exists at parse time

    @unittest.skipUnless(shutil.which('nu'), 'Nushell unavailable')
    def test_installed_nu_relocated_pin_and_reacquisition(self):
        relocated = self.base / "moved ü '# dots"
        shutil.copytree(self.src, relocated)
        templates = relocated/'lib/dots/shell/bootstrap'
        templates.mkdir(parents=True)
        shutil.copyfile(ROOT/'lib/dots/shell/bootstrap/entry.nu', templates/'entry.nu')
        data = self.home/'.local/share/dots/bootstrap'
        data.mkdir(parents=True)
        (data/'entry.nu').write_text(installed_nu_entry(relocated))
        shutil.copyfile(ROOT/'lib/dots/shell/bootstrap/locate.sh', data/'locate.sh')
        entry = self.base/'installed.nu'
        shutil.copyfile(ROOT/'shells/bootstrap/config.nu', entry)
        # An explicit noninteractive source resolves a pinned non-default path.
        code = 'source ' + json.dumps(str(entry), ensure_ascii=False) + '; print $env.LOADED'
        offline = subprocess.run(['nu', '--no-config-file', '-c', code], cwd=self.home,
                                 env=self.env, capture_output=True, text=True, timeout=10)
        self.assertEqual(offline.stdout.strip(), 'from_nu', offline.stderr)
        other = subprocess.run(['nu', '--no-config-file', '-c',
                                'source ' + json.dumps(str(entry), ensure_ascii=False) + "; print ($env.LOADED? | default 'absent')"],
                               cwd=self.home, env=dict(self.env, DOTS_BOOTSTRAP_DIR=str(self.src)),
                               capture_output=True, text=True, timeout=10)
        self.assertEqual(other.stdout.strip(), 'absent', other.stderr)
        self.check_nu_pty(entry)
        self.assertFalse((self.home/'dots').exists())
        conventional = self.home/'dots'
        shutil.copytree(self.src, conventional)
        (conventional/'shells/nushell/init.nu').write_text("$env.LOADED = 'conventional'\n")
        preferred = subprocess.run(['nu', '--no-config-file', '-c', code], cwd=self.home,
                                   env=self.env, capture_output=True, text=True, timeout=10)
        self.assertEqual(preferred.stdout.strip(), 'from_nu', preferred.stderr)
        self.check_nu_pty(entry)
        installed = self.base/'installed Nu CLI'
        shutil.copytree(self.src, installed)
        (installed/'shells/nushell/init.nu').write_text("def first-use [] { print 'NU_CLI_VERIFIED' }\n")
        env = dict(self.env, PATH=str(installed/'bin') + os.pathsep + self.env['PATH'])
        self.check_nu_pty(entry, env, b'NU_CLI_VERIFIED')
        self.check_nu_pty(entry, dict(env, DOTS_BOOTSTRAP_DIR=str(relocated)))
        conventional.rename(self.base/'retired conventional checkout')
        relocated.rename(self.base/'retired checkout')
        self.check_nu_pty(entry)
        self.assertTrue((self.home/'dots/bin/dots').is_file())

    def check_nu_pty(self, entry, env=None, marker=b'NUSHELL_VERIFIED'):
        import pty
        pid,fd=pty.fork()
        if pid==0:
            os.chdir(self.home)
            os.execvpe('nu',['nu','--env-config',os.devnull,'--config',str(entry),'--no-history'],env or self.env)
        data=b''
        try:
            deadline=time.monotonic()+12
            sent=False
            while time.monotonic()<deadline:
                if not select.select([fd],[],[],0.15)[0]:continue
                try:chunk=os.read(fd,65536)
                except OSError:break
                data+=chunk
                if b'\x1b[6n' in chunk:os.write(fd,b'\x1b[1;1R')
                if not sent and b'\x1b]133;B' in data:
                    os.write(fd,b'first-use\r')
                    sent=True
                if marker in data:break
            self.assertIn(marker,data,repr(data[-1800:]))
        finally:
            os.close(fd)
            os.waitpid(pid,0)

    def test_interrupted_first_clone_leaves_destination_absent_and_can_retry(self):
        commands = self.base/'guarded commands'
        commands.mkdir()
        git = commands/'git'
        marker = self.base/'git-started'
        git.write_text('#!/bin/sh\n: > "$STARTED"\nexec sleep 30\n')
        git.chmod(0o755)
        python = commands/'python3'
        python.write_text('#!/bin/sh\n: > "$PYTHON_CALLED"\nexit 5\n')
        python.chmod(0o755)
        env = dict(self.env, PATH=str(commands)+os.pathsep+self.env['PATH'],
                   STARTED=str(marker), PYTHON_CALLED=str(self.base/'unexpected-python'))
        helper = ['sh', str(ROOT/'lib/dots/shell/bootstrap/locate.sh'), 'interactive']
        process = subprocess.Popen(helper, cwd=self.home, env=env, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, start_new_session=True)
        try:
            deadline = time.monotonic()+5
            while not marker.exists() and time.monotonic()<deadline:
                time.sleep(0.03)
            self.assertTrue(marker.exists())
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
            process.communicate(timeout=8)
        self.assertFalse((self.home/'dots').exists())
        git.unlink()  # remove only the fixture wrapper, then use real Git
        result = subprocess.run(helper, cwd=self.home, env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.base/'unexpected-python').exists())
        self.assertTrue((self.home/'dots/lib/dots/shell/startup.bash').is_file())

    def test_partial_native_checkout_is_not_sourced(self):
        dest = self.home/'dots'
        launcher = dest/'bin/dots'
        launcher.parent.mkdir(parents=True)
        shutil.copy2(self.src/'bin/dots', launcher)
        for name, shell, flags, check in (
            ('shells/fish/init.fish', 'fish', ['--no-config'], 'if set -q LOADED; echo "$LOADED"; else; echo absent; end'),
            ('shells/nushell/init.nu', 'nu', ['-n'], 'print ($env.LOADED? | default "absent")'),
            ('shells/xonsh/init.xsh', 'xonsh', ['--no-rc'], 'print(__xonsh__.env.get("LOADED","absent"))'),
        ):
            binary = shutil.which(shell)
            if not binary:
                continue
            with self.subTest(shell=shell):
                native = dest/name
                native.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(self.src/name, native)
                startup = self.base/('bootstrap' + native.suffix)
                startup.write_text(snippet(shell))
                command = 'source ' + json.dumps(str(startup), ensure_ascii=False) + '\n' + check
                result = subprocess.run([binary, *flags, '-c', command], cwd=self.home,
                                        env=dict(self.env, DOTS_BOOTSTRAP_DIR=str(dest)), capture_output=True, text=True, timeout=10)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout.strip(), 'absent', result.stderr)
        self.assertFalse((dest/'.git').exists())

    def test_existing_local_source_spellings_and_journal(self):
        helper = ['sh', str(ROOT/'lib/dots/shell/bootstrap/locate.sh'), 'interactive']
        for number, source in enumerate((self.src.name, self.src.as_uri())):
            dest = self.base / f'quoted " $ directory {number}'
            env = dict(self.env, DOTS_BOOTSTRAP_SOURCE=source, DOTS_BOOTSTRAP_DIR=str(dest))
            result = subprocess.run(helper, cwd=self.base, env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            journal, = self.base.glob('.' + dest.name + '.bootstrap-*/journal.json')
            self.assertEqual(json.loads(journal.read_text()),
                             dict(version=1, status='committed', destination=str(dest), ref='main'))

    def test_occupied_and_failed_clone_preserve_target(self):
        target=self.home/'dots'
        target.mkdir()
        (target/'keep').write_text('unchanged')
        command=['sh',str(ROOT/'lib/dots/shell/bootstrap/locate.sh'),'interactive']
        failed=subprocess.run(command,env=self.env,capture_output=True,text=True)
        self.assertNotEqual(failed.returncode,0)
        self.assertEqual((target/'keep').read_text(),'unchanged')
        dest=self.home/'missing'
        env=dict(self.env,DOTS_BOOTSTRAP_REF='no-such-ref',DOTS_BOOTSTRAP_DIR=str(dest))
        failed=subprocess.run(command,env=env,capture_output=True,text=True)
        self.assertNotEqual(failed.returncode,0)
        self.assertFalse(dest.exists())
        statuses=[json.loads(p.read_text())['status'] for p in self.home.glob('.missing.bootstrap-*/journal.json')]
        self.assertEqual(statuses,['failed'])


if __name__=='__main__':
    unittest.main()
