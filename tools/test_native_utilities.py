"""Standalone utility adapters in owned roots; no live clipboard/network/UI."""
from contextlib import redirect_stdout, redirect_stderr
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'lib/dots'))
import utility_paths
import utility_options
from utility_commands import NAMES, complete
from utility_runtime import ToolExit
import utility_picker
import utility_web
import utility_cli


class BinaryOutput(io.StringIO):
    def __init__(self):
        super().__init__()
        self.buffer = io.BytesIO()


class OwnedFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='dots utilities ü ')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.home = self.base / 'home'; self.home.mkdir()
        self.env = dict(os.environ, HOME=str(self.home), USERPROFILE=str(self.home), DOTS=str(ROOT),
            XDG_CONFIG_HOME=str(self.home/'config'), XDG_STATE_HOME=str(self.home/'state'),
            XDG_CACHE_HOME=str(self.home/'cache'), XDG_DATA_HOME=str(self.home/'data'),
            APPDATA=str(self.home/'appdata'), LOCALAPPDATA=str(self.home/'localappdata'),
            DOTS_COLOR='never', DOTS_ICONS='never', DOTS_PROGRESS='never', DOTS_OPERATION_VERBOSE='0',
            PYTHONDONTWRITEBYTECODE='1')
        for key in ('DOTS_UTILITY_PWD', 'DOTS_UTILITY_TRANSPORT', 'CHTSH', 'CHTSH_CONF',
                    'CHTSH_URL', 'CHTSH_QUERY_OPTIONS', 'CHTSH_CURL_OPTIONS', 'WWW'):
            self.env.pop(key, None)


