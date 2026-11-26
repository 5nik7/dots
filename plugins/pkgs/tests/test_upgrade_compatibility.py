"""Wheel-only automatic Termux upgrades and RubyGems self-update plans."""
import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import unittest
import venv
from unittest.mock import patch
import zipfile

import test_workflows as fixtures
from pkgs_lib import backends, common, workflows, policies, scopes, streams
from pkgs_lib.backends import Backend
from pkgs_lib.common import Error, Package

UV = shutil.which('uv')
RUBY = shutil.which('ruby')


class Compatibility(unittest.TestCase):
    setUp=fixtures.Workflows.setUp

    def test_termux_uv_automatic_wheels_and_explicit_native_overrides(self):
        backend=Backend('uv-tool');backend.termux=True
        rows=[(Package('example','1'), 'explicit','')]
        env={k:v for k,v in os.environ.items() if not k.upper().startswith('UV_')}
        with patch.dict(os.environ,env,clear=True), patch.object(scopes,'inventory',return_value=rows):
            self.assertEqual(workflows.plan(backend,'upgrade',[],self.cfg).commands,
                             [['uv','tool','upgrade','example','--no-build']])
            for action in ('install','upgrade'):
                self.assertNotIn('--no-build',workflows.plan(backend,action,['example'],self.cfg).commands[0])
            for key,value in (('UV_NO_BUILD','false'),('UV_NO_BUILD_PACKAGE','other'),
                              ('UV_NO_BINARY','true'),('UV_NO_BINARY_PACKAGE','example')):
                with self.subTest(env=key), patch.dict(os.environ,{key:value}):
                    self.assertNotIn('--no-build',workflows.plan(backend,'upgrade',[],self.cfg).commands[0])
            for flags in (['--no-binary'],['--no-binary-package=example'],['--no-build-package','other'],
                          ['--no-build'],['--build'],['--build-package','example']):
                for package in (False,True):
                    with self.subTest(flags=flags,package=package):
                        rule={'upgrade':{'flags':flags}}
                        cfg=dict(self.cfg,policies={'uv-tool':{'packages':{'example':rule}} if package else rule})
                        command=workflows.plan(backend,'upgrade',[],cfg).commands[0]
                        self.assertEqual(command,['uv','tool','upgrade','example',*flags])
            for package in (False,True):
                rule={'upgrade':{'replace':[['custom','{packages}']]}}
                cfg=dict(self.cfg,policies={'uv-tool':{'packages':{'example':rule}} if package else rule})
                self.assertEqual(workflows.plan(backend,'upgrade',[],cfg).commands,[['custom','example']])
            backend.termux=False
            self.assertEqual(workflows.plan(backend,'upgrade',[],self.cfg).commands,
                             [['uv','tool','upgrade','example']])

    @unittest.skipUnless(UV,'native uv unavailable')
    def test_native_uv_retains_compatible_dependencies_and_persists_no_build(self):
        wheels=self.home/'wheels ü';wheels.mkdir()
        def wheel(name,version,requires='',entry=False):
            path=wheels/f'{name}-{version}-py3-none-any.whl'
            info=f'{name}-{version}.dist-info/'
            with zipfile.ZipFile(path,'w') as z:
                z.writestr(info+'METADATA',f'Metadata-Version: 2.1\nName: {name}\nVersion: {version}\n'+requires+'\n')
                z.writestr(info+'WHEEL','Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n')
                z.writestr(info+'RECORD','')
                if entry:
                    z.writestr(name+'.py',f'def main():\n    print({version!r})\n')
                    z.writestr(info+'entry_points.txt',f'[console_scripts]\npkgs-fixture-tool = {name}:main\n')
            return path
        wheel('pkgs_fixture_native','1.0')
        wheel('pkgs_fixture_tool','1.0','Requires-Dist: pkgs-fixture-native==1.0\n',True)
        env={k:v for k,v in os.environ.items() if not k.upper().startswith(('UV_','PIP_'))}
        env.update(UV_TOOL_DIR=str(self.home/'tools'),UV_TOOL_BIN_DIR=str(self.home/'commands'),
                   UV_CACHE_DIR=str(self.home/'uv-cache'),UV_PYTHON_INSTALL_DIR=str(self.home/'pythons'),
                   UV_PYTHON_DOWNLOADS='never',UV_NO_CONFIG='1',UV_OFFLINE='1')
        def uv(*args,code=0):
            result=subprocess.run([UV,'tool',*args],cwd=self.home,env=env,capture_output=True,text=True,timeout=30)
            self.assertEqual(result.returncode,code,result.stdout+result.stderr)
            return result
        uv('install','--python',sys.executable,'--no-index','--find-links',str(wheels),'pkgs-fixture-tool')
        wheel('pkgs_fixture_tool','2.0','Requires-Dist: pkgs-fixture-native==2.0\n',True)
        marker=self.home/'uv-source-build-attempted'
        files={'pyproject.toml':'[build-system]\nrequires=[]\nbuild-backend="backend"\nbackend-path=["."]\n',
               'backend.py':f'from pathlib import Path\nPath({str(marker)!r}).touch()\nraise RuntimeError("no Android build")\n',
               'PKG-INFO':'Metadata-Version: 2.2\nName: pkgs-fixture-native\nVersion: 2.0\n'}
        with tarfile.open(wheels/'pkgs_fixture_native-2.0.tar.gz','w:gz') as tar:
            for name,text in files.items():
                payload=text.encode();info=tarfile.TarInfo('pkgs_fixture_native-2.0/'+name);info.size=len(payload)
                tar.addfile(info,io.BytesIO(payload))
        uv('upgrade','pkgs-fixture-tool','--no-build')
        self.assertIn('pkgs-fixture-tool v1.0',uv('list').stdout)
        receipt=self.home/'tools/pkgs-fixture-tool/uv-receipt.toml'
        self.assertIn('no-build = true',receipt.read_text())
        # Compatible future releases still upgrade; the saved build policy survives.
        wheel('pkgs_fixture_tool','3.0','Requires-Dist: pkgs-fixture-native==1.0\n',True)
        uv('upgrade','pkgs-fixture-tool')
        self.assertIn('pkgs-fixture-tool v3.0',uv('list').stdout)
        failed=uv('upgrade','pkgs-fixture-tool==2.0',code=1)
        self.assertIn('no usable wheels',failed.stderr)
        self.assertIn('pkgs-fixture-tool v3.0',uv('list').stdout)
        self.assertFalse(marker.exists())

    def test_termux_automatic_wheels_and_explicit_native_overrides(self):
        backend=Backend('pip');backend.termux=True
        rows=[(Package('example','1'), 'explicit','')]
        with patch.object(scopes,'inventory',return_value=rows):
            auto=workflows.plan(backend,'upgrade',[],self.cfg)
            self.assertIn('--only-binary=:all:',auto.commands[0])
            explicit=workflows.plan(backend,'upgrade',['example'],self.cfg)
            self.assertNotIn('--only-binary=:all:',explicit.commands[0])
            cfg=dict(self.cfg,policies={'pip':{'upgrade':{'flags':['--no-binary=example']}}})
            custom=workflows.plan(backend,'upgrade',[],cfg)
            self.assertNotIn('--only-binary=:all:',custom.commands[0])
            self.assertIn('--no-binary=example',custom.commands[0])
            with patch.dict(os.environ,PIP_NO_BINARY='example'):
                self.assertNotIn('--only-binary=:all:',workflows.plan(backend,'upgrade',[],self.cfg).commands[0])
            backend.termux=False
            self.assertNotIn('--only-binary=:all:',workflows.plan(backend,'upgrade',[],self.cfg).commands[0])

    def test_rubygems_runs_with_empty_inventory_and_has_truthful_updated_identity(self):
        backend=Backend('gem')
        with patch.object(scopes,'inventory',return_value=[]), patch.object(backend,'gem_system_update_disabled',return_value=False):
            item=workflows.plan(backend,'upgrade',[],self.cfg)
        self.assertEqual(item.commands,[['gem','update','--system','--no-document']])
        with patch.object(backend,'installed',return_value=[]),patch('pkgs_lib.common.run',side_effect=['4.0.1','4.0.2']), \
             patch.object(streams,'run',return_value=0) as run,contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(workflows.apply_compact(item,self.cfg),0)
        self.assertIn('Updated: RubyGems',out.getvalue());self.assertEqual(run.call_count,1)
        with patch.object(scopes,'inventory',return_value=[]):
            disabled=workflows.plan(backend,'upgrade',[],dict(self.cfg,upgrade={'gem_system':False}))
        self.assertEqual(disabled.commands,[])
        explicit=workflows.plan(backend,'upgrade',['rake'],self.cfg)
        self.assertEqual(explicit.commands,[['gem','update','rake']])

    def test_gem_recipe_boundaries_native_protections_and_version_selection(self):
        backend=Backend('gem'); rows=[(Package('rake','1'),'all','')]
        cfg=dict(self.cfg,policies={'gem':{'upgrade':{'before':[['before']], 'after':[['after']]}}})
        with patch.object(scopes,'inventory',return_value=rows), patch.object(backend,'gem_system_update_disabled',return_value=False):
            item=workflows.plan(backend,'upgrade',[],cfg)
        self.assertEqual(item.commands,[['before'],['gem','update','rake'],['gem','update','--system','--no-document'],['after']])
        calls=[]
        with patch.object(streams,'run',side_effect=lambda cmd,*a,**k:calls.append(cmd) or (1 if '--system' in cmd else 0)):
            self.assertEqual(workflows.apply(item,cfg),1)
        self.assertNotIn(['after'],calls);self.assertFalse(any('sudo' in cmd or '--force' in cmd for cmd in calls))
        changed=workflows.changed_packages(item,{'rake':('rake','1'),'RubyGems':('RubyGems','1')},
                                          {'rake':('rake','2'),'RubyGems':('RubyGems','2')})
        self.assertEqual(changed,['rake','RubyGems'])
        policies.validate({'upgrade':{'gem_system':False}})

    def test_disabled_self_update_skips_only_rubygems(self):
        backend = Backend('gem')
        cfg = dict(self.cfg, policies={'gem': {'upgrade': {'before': [['before']], 'after': [['after']]}}})
        rows = [(Package('rake', '1'), 'all', '')]
        with patch.object(backend, 'gem_system_update_disabled', return_value=True), patch.object(scopes, 'inventory', return_value=rows):
            item = workflows.plan(backend, 'upgrade', [], cfg)
            self.assertEqual(item.commands, [['before'], ['gem', 'update', 'rake'], ['after']])
            self.assertEqual(item.skipped, [{'package': 'RubyGems', 'reason': 'This RubyGems installation disables self-updates.'}])
            with patch.object(backend, 'installed', side_effect=[[Package('rake', '1')], [Package('rake', '2')]]), \
                 patch('pkgs_lib.common.run', side_effect=AssertionError('unexpected RubyGems version query')), \
                 patch.object(streams, 'run', return_value=0), contextlib.redirect_stdout(io.StringIO()) as out:
                self.assertEqual(workflows.apply_compact(item, cfg), 0)
            self.assertIn('Updated: rake', out.getvalue())
            rows.clear()
            empty = workflows.plan(backend, 'upgrade', [], cfg)
        self.assertEqual(empty.commands, [])
        self.assertEqual(empty.skipped, item.skipped)

    def test_rubygems_probe_is_limited_to_automatic_native_self_update(self):
        backend = Backend('gem')
        rows = [(Package('rake', '1'), 'all', '')]
        self_update = ['gem', 'update', '--system', '--no-document']
        replacement = dict(self.cfg, policies={'gem': {'upgrade': {'replace': [self_update]}}})
        disabled = dict(self.cfg, upgrade={'gem_system': False})
        cases = [
            ('upgrade', [], disabled, [['gem', 'update', 'rake']]),
            ('upgrade', ['rake'], self.cfg, [['gem', 'update', 'rake']]),
            ('upgrade', [], replacement, [self_update]),
            ('install', ['rake'], self.cfg, [['gem', 'install', 'rake']]),
        ]
        with patch.object(scopes, 'inventory', return_value=rows), \
             patch.object(backend, 'gem_system_update_disabled', side_effect=AssertionError('unexpected policy probe')):
            for action, names, cfg, expected in cases:
                with self.subTest(action=action, names=names, cfg=cfg):
                    self.assertEqual(workflows.plan(backend, action, names, cfg).commands, expected)

    def test_self_update_guard_requires_positive_evidence_from_selected_ruby(self):
        backend = Backend('gem')
        backend.operation_env = {'GEM_HOME': str(self.home/'user gems'), 'GEM_PATH': str(self.home/'user gems')}
        ruby = self.bin/'Ruby Installer ü'/'ruby.exe'
        ruby.parent.mkdir()
        ruby.touch()
        ruby.chmod(0o755)
        environment = 'RubyGems Environment:\n  - RUBY EXECUTABLE: "' + str(ruby) + '"\n'
        def result(stdout, status=0):
            return subprocess.CompletedProcess([], status, stdout, '')

        for policy, disabled in [(result('blocked\n'), True), (result('allowed\n'), False),
                                 (result('blocked\nextra\n'), False), (result('blocked', 1), False),
                                 (Error('query timed out'), False)]:
            with self.subTest(policy=policy), patch.object(backends, 'query', side_effect=[result(environment), policy]) as probe:
                self.assertEqual(backend.gem_system_update_disabled(), disabled)
                first, second = probe.call_args_list
                self.assertEqual(first.args[0], ['gem', 'environment'])
                self.assertEqual(second.args[0][:-1], [str(ruby), '-rrubygems', '-e'])
                self.assertIn('Gem.disable_system_update_message', second.args[0][-1])
                self.assertEqual(first.kwargs['env'], backend.operation_env)
                self.assertEqual(second.kwargs['env'], backend.operation_env)
        invalid = [result(environment, 1), result(''), result('  - RUBY EXECUTABLE: ruby\n'),
                   result(environment + environment), Error('gem unavailable')]
        for response in invalid:
            with self.subTest(response=response), patch.object(backends, 'query', side_effect=[response]) as probe:
                self.assertFalse(backend.gem_system_update_disabled())
                probe.assert_called_once()

    @unittest.skipUnless(RUBY, 'native Ruby unavailable')
    def test_native_ruby_guard_handles_missing_accessor_and_message_values(self):
        backend = Backend('gem')
        def fixture_query(command, *, env):
            if command == ['gem', 'environment']:
                report = '  - RUBY EXECUTABLE: ' + RUBY
                return subprocess.CompletedProcess(command, 0, report, '')
            self.assertEqual(command[0], RUBY)
            # Load our RubyGems stub before any host RubyGems library.
            return common.query([RUBY, '--disable-gems', '-I', str(self.home), *command[1:]],
                                env={'RUBYLIB': '', 'RUBYOPT': ''})

        with patch.object(backends, 'query', side_effect=fixture_query):
            for value, disabled in [(None, False), ('nil', False), ('false', False),
                                    ('""', True), ('"Updated by APT"', True)]:
                method = '' if value is None else f'def self.disable_system_update_message\n{value}\nend'
                (self.home/'rubygems.rb').write_text('module Gem\n' + method + '\nend\n')
                with self.subTest(value=value):
                    self.assertEqual(backend.gem_system_update_disabled(), disabled)

    @unittest.skipIf(os.name == 'nt', 'fake Termux gem uses a POSIX executable')
    def test_compact_bundler_permission_diagnostics_follow_native_step_and_status(self):
        ruby = self.bin/'fixture ruby'
        ruby.write_text('#!'+sys.executable+'\nimport sys\nassert "disable_system_update_message" in sys.argv[-1]\nprint("allowed")\n')
        ruby.chmod(0o755)
        gem = self.bin/'gem'
        gem.write_text('#!'+sys.executable+'\n'+'''import os, sys
from pathlib import Path
args = sys.argv[1:]
if args == ['environment']: print('  - RUBY EXECUTABLE: ' + str(Path(__file__).with_name('fixture ruby'))); sys.exit(0)
if args == ['list', '--local']: sys.exit(0)
if args == ['--version']: print('4.1.1'); sys.exit(0)
if args == ['hook']: print('error: after-hook failed', file=sys.stderr); sys.exit(29)
if args == ['silent-hook']: sys.exit(29)
files = ['MIT.txt', 'bundler.gemspec', 'exe/bundle', 'lib/bundler.rb', 'lib/bundler/man/.document']
files += [f'lib/bundler/tool_{i}.rb' for i in range(340)]
if os.environ.get('GEM_TEST_OTHER_PATH'):
    print('WARNING:  lib/other_tool.rb is not world-readable', file=sys.stderr)
for name in files: print('WARNING:  '+name+' is not world-readable', file=sys.stderr)
if os.environ.get('GEM_TEST_MIXED'):
    print('WARNING:  exe/bundle is not executable', file=sys.stderr)
print('WARNING:  See https://guides.rubygems.org/specification-reference/ for help', file=sys.stderr)
if os.environ.get('GEM_TEST_FAIL'):
    print('ERROR:  installation directory is not writable', file=sys.stderr)
    sys.exit(27)
print('RubyGems system software updated')
''')
        gem.chmod(0o755)
        path = self.home/'config/pkgs/config.json'
        path.parent.mkdir(parents=True)
        native = ['gem', 'update', '--system', '--no-document']

        def invoke(*args, output='styled', recipe=None, termux=True, **env):
            path.write_text(json.dumps({'output':output, 'policies':{'gem':{'upgrade':recipe or {}}}}))
            # A Termux host can place even the fixture directory beneath /com.termux/.
            if not termux: env.update(HOME=os.path.relpath(self.home), PREFIX=os.path.relpath(self.home))
            with patch.dict(os.environ, TERMUX_VERSION='fixture' if termux else '', **env):
                return fixtures.Workflows.invoke(self, 'up', '--manager', 'gem', *args)

        success = invoke()
        self.assertEqual(success.returncode, 0, success.stderr)
        self.assertIn('complete', success.stdout)
        self.assertEqual(success.stderr, '')

        mixed = invoke(GEM_TEST_MIXED='1')
        self.assertEqual(mixed.returncode, 0, mixed.stderr)
        self.assertIn('is not executable', mixed.stderr)
        self.assertIn('specification-reference', mixed.stderr)
        self.assertNotIn('world-readable', mixed.stderr)
        self.assertNotIn('more diagnostic lines', mixed.stderr)
        other_path = invoke(GEM_TEST_OTHER_PATH='1')
        self.assertEqual(other_path.returncode, 0, other_path.stderr)
        self.assertIn('lib/other_tool.rb is not world-readable', other_path.stderr)
        self.assertIn('specification-reference', other_path.stderr)
        self.assertNotIn('MIT.txt', other_path.stderr)

        failure = invoke(GEM_TEST_FAIL='1')
        self.assertEqual(failure.returncode, 27, failure.stderr)
        self.assertIn('installation directory is not writable', failure.stderr)
        self.assertIn('MIT.txt is not world-readable', failure.stderr)
        self.assertLessEqual(len(failure.stderr.splitlines()), 4)
        hook = invoke(recipe={'after':[['gem','hook']]})
        self.assertEqual(hook.returncode, 29, hook.stderr)
        self.assertIn('after-hook failed', hook.stderr)
        self.assertNotIn('world-readable', hook.stderr)
        self.assertNotIn('more diagnostic lines', hook.stderr)
        silent = invoke(recipe={'after':[['gem','silent-hook']]})
        self.assertEqual(silent.returncode, 29, silent.stderr)
        self.assertEqual(silent.stderr, '')

        for route, unchanged in [('named', invoke('rake')), ('linux', invoke(termux=False)),
                                 ('replace', invoke('rake', recipe={'replace':[native]})),
                                 ('before', invoke(recipe={'before':[native]}))]:
            with self.subTest(route=route):
                self.assertEqual(unchanged.returncode, 0, unchanged.stderr)
                self.assertIn('MIT.txt is not world-readable', unchanged.stderr, unchanged.stdout)
                self.assertIn('344 more diagnostic lines', unchanged.stderr)
        for full in (invoke('--raw'), invoke(output='auto')):
            self.assertEqual(full.returncode, 0, full.stderr)
            self.assertEqual(full.stderr.count('is not world-readable'), 345)
            self.assertIn('specification-reference', full.stderr)

    def test_native_pip_retains_compatible_version_without_executing_source_backend(self):
        root=self.home/'isolated python';venv.EnvBuilder(with_pip=True).create(root)
        python=root/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
        wheels=self.home/'wheels';wheels.mkdir()
        def wheel(version,requires=''):
            path=wheels/f'pkgs_fixture_binary-{version}-py3-none-any.whl'
            info=f'pkgs_fixture_binary-{version}.dist-info/'
            with zipfile.ZipFile(path,'w') as z:
                z.writestr(info+'METADATA',f'Metadata-Version: 2.1\nName: pkgs-fixture-binary\nVersion: {version}\n'+requires+'\n')
                z.writestr(info+'WHEEL','Wheel-Version: 1.0\nGenerator: fixture\nRoot-Is-Purelib: true\nTag: py3-none-any\n')
                z.writestr(info+'RECORD','')
            return path
        old=wheel('1.0');wheel('2.0','Requires-Dist: pkgs-fixture-rust>=1\n')
        marker=self.home/'source-build-attempted'
        files={'pyproject.toml':'[build-system]\nrequires=[]\nbuild-backend="backend"\nbackend-path=["."]\n',
               'backend.py':f'from pathlib import Path\nPath({str(marker)!r}).touch()\nraise RuntimeError("no Android build")\n'}
        with tarfile.open(wheels/'pkgs_fixture_rust-1.0.tar.gz','w:gz') as tar:
            for name,text in files.items():
                payload=text.encode();info=tarfile.TarInfo('pkgs_fixture_rust-1.0/'+name);info.size=len(payload)
                tar.addfile(info,io.BytesIO(payload))
        env=dict(os.environ,PIP_CONFIG_FILE=os.devnull,PIP_DISABLE_PIP_VERSION_CHECK='1',PIP_NO_CACHE_DIR='1')
        def pip(*args):
            result=subprocess.run([str(python),'-m','pip',*args],cwd=self.home,env=env,capture_output=True,text=True,timeout=45)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr);return result
        pip('install','--no-index',str(old))
        pip('install','--no-index','--find-links',str(wheels),'--only-binary=:all:','--upgrade','pkgs-fixture-binary')
        installed=json.loads(pip('list','--format=json').stdout)
        self.assertEqual(next(p['version'] for p in installed if p['name']=='pkgs-fixture-binary'),'1.0')
        self.assertFalse(marker.exists())


if __name__=='__main__':unittest.main()
