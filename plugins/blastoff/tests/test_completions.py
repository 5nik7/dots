"""Offline native-shell dispatch tests; no application/checksum dependency.

Fish uses complete -C. Bash invokes its registered callback (compopt is a
labelled stub outside Readline). Zsh invokes its autoload callback with labelled
compadd/_files stubs: this verifies dispatch, not ZLE quoting or fzf-tab.
"""
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SHELLS = {name: shutil.which(name) for name in ('bash', 'zsh', 'fish')}


@unittest.skipUnless(os.name == 'posix', 'POSIX shell/symlink fixtures; Windows is a separate gate')
class CompletionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='blastoff completion ')
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.store = self.home / 'store with spaces'
        for kind in ('themes', 'modules', 'backups'):
            (self.store / kind).mkdir(parents=True)
        for name in ('alpha', 'auto', 'always', 'never', 'apply', 'a' * 96,
                     'a' * 97, 'CON', 'nul', 'COM1', 'lpt9', 'bad.name',
                     'bad name', 'éclair', '_bad'):
            (self.store / 'themes' / (name + '.toml')).write_text('')
        (self.store / 'themes' / 'linked.toml').symlink_to('alpha.toml')
        (self.store / 'themes' / 'directory.toml').mkdir()
        if hasattr(os, 'mkfifo'):
            os.mkfifo(self.store / 'themes' / 'pipe.toml')
        (self.store / 'modules' / 'snippet.toml').write_text('')
        for suffix in ('toml', 'json'):
            (self.store / 'backups' / ('20260930T120000Z-abcdef.' + suffix)).write_text('')
        (self.store / 'backups' / 'unpaired.toml').write_text('')
        (self.store / 'backups' / 'linked.toml').symlink_to('unpaired.toml')
        (self.store / 'backups' / 'linked.json').write_text('')
        (self.home / 'empty-bin').mkdir()
        self.env = dict(os.environ, HOME=str(self.home), BLASTOFF_HOME=str(self.store),
                        XDG_CONFIG_HOME=str(self.home / 'xdg'),
                        PATH=str(self.home / 'empty-bin'))
        # This Fish build creates its own XDG scaffold even for `-c true`.
        # Separate shell initialization from completion-triggered writes.
        if SHELLS['fish']:
            subprocess.run([SHELLS['fish'],'--no-config','--private','-c','true'],
                           env=self.env,capture_output=True,check=True,timeout=5)

    def snapshot(self):
        # lstat only: never open FIFO/symlink fixtures. Ignore read-access times.
        return {str(p.relative_to(self.home)): (p.lstat().st_mode, p.lstat().st_size, p.lstat().st_mtime_ns)
                for p in [self.home, *self.home.rglob('*')]}

    def complete(self, shell, args):
        if not SHELLS[shell]:
            self.skipTest(shell + ' unavailable')
        script = ROOT / 'completions' / ('blastoff.' + shell)
        quoted = ' '.join(shlex.quote(x) for x in ['blastoff', *args])
        if shell == 'bash':
            code = (f'source {shlex.quote(str(script))}; '
                    'compopt() { :; }; COMP_WORDBREAKS=""; '  # Readline-only API stub
                    f'COMP_WORDS=({quoted}); COMP_CWORD={len(args)}; '
                    '_blastoff; printf "%s\\n" "${COMPREPLY[@]}"')
            command = [SHELLS[shell], '--noprofile', '--norc', '-c', code]
        elif shell == 'zsh':
            # Capture candidates, not matching (normally handled by compadd).
            code = (f'source {shlex.quote(str(script))}; '
                    'compadd() { local x; [[ $1 == -S ]] && shift 2; if [[ $1 == -a ]]; then '
                    'for x in "${(@P)2}"; do print -r -- "$x"; done; '
                    'else for x in "$@"; do [[ $x == -- ]] || print -r -- "$x"; done; fi; }; '
                    '_files() { print -r -- "@FILES:$*"; }; '
                    f'words=({quoted}); CURRENT={len(args)+1}; _blastoff')
            command = [SHELLS[shell], '-f', '-c', code]
        else:
            line = 'blastoff ' + ' '.join(shlex.quote(x) for x in args[:-1]) + ' '
            line += shlex.quote(args[-1]) if args[-1] else ''
            code = f'source {shlex.quote(str(script))}; complete -C {shlex.quote(line)}'
            command = [SHELLS[shell], '--no-config', '--private', '-c', code]
        before = self.snapshot()
        result = subprocess.run(command, env=self.env, cwd=self.home,
                                text=True, capture_output=True, timeout=5)
        self.assertEqual(self.snapshot(), before, 'Completion wrote into its isolated HOME/storage')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '', result.stderr)
        return {line.split('\t')[0] for line in result.stdout.splitlines() if line}

    def test_release_017_contexts(self):
        for reserved in ('all','y','yes'):
            for suffix in ('toml','json'):
                (self.store/'backups'/(reserved+'.'+suffix)).write_text('')
        cases = [
            (['theme',''], {'edit'}, set()),
            (['module','show',''], {'snippet'}, {'alpha'}),
            (['backup','delete',''], {'all','20260930T120000Z-abcdef'}, {'y','yes'}),
            (['backup','delete','ID',''], {'y','yes','20260930T120000Z-abcdef'}, {'all'}),
            (['backup','delete','--yes','--',''], {'all','y','yes'}, set()),
            (['backup','delete','all','yes',''], set(), {'y','yes','all','20260930T120000Z-abcdef'}),
            (['backup','delete','ID','Yes',''], set(), {'y','yes','all','20260930T120000Z-abcdef'}),
            (['backup','delete','ALL',''], {'y','yes'}, {'20260930T120000Z-abcdef','all'}),
            (['backup','delete','--all',''], {'y','yes'}, {'20260930T120000Z-abcdef'}),
            (['backup','delete','--'], {'--all','--pick','--yes','--dry-run','--verbose'}, set()),
            (['pick',''], {'fancy','fzf'}, set()),
            (['pick','--'], {'--fancy','--fzf'}, set()),
            (['pick','--fzf','--'], {'--fzf'}, {'--fancy'}),
            (['pick','fancy','--'], {'--fancy'}, {'--fzf'}),
            (['module','show','--'], {'--fancy','--fzf'}, set()),
            (['backup','delete','--pick','--'], {'--fancy','--fzf'}, set()),
            (['backup','delete','--pick','--fancy',''], {'unicode','ascii'}, {'all'}),
            (['pick','--fancy',''], {'unicode','ascii'}, {'fancy'}),
            (['pick','--fancy='], {'--fancy=unicode','--fancy=ascii'}, set()),
            (['-v','module','--dry-run','show',''], {'snippet'}, set()),
        ]
        for shell in SHELLS:
            for args, expected, excluded in cases:
                with self.subTest(shell=shell,args=args):
                    got=self.complete(shell,args)
                    self.assertTrue(expected <= got,(expected,got))
                    self.assertFalse(excluded & got,got)

    def test_positions(self):
        cases = [
            (['theme', 'apply', ''], {'alpha', 'local:', 'preset:'}, {'snippet'}),
            (['theme', 'copy', ''], {'alpha', 'local:', 'preset:'}, set()),
            (['theme', 'delete', ''], {'alpha'}, {'local:', 'preset:'}),
            (['theme', 'copy', 'alpha', ''], set(), {'alpha', 'local:', 'preset:'}),
            (['theme', 'save', ''], set(), {'alpha', 'local:', 'preset:'}),
            (['theme', 'import', '/tmp/input', ''], set(), {'alpha', 'local:'}),
            (['module', 'load', ''], {'snippet'}, {'alpha'}),
            (['module', 'delete', ''], {'snippet'}, {'alpha'}),
            (['module', 'save', ''], set(), {'snippet', 'alpha'}),
            (['module', 'save', 'directory', ''], set(), {'snippet'}),
            (['preset', 'save', 'preset-name', ''], set(), {'alpha', 'preset:'}),
            (['backup', 'restore', ''], {'20260930T120000Z-abcdef'}, {'unpaired', 'linked'}),
            (['completion', ''], {'bash', 'zsh', 'fish'}, set()),
            (['--json', 'theme', '--color', 'auto', 'apply', '--force', ''], {'alpha'}, set()),
            (['theme', 'copy', 'auto', '--json', ''], set(), {'alpha'}),
            (['theme', 'copy', 'always', '--color=never', ''], set(), {'alpha'}),
            (['theme', 'apply', 'never', '--replace-link', ''], set(), {'alpha'}),
            (['--color=always', '--theme', '--json', ''], {'alpha', 'local:'}, set()),
            (['-t', ''], {'alpha', 'preset:'}, set()),
            (['-l', ''], set(), {'alpha', 'theme'}),
            (['--list', ''], set(), {'alpha', 'theme'}),
            (['theme', '--color', ''], {'auto', 'always', 'never'}, {'apply'}),
            (['theme', 'apply', '--color', ''], {'auto', 'always', 'never'}, {'alpha'}),
            (['theme', 'apply', 'alpha', '--color', ''], {'auto', 'always', 'never'}, {'alpha'}),
        ]
        for shell in SHELLS:
            for args, expected, excluded in cases:
                with self.subTest(shell=shell, args=args):
                    got = self.complete(shell, args)
                    self.assertTrue(expected <= got, (expected, got))
                    self.assertFalse(excluded & got, got)

    def test_options_and_operand_boundaries(self):
        for shell in SHELLS:
            for flag in ('--json', '--force', '--replace-link', '--color=auto'):
                for index in range(4):
                    args = ['theme', 'copy', 'never', '']
                    args.insert(index, flag)
                    with self.subTest(shell=shell, flag=flag, index=index):
                        self.assertFalse(self.complete(shell, args))
            for args, expected in [
                ([''], {'theme', 'backup'}),
                (['theme', ''], {'apply', 'copy'}),
                (['theme', 'apply', '--'], {'--force', '--color'}),
                (['theme', 'apply', '--color='], {'--color=auto', '--color=always', '--color=never'}),
                (['theme', 'apply', '--color', 'a'], {'auto', 'always'}),
                (['--color', '--json', 'theme', 'apply', ''], {'alpha'}),
            ]:
                with self.subTest(shell=shell, args=args):
                    self.assertTrue(expected <= self.complete(shell, args))
            self.assertFalse(self.complete(shell, ['theme', 'copy', '--', '--json', '']))
            self.assertIn('--version', self.complete(shell, ['--']))
            self.assertNotIn('--version', self.complete(shell, ['theme', '--']))

    def test_bash_readline_wordbreaks(self):
        if not SHELLS['bash']:
            self.skipTest('bash unavailable')
        for words, expected in [
            (['theme', 'apply', 'local', ':', 'a'], {'alpha', 'auto', 'always', 'apply', 'a' * 96}),
            (['theme', 'apply', 'local', ':'], {'alpha', 'auto', 'always', 'never', 'apply', 'a' * 96}),
            (['theme', 'copy', 'local', ':', 'alpha', ''], set()),
            (['theme', 'apply', '--color', '=', 'a'], {'auto', 'always'}),
            (['theme', '--color', '=', 'never', 'apply', ''], {'local:', 'preset:', 'alpha', 'auto', 'always', 'never', 'apply', 'a' * 96}),
        ]:
            with self.subTest(words=words):
                quoted = ' '.join(shlex.quote(x) for x in ['blastoff', *words])
                code = (f'source {shlex.quote(str(ROOT / "completions/blastoff.bash"))}; '
                        'compopt() { :; }; COMP_WORDBREAKS="=:"; '
                        f'COMP_WORDS=({quoted}); COMP_CWORD={len(words)}; '
                        '_blastoff; printf "%s\\n" "${COMPREPLY[@]}"')
                result = subprocess.run([SHELLS['bash'], '--noprofile', '--norc', '-c', code],
                                        env=self.env, text=True, capture_output=True, timeout=5)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stderr, '')
                self.assertEqual(set(result.stdout.split()), expected)

    def test_zsh_autoload_registration(self):
        if not SHELLS['zsh']:
            self.skipTest('zsh unavailable')
        folder = self.home / 'completion functions'
        folder.mkdir()
        shutil.copyfile(ROOT / 'completions/blastoff.zsh', folder / '_blastoff')
        code = (f'fpath=({shlex.quote(str(folder))} $fpath); autoload -Uz compinit; compinit -D; '
                '[[ $_comps[blastoff] == _blastoff ]] || exit 1; '
                'compadd() { :; }; words=(blastoff theme apply ""); CURRENT=4; _blastoff')
        result = subprocess.run([SHELLS['zsh'], '-f', '-c', code], env=self.env,
                                text=True, capture_output=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')

    def test_safe_names(self):
        valid = {'alpha', 'auto', 'always', 'never', 'apply', 'a' * 96}
        for shell in SHELLS:
            with self.subTest(shell=shell):
                got = self.complete(shell, ['theme', 'apply', ''])
                self.assertEqual({x for x in got if not x.startswith('-')}, valid | {'local:', 'preset:'})

    def test_linked_storage_root(self):
        alias = self.home / 'linked store'
        alias.symlink_to(self.store, target_is_directory=True)
        self.env['BLASTOFF_HOME'] = str(alias)
        for shell in SHELLS:
            for args, expected in [(['theme', 'apply', ''], 'alpha'),
                                   (['module', 'load', ''], 'snippet'),
                                   (['backup', 'restore', ''], '20260930T120000Z-abcdef')]:
                with self.subTest(shell=shell, args=args):
                    self.assertIn(expected, self.complete(shell, args))
        self.assertTrue(alias.is_symlink())
        for kind, args, excluded in [('themes', ['theme', 'apply', ''], 'alpha'),
                                     ('modules', ['module', 'load', ''], 'snippet'),
                                     ('backups', ['backup', 'restore', ''], '20260930T120000Z-abcdef')]:
            child = self.store / kind
            target = self.home / ('outside-' + kind)
            child.rename(target)
            child.symlink_to(target, target_is_directory=True)
            for shell in SHELLS:
                with self.subTest(shell=shell, child=kind):
                    self.assertNotIn(excluded, self.complete(shell, args))

    def test_empty_store(self):
        self.env['BLASTOFF_HOME'] = str(self.home / 'missing')
        for shell in SHELLS:
            with self.subTest(shell=shell):
                got = self.complete(shell, ['module', 'load', ''])
                self.assertFalse({x for x in got if not x.startswith('-')})
        self.assertFalse((self.home / 'missing').exists())

    def test_safe_backup_pairs(self):
        backup = self.store / 'backups'
        for name in ('CON', 'cOm9', 'Lpt1', 'bad.name', 'bad name', 'a' * 97):
            for suffix in ('json', 'toml'):
                (backup / (name + '.' + suffix)).write_text('')
        (backup / 'json-link.toml').write_text('')
        (backup / 'json-link.json').symlink_to('linked.json')
        (backup / 'json-dir.toml').write_text('')
        (backup / 'json-dir.json').mkdir()
        for shell in SHELLS:
            with self.subTest(shell=shell):
                self.assertEqual(self.complete(shell, ['backup', 'restore', '']),
                                 {'20260930T120000Z-abcdef'})

    def test_storage_roots(self):
        for root in ('~/store with spaces', '', None):
            if root is None:
                self.env.pop('BLASTOFF_HOME', None)
            else:
                self.env['BLASTOFF_HOME'] = root
            if not root:
                default = self.home / '.config' / 'blastoff' / 'themes'
                default.mkdir(parents=True, exist_ok=True)
                (default / 'alpha.toml').write_text('')
            for shell in SHELLS:
                with self.subTest(shell=shell, root=root):
                    self.assertIn('alpha', self.complete(shell, ['theme', 'apply', '']))
        link = self.home / 'linked-store'
        link.symlink_to(self.store, target_is_directory=True)
        self.env['BLASTOFF_HOME'] = str(link)
        for shell in SHELLS:
            with self.subTest(shell=shell, root='symlink'):
                self.assertIn('alpha', self.complete(shell, ['theme', 'apply', '']))
        empty = self.home / 'empty-store' / 'modules'
        empty.mkdir(parents=True)
        self.env['BLASTOFF_HOME'] = str(empty.parent)
        for shell in SHELLS:
            with self.subTest(shell=shell, root='empty'):
                self.assertFalse(self.complete(shell, ['module', 'load', '']))

    def test_prefixes(self):
        for shell in SHELLS:
            with self.subTest(shell=shell):
                got = self.complete(shell, ['theme', 'apply', 'local:a'])
                self.assertIn('local:alpha', got)
                self.assertNotIn('preset:', got)
                self.assertFalse(self.complete(shell, ['theme', 'apply', 'preset:a']))

    def test_paths(self):
        path = self.home / 'input space.toml'
        path.write_text('')
        directory = self.home / 'input directory'
        directory.mkdir()
        for shell in SHELLS:
            with self.subTest(shell=shell):
                got = self.complete(shell, ['theme', 'import', str(self.home / 'input')])
                if shell == 'zsh':
                    self.assertEqual(got, {'@FILES:'})
                    self.assertEqual(self.complete(shell, ['migrate', '']), {'@FILES:-/'})
                else:
                    self.assertTrue(any('input space.toml' in x or 'input\\ space.toml' in x for x in got), got)
                    dirs = self.complete(shell, ['migrate', str(self.home / 'input')])
                    self.assertFalse(any('space.toml' in x for x in dirs), dirs)
                    self.assertTrue(any('directory' in x for x in dirs), dirs)
                self.assertFalse(self.complete(shell, ['theme', 'import', str(path), 'input']))
                self.assertFalse(self.complete(shell, ['migrate', str(directory), 'input']))


if __name__ == '__main__':
    unittest.main()