class Utilities(OwnedFixture):
    def test_linked_schema_deepest_relative_broken_and_literal_paths(self):
        target = self.home / 'target ü'; (target/'child [x]').mkdir(parents=True)
        link = self.home / "-link ' ü"
        link.symlink_to(target.name, target_is_directory=True)
        with patch.dict(os.environ, self.env, clear=True):
            data = utility_paths.linked_data(str(link/'child [x]'))
            self.assertEqual(data['symlink']['path'], str(link))
            self.assertEqual(data['source']['path'], str(target))
            self.assertEqual(data['prefix']['path'], 'child [x]')
            self.assertEqual(data['source']['with_prefix'], str(target/'child [x]'))
            self.assertEqual(data['placeholders']['%l'], '~'+os.sep+link.name)
            self.assertEqual(data['target']['physical'], str(target/'child [x]'))
            output = io.StringIO()
            with redirect_stdout(output): utility_paths.linked(['--raw', '--format', '%l -> %P %%', str(link/'child [x]')])
            self.assertEqual(output.getvalue(), str(link)+' -> '+str(target/'child [x]')+' %\n')
            broken = self.home/'broken'; broken.symlink_to(self.home/'missing')
            self.assertEqual(utility_paths.linked_data(str(broken))['source']['path'], str(self.home/'missing'))
            with self.assertRaises(FileNotFoundError): utility_paths.linked_data(str(target))
            with self.assertRaises(ValueError): utility_paths.linked([str(link), str(link)])

    def test_path_scalar_plain_and_predicate_contracts(self):
        target = self.home/'-file [ü]'; target.write_text('keep')
        with patch.dict(os.environ, self.env, clear=True):
            output = io.StringIO()
            with redirect_stdout(output):
                utility_paths.path_command('pathout', ['--raw', '--', '', '-literal', str(target)])
            self.assertEqual(output.getvalue(), '\n-literal\n'+str(target)+'\n')
            output = io.StringIO()
            with redirect_stdout(output): utility_paths.path_command('dirout', ['-r', str(target)])
            self.assertEqual(output.getvalue(), str(self.home)+'\n')
            self.assertEqual(utility_paths.path_command('isfile', [str(target)]), 0)
            self.assertEqual(utility_paths.path_command('isfile', ['--', str(target)]), 0)
            self.assertEqual(utility_paths.path_command('isdir', [str(target)]), 1)
            self.assertEqual(utility_paths.path_command('isdir', []), 1)

    def test_completion_literal_value_case_and_option_ownership(self):
        self.assertEqual(complete('linked', ['--', '--s']), [('file', '', '')])
        self.assertEqual(complete('linked', ['--format', '--']), [])
        self.assertEqual([r[1] for r in complete('linked', ['--arrays=z'])], ['--arrays=zsh'])
        self.assertEqual(complete('fzopt', ['height', '-']), [])
        self.assertIn(('candidate', 'prompt', ''), complete('fzopt', ['color', 'pr']))
        self.assertEqual(complete('HTTPGET.PS1', ['--h'], windows=False), [])
        self.assertIn(('candidate', '--help', ''), complete('HTTPGET.PS1', ['--h'], windows=True))

    def test_fzopt_literal_merge_and_managed_repeat(self):
        value = "--height=40% --prompt='old text' --bind='ctrl-x:execute(echo a,b),ctrl-y:accept' --color=fg:blue,bg:black"
        result = utility_options.edit(value, ['prompt', "$(throw 1) ' ü", 'color', 'fg', '#112233', 'unbind', 'ctrl-y'])
        words = utility_options.option_words(result)
        self.assertEqual(utility_options.get_option(words, 'prompt'), "$(throw 1) ' ü")
        self.assertEqual(utility_options.get_option(words, 'bind'), 'ctrl-x:execute(echo a,b)')
        self.assertEqual(utility_options.get_option(words, 'color'), 'bg:black,fg:#112233')
        with self.assertRaises(ValueError): utility_options.edit(value, ['unknown', 'value'])
        target = self.home/'.fzfrc'; target.write_text('original\n')
        with patch.dict(os.environ, self.env, clear=True):
            record = utility_options.publish_text(target, result+'\n', 'fzopt-write-rc')
            self.assertRegex(record, '^[0-9a-f]{32}$')
            self.assertIsNone(utility_options.publish_text(target, result+'\n', 'fzopt-write-rc'))
            sys.path.insert(0, str(ROOT/'lib/dots/files'))
            from transactions import Store
            store = Store(self.home/'state/dots')
            self.assertEqual(len(store.records()), 1)
            target.write_text('user drift\n')
            with self.assertRaisesRegex(ValueError, 'changed|drift'): store.inverse(record)
            self.assertEqual(target.read_text(), 'user drift\n')
            target.write_bytes((result+'\n').encode('utf-8'))
            operations, guards, catalogs = store.inverse(record)
            store.apply('undo', operations, guards, catalogs=catalogs, retain=True)
            self.assertEqual(target.read_text(), 'original\n')

    def test_cpwed_copy_exact_and_failed_provider_status(self):
        with patch('clipboard.copy') as copied, patch('utility_paths.cwd', return_value="C:\\literal ' ü"), redirect_stdout(io.StringIO()):
            self.assertEqual(utility_cli.main(['cpwd']), 0)
            copied.assert_called_once_with("C:\\literal ' ü")
        with patch('utility_web.http_get', side_effect=ToolExit(37, 'fixture failure')), redirect_stderr(io.StringIO()):
            self.assertEqual(utility_cli.main(['httpGet', 'https://example.invalid']), 37)

    def test_picker_cancellation_and_literal_provider_arguments(self):
        from interaction import SelectionEnded
        with patch('utility_picker.file_rows', return_value=[]), patch('utility_picker.pick', side_effect=SelectionEnded(130)), patch('utility_picker.execute') as launched:
            self.assertEqual(utility_picker.main('fzfd', []), 130)
            launched.assert_not_called()
        record = dict(type='match', data=dict(path=dict(text="-name ' ü"), line_number=7, lines=dict(text='literal\n')))
        with patch('utility_picker.capture', return_value=json.dumps(record).encode()+b'\n') as provider:
            rows = utility_picker.search_rows("-x $(touch nope)")
            provider.assert_called_once_with('rg', ['--json', '--smart-case', '-e', '-x $(touch nope)', '--', '.'], allowed=(0, 1))
            self.assertEqual(rows[0]['line'], 7)
        with patch.dict(os.environ, dict(self.env, EDITOR='vim'), clear=True), patch('utility_picker.execute', return_value=23) as launch:
            self.assertEqual(utility_picker.edit_match(rows[0]), 23)
            self.assertEqual(launch.call_args.args[0][-3:], ['+7', '--', rows[0]['path']])

    def test_picker_refresh_toggle_and_font_render_are_literal(self):
        from interaction import SelectionEvent
        row = dict(value='font', kind='font', renderer='figlet', text='-literal $(bad)')
        output = BinaryOutput()
        with patch('utility_picker.font_rows', return_value=[row]), patch('utility_picker.pick', return_value=row), patch('utility_picker.capture', side_effect=[b'rendered\n', b'filtered\n']) as rendered, patch('clipboard.copy') as copied, redirect_stdout(output):
            self.assertEqual(utility_picker.main('fzfig', ['--pipe', 'filter "literal argument"', '--', '-literal $(bad)']), 0)
            self.assertEqual(rendered.call_args_list[0].args, ('figlet', ['-f', 'font']))
            self.assertEqual(rendered.call_args_list[0].kwargs, dict(data=b'-literal $(bad)'))
            self.assertEqual(rendered.call_args_list[1].args, ('filter', ['literal argument']))
            copied.assert_called_once_with('filtered\n')
            self.assertEqual(output.buffer.getvalue(), b'filtered\n')
        with self.assertRaisesRegex(ValueError, 'shell program'):
            utility_picker.main('fzfig', ['-p', 'echo | bad'])
        def selection(*args, **kwargs):
            if selection.first:
                selection.first = False; kwargs['navigation']['query'] = 'literal'
                raise SelectionEvent('toggle')
            return dict(value='chosen')
        selection.first = True
        with patch('utility_picker.file_rows', return_value=[]) as files, patch('utility_picker.pick', side_effect=selection), redirect_stdout(io.StringIO()) as output:
            self.assertEqual(utility_picker.main('fzfd', []), 0)
            self.assertEqual([call.args for call in files.call_args_list], [(False,), (True,)])
            self.assertEqual(output.getvalue(), 'chosen\n')

    def test_preview_identity_and_sensitive_environment(self):
        rows = [dict(label='$(throw 1)', kind='text', preview='safe\x1b[31m\nnext')]
        with utility_picker.preview_snapshot(rows) as (command, _, environment):
            self.assertNotIn('$(throw 1)', command)
            self.assertIn('{1}', command)
            with redirect_stdout(io.StringIO()) as output:
                utility_picker.preview_main(['preview', environment['DOTS_UTILITY_SNAPSHOT'], '0'])
            self.assertNotIn('\x1b', output.getvalue())
            with self.assertRaises(ValueError): utility_picker.preview_main(['preview', environment['DOTS_UTILITY_SNAPSHOT'], '0;bad'])
        with patch.dict(os.environ, dict(API_TOKEN='secret-marker', PUBLIC='visible'), clear=True):
            found = {row['label']: row['value'] for row in utility_picker.environment_rows()}
            self.assertEqual(found['API_TOKEN'], 'API_TOKEN=<redacted>')
            self.assertEqual(found['PUBLIC'], 'PUBLIC=visible')

    def test_http_browser_query_no_live_provider(self):
        arguments = ['--header', 'literal $(bad)', 'https://example.invalid/a?b=c']
        with patch('utility_web.require', return_value='owned-curl'), patch('utility_web.execute', return_value=29) as provider:
            self.assertEqual(utility_web.http_get(arguments), 29)
            self.assertEqual(provider.call_args.args[0], ['curl', '-A', 'curl', '-s', *arguments])
        self.assertEqual(utility_web.remote_url('git@example.invalid:owner/repo.git'), 'https://example.invalid/owner/repo')
        self.assertNotIn('secret', utility_web.remote_url('https://user:secret@example.invalid/owner/repo.git'))
        self.assertEqual(utility_web.remote_url('https://user:secret@example.invalid:8443/team/repo.git'), 'https://example.invalid:8443/team/repo')
        self.assertEqual(utility_web.remote_url('https://user:secret@[::1]:8443/team/repo.git'), 'https://[::1]:8443/team/repo')
        self.assertEqual(utility_web.remote_url('http://[::1]:8080/team/repo.git'), 'https://[::1]:8080/team/repo')
        self.assertEqual(utility_web.remote_url('ssh://user@[::1]:2222/team/repo.git'), 'https://[::1]/team/repo')
        self.assertEqual(utility_web.browser_url(['--query', 'literal $(bad)', 'ü']), 'https://www.google.com/search?q=literal+%24%28bad%29+%C3%BC')
        with self.assertRaisesRegex(ValueError, 'HTTPS'): utility_web.browser_url(['http://example.invalid'])
        with patch('utility_web.webbrowser.open', return_value=True) as opened:
            self.assertEqual(utility_web.main('www', ['example.invalid']), 0)
            opened.assert_called_once_with('https://example.invalid')

    @unittest.skipUnless(os.name == 'nt', 'Windows executable boundary')
    def test_runtime_rejects_implicit_command_shell(self):
        import utility_runtime
        with patch('utility_runtime.shutil.which', side_effect=lambda name: 'C:\\owned\\fake.cmd' if name == 'fake' else None):
            with self.assertRaisesRegex(ToolExit, 'shell script'): utility_runtime.require('fake')
        with patch('utility_runtime.shutil.which', side_effect=lambda name: 'C:\\owned\\fake.exe' if name == 'fake.exe' else None):
            self.assertEqual(utility_runtime.require('fake'), 'C:\\owned\\fake.exe')

    def test_shared_picker_geometry_plain_light_dark_and_inert_rows(self):
        import interaction
        from files.catalog import Presentation
        from files import picker as files_picker
        rows = [dict(label='$(bad)\tü', value='selected', kind='text', preview='safe')]
        def selected(flags, **kwargs):
            self.assertEqual(kwargs['input'], '0\t$(bad)\\tü\0'.encode())
            self.assertTrue(any(flag.startswith('--preview=') and '{1}' in flag for flag in flags))
            self.assertFalse(any('$(bad)' in flag for flag in flags))
            self.assertIn('--header=Enter: select  Esc: cancel', flags)
            return subprocess.CompletedProcess(flags, 0, b'0\tignored\0')
        for columns in (40, 80, 120):
            for appearance in ('plain', 'light', 'dark'):
                palette = 'fg:#111111,bg:#eeeeee' if appearance == 'light' else 'fg:#eeeeee,bg:#111111'
                with self.subTest(columns=columns, appearance=appearance), patch.dict(os.environ, dict(self.env, DOTS_COLOR='never' if appearance == 'plain' else 'always'), clear=True), patch('utility_picker.require', return_value='owned-fzf'), patch('utility_picker.rich_fzf_available', return_value=True), patch('menu_popup.viewport', return_value=(columns, 24)), patch('files.picker.fzf_colors', return_value=palette), patch('interaction.subprocess.run', side_effect=selected):
                    self.assertEqual(utility_picker.pick('fixture', rows, header='Enter: select  Esc: cancel')['value'], 'selected')

    def test_cheat_literal_settings_query_and_journaled_files(self):
        owner = self.home/'.cht.sh'; owner.mkdir()
        (owner/'cht.sh.conf').write_text("CHTSH_URL='https://example.invalid'\nCHTSH_QUERY_OPTIONS='T&lang=en'\n")
        with patch.dict(os.environ, self.env, clear=True), redirect_stdout(io.StringIO()), patch('utility_web.capture', return_value=b'answer\n') as provider:
            client = utility_web.Cheat()
            self.assertEqual(client.query('python/literal+$(bad)'), b'answer\n')
            self.assertEqual(provider.call_args.args, ('curl', ['-s', '--', 'https://example.invalid/python/literal+%24%28bad%29?T&lang=en']))
            client.set_mode('lite'); client.set_mode('lite')
            self.assertEqual((owner/'mode').read_text(), 'lite\n')
            client.identity('test-only-identity-1234')
            self.assertIn('\tid\ttest-only-identity-1234', (owner/'id').read_text())
            client.identity('remove')
            self.assertNotIn('\tid\t', (owner/'id').read_text())
            (owner/'cht.sh.conf').write_text('CHTSH_URL=$(untrusted)\n')
            with self.assertRaisesRegex(ValueError, 'shell expressions'): utility_web.Cheat()
        with patch.dict(os.environ, dict(self.env, CHTSH_URL='https://override.invalid'), clear=True):
            self.assertEqual(utility_web.Cheat().url, 'https://override.invalid')

    def test_cheat_shell_explicit_copy_and_unsupported_status(self):
        with patch.dict(os.environ, self.env, clear=True):
            client = utility_web.Cheat()
            answers = iter(['copy', 'python list', 'copy', 'ccopy', 'hush', 'stealth', 'exit'])
            with patch.object(client, 'query', return_value=b'answer') as queried, patch('clipboard.copy') as copied, redirect_stdout(BinaryOutput()), redirect_stderr(io.StringIO()):
                self.assertEqual(utility_web.cheat_shell(client, read=lambda _:next(answers)), 3)
                self.assertEqual([call.args[0] for call in queried.call_args_list], ['python/list', 'python/list?T', 'python/list?TQ'])
                self.assertEqual(copied.call_count, 2)
                self.assertTrue((client.home/'.hushlogin').is_file())
            with self.assertRaisesRegex(ToolExit, 'native installer'): utility_web.cheat(['--standalone-install'])

    def test_journal_refuses_managed_source_link(self):
        source = self.home/'owned'; source.write_text('keep')
        target = self.home/'.fzfrc'; target.symlink_to(source)
        with patch.dict(os.environ, self.env, clear=True), self.assertRaisesRegex(ValueError, 'owning source'):
            utility_options.publish_text(target, 'replace', 'test')
        self.assertEqual(source.read_text(), 'keep')


