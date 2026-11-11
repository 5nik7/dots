"""Wheel-only automatic Termux upgrades and RubyGems self-update plans."""
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import unittest
import venv
from unittest.mock import patch
import zipfile

import test_workflows as fixtures
from pkgs_lib import workflows, policies, scopes, streams
from pkgs_lib.backends import Backend
from pkgs_lib.common import Package


class Compatibility(unittest.TestCase):
    setUp=fixtures.Workflows.setUp

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
        with patch.object(scopes,'inventory',return_value=[]):
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
        with patch.object(scopes,'inventory',return_value=rows):item=workflows.plan(backend,'upgrade',[],cfg)
        self.assertEqual(item.commands,[['before'],['gem','update','rake'],['gem','update','--system','--no-document'],['after']])
        calls=[]
        with patch.object(streams,'run',side_effect=lambda cmd,*a,**k:calls.append(cmd) or (1 if '--system' in cmd else 0)):
            self.assertEqual(workflows.apply(item,cfg),1)
        self.assertNotIn(['after'],calls);self.assertFalse(any('sudo' in cmd or '--force' in cmd for cmd in calls))
        changed=workflows.changed_packages(item,{'rake':('rake','1'),'RubyGems':('RubyGems','1')},
                                          {'rake':('rake','2'),'RubyGems':('RubyGems','2')})
        self.assertEqual(changed,['rake','RubyGems'])
        policies.validate({'upgrade':{'gem_system':False}})

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
