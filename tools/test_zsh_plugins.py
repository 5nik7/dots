#!/usr/bin/env python3
"""Isolated public-plugin acquisition, recovery and first-key activation."""
import concurrent.futures
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'lib/dots'))
import zsh_plugins as plugins


@unittest.skipUnless(os.name == 'posix' and shutil.which('zsh'), 'requires Zsh on POSIX')
class Plugins(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='dots-plugins-ü-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.commands = self.root / 'commands'
        self.commands.mkdir()
        self.log = self.root / 'requests'
        self.manager = self.root / 'Zinit manager'
        self.installed = self.root / 'first plugins'
        self.state = self.root / 'private state'
        self.env = {'HOME': str(self.root), 'PATH': str(self.commands) + os.pathsep + os.environ['PATH'],
                    'DOTS': str(ROOT), 'ZDOTDIR': str(self.root), 'TERM': 'xterm-256color',
                    'XDG_STATE_HOME': str(self.root/'state'), 'XDG_DATA_HOME': str(self.root/'data'),
                    'GIT_CONFIG_GLOBAL': str(self.root/'should never read'), 'GIT_ASKPASS':'sentinel'}
        for key in ('TMPDIR', 'LD_PRELOAD', 'PREFIX'):
            if key in os.environ:
                self.env[key] = os.environ[key]

        self.fake('git', '''import json, os, sys, time
from pathlib import Path
source, stage = sys.argv[-2:]
assert os.environ['GIT_CONFIG_GLOBAL'] == os.devnull and 'GIT_ASKPASS' not in os.environ
assert os.environ['GIT_ALLOW_PROTOCOL'] == 'https' and os.environ['GIT_TERMINAL_PROMPT'] == '0'
assert source.startswith('https://github.com/') and source.endswith('.git')
name = source.removeprefix('https://github.com/').removesuffix('.git')
with LOG.open('a') as f: print(name, file=f)
if (LOG.parent/'fail').exists(): sys.exit(9)
if (LOG.parent/'pause').exists(): time.sleep(0.3)
stage=Path(stage); stage.mkdir()
if name == 'zdharma-continuum/zinit':
    (stage/'zinit.zsh').write_text('zinit() { [[ $1 != light ]] || print -r -- "$2" >> "$HOME/activated"; return 0; }')
else:
    (stage/(name.split('/')[1]+'.plugin.zsh')).touch()
    if name == 'zsh-users/zsh-completions':
        (stage/'src').mkdir()
        (stage/'src/_synthetic').write_text('#compdef synthetic-fixture\\n')
''')
        self.fake('curl', '''import sys
from pathlib import Path
args=sys.argv[1:]
with LOG.open('a') as f: print(args[-1], file=f)
assert args[0] == '--disable' and '--max-time' in args and '--max-filesize' in args
path=LOG.parent / ('archive' if args[-1].endswith('.gz') else 'metadata')
Path(args[args.index('--output')+1]).write_bytes(path.read_bytes())
''')

    def fake(self, name, body):
        path = self.commands/name
        path.write_text('#!'+sys.executable+'\nfrom pathlib import Path\nLOG=Path('+repr(str(self.log))+')\n'+body)
        path.chmod(0o700)

    def command(self, *names, mode='auto', platform='termux'):
        return subprocess.run([sys.executable,'-B',str(ROOT/'lib/dots/zsh_plugins.py'),
                               mode,str(self.manager),str(self.installed),str(self.state),platform,'aarch64',*names],
                              env=self.env,cwd=self.root,capture_output=True,text=True,timeout=30)

    def test_concurrent_receipts_failure_retry_and_occupied_path(self):
        name='Aloxaf/fzf-tab'
        (self.root/'pause').touch()
        with concurrent.futures.ThreadPoolExecutor() as pool:
            results=list(pool.map(lambda n:self.command(n), [name,name]))
        self.assertTrue(all(r.returncode==0 for r in results),results)
        self.assertEqual(self.log.read_text().splitlines(),[name])
        self.assertTrue((self.installed/'Aloxaf---fzf-tab/fzf-tab.plugin.zsh').exists())
        (self.root/'fail').touch()
        for _ in range(2):
            self.assertNotEqual(self.command(plugins.MANAGER).returncode,0)
        self.assertEqual(self.log.read_text().count(plugins.MANAGER),1)
        (self.root/'fail').unlink()
        self.assertEqual(self.command(plugins.MANAGER,mode='retry').returncode,0)
        self.assertEqual(self.log.read_text().count(plugins.MANAGER),2)
        (self.installed/'zsh-users---zsh-autosuggestions').mkdir()
        p=self.command('zsh-users/zsh-autosuggestions',mode='setup')
        self.assertNotEqual(p.returncode,0)
        self.assertIn('occupied',p.stderr)
        self.assertNotIn('zsh-users/zsh-autosuggestions',self.log.read_text())

    def test_interrupted_receipt_and_bounded_transport(self):
        import hashlib
        target = self.installed / 'Aloxaf---fzf-tab'
        self.state.mkdir()
        token = hashlib.sha256(os.fsencode(target)).hexdigest()
        (self.state / (token + '.status')).write_text('preparing\n')
        self.assertNotEqual(self.command('Aloxaf/fzf-tab').returncode, 0)
        self.assertFalse(self.log.exists())
        self.assertEqual(self.command('Aloxaf/fzf-tab',mode='retry').returncode, 0)
        self.assertEqual((self.state / (token + '.status')).read_text().strip(), 'installed')
        started = time.monotonic()
        with self.assertRaises((ValueError, subprocess.TimeoutExpired)):
            plugins.run([sys.executable, '-c', 'import time; time.sleep(60)'], self.root, started + 0.2)
        self.assertLess(time.monotonic() - started, 4)

    def test_deja_release_is_bounded_and_platform_specific(self):
        name=plugins.BINARY
        filename='deja_0.0.1_linux_arm64.tar.gz'
        (self.root/'metadata').write_text(json.dumps({'tag_name':'v0.0.1','assets':[{'name':filename}]}))
        with tarfile.open(self.root/'archive','w:gz') as archive:
            content=b'fixture binary'
            info=tarfile.TarInfo('./deja')
            info.size=len(content)
            archive.addfile(info,io.BytesIO(content))
        self.assertNotEqual(self.command(name).returncode,0)
        self.assertFalse(self.log.exists())
        p=self.command(name,mode='setup',platform='wsl')
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertEqual((self.installed/name/'deja').read_bytes(),content)
        self.assertEqual((self.installed/name/'._zinit/is_release').read_text().strip(),
                         f'/{plugins.DEJA}/releases/download/v0.0.1/{filename}')
        self.assertEqual(len(self.log.read_text().splitlines()),2)
        self.assertEqual(self.command(name,platform='wsl').returncode,0)
        self.assertEqual(len(self.log.read_text().splitlines()),2)

    def test_offline_first_command_uses_no_worker_or_receipt(self):
        from zsh_interactive import Session
        offline = self.root / 'offline-bin'
        offline.mkdir()
        self.fake('python3', "LOG.write_text('unexpected Python worker')")
        (offline / 'python3').symlink_to(self.commands / 'python3')
        env = dict(self.env, PATH=str(offline))
        (self.root / '.zshrc').write_text('''autoload -Uz add-zle-hook-widget
source "$DOTS/shells/zsh/integrations/plugins.zsh"
DOTS_ZSH_SUGGESTIONS=none
_dots_completion_plugins
_dots_widget_plugins
_dots_plugins_arm
_ready() { print -r -- __DOTS_INPUT_READY__; }
add-zle-hook-widget line-init _ready
''')
        session = Session(env, self.root)
        session.log = self.root / 'pty.log'
        self.addCleanup(session.close)
        session.wait()
        session.send('print -r -- "${#_DOTS_PLUGIN_WORKERS} ${#_DOTS_PLUGINS_REQUESTED} ${#_DOTS_PLUGINS_MISSING}" > "$HOME/first-command"\n')
        session.wait()
        counts = (self.root / 'first-command').read_text().split()
        self.assertEqual(counts[:2], ['0', '0'])
        self.assertGreater(int(counts[2]), 0)
        self.assertFalse(self.log.exists())
        self.assertFalse((self.root / 'state/dots/zsh/plugins').exists())

    def test_queue_filters_each_transport_and_explicit_setup_reports_failure(self):
        repo = 'Aloxaf/fzf-tab'
        cases = (
            (('git', 'curl', 'timeout'), set()),
            (('python3', 'git', 'curl'), set()),
            (('python3', 'timeout'), set()),
            (('python3', 'timeout', 'curl'), {plugins.BINARY}),
            (('python3', 'timeout', 'git'), {plugins.MANAGER, repo}),
        )
        script = '''autoload -Uz add-zsh-hook
source "$DOTS/shells/zsh/integrations/plugins.zsh"
source "$DOTS/lib/dots/shell/plugins.zsh"
_dots_plugins_acquire() { :; }
for name in "$@"; do _DOTS_PLUGINS_MISSING[$name]=1; done
_dots_plugins_queue "$@"
print -r -- ${#_DOTS_PLUGIN_WORKERS}
print -rl -- "${(@k)_DOTS_PLUGINS_REQUESTED}"
'''
        for index, (available, expected) in enumerate(cases):
            with self.subTest(available=available):
                commands = self.root / f'bin-{index}'
                commands.mkdir()
                for name in available:
                    (commands / name).symlink_to(sys.executable)
                result = subprocess.run(
                    [shutil.which('zsh'), '-dfc', script, 'queue', plugins.MANAGER, repo, plugins.BINARY],
                    cwd=self.root, env=dict(self.env, PATH=str(commands)),
                    capture_output=True, text=True, check=True, timeout=5)
                workers, *requested = result.stdout.strip().splitlines()
                self.assertEqual(workers, str(int(bool(expected))))
                self.assertEqual(set(requested), expected)
        commands = self.root / 'explicit-bin'
        commands.mkdir()
        (commands / 'python3').symlink_to(sys.executable)
        for mode in ('setup', 'retry'):
            result = subprocess.run(
                [shutil.which('zsh'), '-dfc', '''source "$DOTS/shells/zsh/integrations/plugins.zsh"
_DOTS_PLUGINS_MISSING[Aloxaf/fzf-tab]=1
dots-zsh-plugins "$1"''', 'explicit', mode],
                cwd=self.root, env=dict(self.env, PATH=str(commands), DOTS_ZSH_SUGGESTIONS='none'),
                capture_output=True, text=True, timeout=10)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('the timeout utility is required', result.stderr)

    def test_first_history_key_dispatches_native_widget_and_only_its_plugin(self):
        from zsh_interactive import Session
        (self.root/'.zshrc').write_text('''autoload -Uz add-zsh-hook add-zle-hook-widget
source "$DOTS/shells/zsh/integrations/plugins.zsh"
DOTS_ZSH_SUGGESTIONS=none
_dots_completion_plugins
_dots_widget_plugins
bindkey -e
bindkey '^[[A' up-line-or-history
print -s 'history-first-native'
_dots_plugins_arm
_ready() { print -r -- __DOTS_INPUT_READY__; }
add-zle-hook-widget line-init _ready
''')
        session=Session(self.env,self.root)
        session.log=self.root / 'pty.log'
        self.addCleanup(session.close)
        session.wait()
        self.assertFalse(self.log.exists())
        session.send('\x1b[A')
        session.wait(b'history-first-native')
        deadline=time.monotonic()+15
        while time.monotonic()<deadline:
            if self.log.exists() and 'zsh-users/zsh-history-substring-search' in self.log.read_text():
                break
            time.sleep(0.05)
        self.assertEqual(set(self.log.read_text().splitlines()),
                         {plugins.MANAGER,'zsh-users/zsh-history-substring-search'})

    def test_actual_first_tab_native_fallback_then_safe_prompt_activation(self):
        from zsh_interactive import Session
        rc=self.root/'.zshrc'
        rc.write_text('''autoload -Uz compinit add-zsh-hook add-zle-hook-widget
compinit -D
_fixture_widget() { :; }
zle -N complete-word _fixture_widget
compdef _files kept-user-command
source "$DOTS/shells/zsh/integrations/plugins.zsh"
DOTS_ZSH_SUGGESTIONS=none
DOTS_PLATFORM=termux
_dots_completion_plugins
_dots_widget_plugins
_dots_compinit() { :; }
_dots_completion_compat() { :; }
_dots_plugins_arm
PROMPT='P> '
_ready() { print -r -- __DOTS_INPUT_READY__; }
add-zle-hook-widget line-init _ready
''')
        (self.root/'unique-first-file').touch()
        session=Session(self.env,self.root)
        session.log = self.root / 'pty.log'
        self.addCleanup(session.close)
        session.wait()
        self.assertFalse(self.log.exists())
        session.send('print -r -- unique-first-fi\t')
        completion=('zsh-users/zsh-completions','Aloxaf/fzf-tab')
        def wait_requests(names):
            deadline=time.monotonic()+15
            while time.monotonic()<deadline:
                if self.log.exists() and set(names) <= set(self.log.read_text().splitlines()):
                    break
                time.sleep(0.04)
            requests=self.log.read_text().splitlines() if self.log.exists() else []
            self.assertTrue(set(names)<=set(requests),requests)
            return requests
        self.assertEqual(set(wait_requests(completion)),{plugins.MANAGER,*completion})
        self.assertFalse((self.root/'activated').exists())
        session.send('\t\n')
        self.assertIn(b'unique-first-file',session.wait())
        rest=['zdharma-continuum/fast-syntax-highlighting','zsh-users/zsh-history-substring-search']
        wait_requests(rest)
        for _ in range(15):
            time.sleep(0.1)
            session.send(':\n');session.wait()
            active=self.root/'activated'
            if active.exists() and set(rest+list(completion)) <= set(active.read_text().splitlines()):
                break
        self.assertTrue(active.exists())
        self.assertEqual(sorted(active.read_text().splitlines()),sorted(rest+list(completion)))
        session.send('print -r -- "$_comps[synthetic-fixture]|$_comps[kept-user-command]|$widgets[complete-word]" > "$HOME/after"\n')
        session.wait()
        self.assertEqual((self.root/'after').read_text().strip(),'_synthetic|_files|user:_fixture_widget')
        session.send('source "$HOME/.zshrc"\n');session.wait()
        self.assertEqual(len(self.log.read_text().splitlines()),5)


if __name__ == '__main__':
    unittest.main()