PWSH = shutil.which(os.environ.get('DOTS_TEST_POWERSHELL') or 'pwsh')
if os.environ.get('DOTS_TEST_POWERSHELL') and not PWSH:
    raise SystemExit('required PowerShell engine unavailable')


@unittest.skipUnless(PWSH, 'native PowerShell unavailable')
class NativeAdapters(OwnedFixture):
    def setUp(self):
        super().setUp()
        self.repo = self.base / "repo ' [ü]"
        shutil.copytree(ROOT/'lib/dots', self.repo/'lib/dots', ignore=shutil.ignore_patterns('__pycache__'))
        (self.repo/'scripts').mkdir()
        for name in (*[name+'.ps1' for name in NAMES], 'linked'):
            shutil.copy2(ROOT/'scripts'/name, self.repo/'scripts'/name)
        self.env.update(DOTS=str(self.repo), TEMP=str(self.base), TMP=str(self.base), TMPDIR=str(self.base),
            PSModuleAnalysisCachePath=str(self.base/'ps-module-cache'), POWERSHELL_TELEMETRY_OPTOUT='1',
            POWERSHELL_UPDATECHECK='Off')

    def run_ps(self, code):
        import base64
        encoded = base64.b64encode(code.encode('utf-16le')).decode('ascii')
        return subprocess.run([PWSH, '-NoLogo', '-NoProfile', '-NonInteractive', '-EncodedCommand', encoded],
                              env=self.env, cwd=self.home, capture_output=True, text=True, encoding='utf-8', timeout=30)

    def test_native_literal_paths_predicates_and_environment_restoration(self):
        marker = self.home/'-literal [ü].txt'; marker.write_text('keep')
        code = r'''
$old=$env:DOTS; $env:DOTS='unrelated inherited checkout'
$paths=& (Join-Path $env:FIXTURE_ROOT 'scripts/pathout.ps1') --raw '--' '' '-literal [ü]'
& (Join-Path $env:FIXTURE_ROOT 'scripts/isfile.ps1') '-literal [ü].txt'; $exists=$LASTEXITCODE
& (Join-Path $env:FIXTURE_ROOT 'scripts/isdir.ps1') '-literal [ü].txt'; $directory=$LASTEXITCODE
@{paths=@($paths); exists=$exists; directory=$directory; root=$env:DOTS} | ConvertTo-Json -Compress
'''
        self.env['FIXTURE_ROOT'] = str(self.repo)
        result = self.run_ps(code)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), dict(paths=['', '-literal [ü]'], exists=0, directory=1,
                                                       root='unrelated inherited checkout'))

    def test_native_fzopt_updates_only_calling_environment(self):
        self.env.update(FIXTURE_ROOT=str(self.repo), FZF_DEFAULT_OPTS='--height=40% --color=fg:blue',
                        DOTS_UTILITY_PWD='previous literal', DOTS_UTILITY_TRANSPORT='previous transport')
        result = self.run_ps(r'''
& (Join-Path $env:FIXTURE_ROOT 'scripts/fzopt.ps1') prompt "literal $(if($false){'bad'}) ü" color fg '#112233'
$changed=$LASTEXITCODE
@{options=$env:FZF_DEFAULT_OPTS; code=$changed; pwd=$env:DOTS_UTILITY_PWD; transport=$env:DOTS_UTILITY_TRANSPORT} | ConvertTo-Json -Compress
''')
        self.assertEqual(result.returncode, 0, result.stderr)
        value = json.loads(result.stdout)
        self.assertEqual(value['code'], 0)
        self.assertEqual(value['pwd'], 'previous literal')
        self.assertEqual(value['transport'], 'previous transport')
        self.assertEqual(utility_options.get_option(utility_options.option_words(value['options']), 'color'), 'fg:#112233')
        self.assertIn('literal  ü', value['options'])
        self.assertFalse((self.home/'.fzfrc').exists())

    def test_native_help_all_wrappers_without_provider_or_state_writes(self):
        self.env['FIXTURE_ROOT'] = str(self.repo)
        code = '$names='+"@("+','.join("'"+name+"'" for name in NAMES)+")"+r'''
$results=@(); foreach($name in $names) {
  $out=& (Join-Path $env:FIXTURE_ROOT ('scripts/'+$name+'.ps1')) --help
  $results+=@{name=$name; code=$LASTEXITCODE; help=($out -join "`n")}
}; ConvertTo-Json -InputObject $results -Compress
'''
        result = self.run_ps(code)
        self.assertEqual(result.returncode, 0, result.stderr)
        values = json.loads(result.stdout)
        self.assertEqual(len(values), len(NAMES))
        for value in values:
            self.assertEqual(value['code'], 0, value)
            self.assertIn('usage:', value['help'].lower(), value)
        self.assertFalse((self.home/'state').exists())

    def test_native_fzopt_journal_repeat_and_preview_literal_identity(self):
        self.env.update(FIXTURE_ROOT=str(self.repo), FZF_DEFAULT_OPTS='--height=40% --prompt=fixture')
        items = self.base/'preview.json'
        items.write_text(json.dumps([dict(kind='text', preview='literal $(throw 1) ü')]))
        self.env.update(FIXTURE_PREVIEW=str(items), FIXTURE_PYTHON=sys.executable)
        result = self.run_ps(r'''
$first=& (Join-Path $env:FIXTURE_ROOT 'scripts/fzopt.ps1') write-rc; $one=$LASTEXITCODE
$second=& (Join-Path $env:FIXTURE_ROOT 'scripts/fzopt.ps1') write-rc; $two=$LASTEXITCODE
$env:PYTHONIOENCODING='utf-8'; [Console]::OutputEncoding=[Text.UTF8Encoding]::new($false)
$preview=& $env:FIXTURE_PYTHON -B (Join-Path $env:FIXTURE_ROOT 'lib/dots/utility_picker.py') preview $env:FIXTURE_PREVIEW 0
@{first=($first -join "`n"); second=($second -join "`n"); codes=@($one,$two); preview=($preview -join "`n")} | ConvertTo-Json -Compress
''')
        self.assertEqual(result.returncode, 0, result.stderr)
        values = json.loads(result.stdout)
        self.assertEqual(values['codes'], [0, 0])
        self.assertIn('Recovery transaction', values['first'])
        self.assertIn('unchanged', values['second'])
        self.assertEqual(values['preview'], 'literal $(throw 1) ü')
        self.assertEqual((self.home/'.fzfrc').read_text(), '--height=40%\n--prompt=fixture\n')


if __name__ == '__main__': unittest.main()
