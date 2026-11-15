#!/usr/bin/env python3
"""Fixture containment checks using only owned repositories and fake transports."""
import json
import os
from pathlib import Path
import shlex
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

import test_git_operations as operations


posix_transport = unittest.skipUnless(
    os.name == 'posix' and shutil.which('bash') and shutil.which('git'),
    'requires native POSIX Bash and Git for owned transport fixtures')


class GitFixture(unittest.TestCase):
    def fixture(self, ambient=None):
        fixture = operations.GitOperations()
        self.addCleanup(fixture.doCleanups)
        with patch.dict(os.environ, ambient or {}): fixture.setUp()
        return fixture

    @unittest.skipUnless(shutil.which('git'), 'requires native Git')
    def test_native_environment_and_local_git_config_are_contained(self):
        with tempfile.TemporaryDirectory(prefix='dots git native ambient ') as directory:
            ambient = Path(directory)
            config = ambient/'ambient.gitconfig'
            config.write_text('[user]\nname = Ambient Git Identity\n[protocol "https"]\nallow = always\n')
            templates = ambient/'templates'; templates.mkdir()
            marker = 'ambient-template-marker'
            (templates/marker).write_text('ambient template must not be inherited\n')
            (ambient/'sitecustomize.py').write_text(
                'from pathlib import Path\nPath(__file__).with_name("python-override-ran").write_text("ran")\n')
            unwanted = dict(PYTHONPATH=str(ambient), PYTHONHOME=str(ambient/'missing-python'),
                            SSH_AUTH_SOCK=str(ambient/'agent'), SSH_AGENT_PID='123', SSH_ASKPASS=str(ambient/'askpass'),
                            BASH_ENV=str(ambient/'startup'), ENV=str(ambient/'startup'),
                            GIT_CONFIG_GLOBAL=str(config), GIT_CONFIG_SYSTEM=str(config),
                            GIT_TEMPLATE_DIR=str(templates),
                            GIT_CONFIG_COUNT='1', GIT_CONFIG_KEY_0='user.name',
                            GIT_CONFIG_VALUE_0='Ambient Git Identity', GIT_EXEC_PATH=str(ambient),
                            GIT_SSH_COMMAND=str(ambient/'ssh'), GIT_ALLOW_PROTOCOL='https:ssh',
                            DOTS=str(ambient), DOTS_PROFILE='unexpected')
            fixture = self.fixture(unwanted)
            for key in ('PYTHONPATH','PYTHONHOME','SSH_AUTH_SOCK','SSH_AGENT_PID','SSH_ASKPASS',
                        'BASH_ENV','ENV','GIT_CONFIG_SYSTEM','GIT_EXEC_PATH','GIT_SSH_COMMAND','DOTS','DOTS_PROFILE'):
                self.assertNotIn(key,fixture.env)
            roots = ('HOME','USERPROFILE','APPDATA','LOCALAPPDATA','TMPDIR','TMP','TEMP',
                     'XDG_CONFIG_HOME','XDG_DATA_HOME','XDG_STATE_HOME','XDG_CACHE_HOME','XDG_RUNTIME_DIR',
                     'GIT_TEMPLATE_DIR')
            for key in roots:
                self.assertTrue(Path(fixture.env[key]).is_relative_to(fixture.base),key)
            owned_templates = Path(fixture.env['GIT_TEMPLATE_DIR'])
            self.assertEqual(owned_templates, fixture.base/'git-templates')
            self.assertTrue(owned_templates.is_dir())
            self.assertFalse(owned_templates.is_symlink())
            self.assertEqual(list(owned_templates.iterdir()), [])
            # Actual child observation, without isolated Python masking a leak.
            child = fixture.run_cmd([sys.executable,'-B','-c',
                'import json,os; print(json.dumps({key:os.environ.get(key) for key in '+
                repr((*roots,'GIT_ALLOW_PROTOCOL','GIT_CONFIG_GLOBAL'))+'}))'])
            values = json.loads(child.stdout)
            self.assertEqual(values,{key:fixture.env[key] for key in values})
            self.assertEqual(values['GIT_ALLOW_PROTOCOL'],'file')
            self.assertEqual(values['GIT_CONFIG_GLOBAL'],os.devnull)
            self.assertFalse((ambient/'python-override-ran').exists())
            repo = fixture.base/'local repo'; repo.mkdir()
            fixture.run_cmd(['git','init','-b','main',str(repo)])
            self.assertFalse((repo/'.git'/marker).exists())
            # Prove the inert poison would be copied if template isolation broke.
            control = fixture.base/'template control'
            fixture.run_cmd(['git','init','-b','main',str(control)],
                            env=dict(fixture.env, GIT_TEMPLATE_DIR=str(templates)))
            self.assertEqual((control/'.git'/marker).read_bytes(), (templates/marker).read_bytes())
            self.assertEqual(list(owned_templates.iterdir()), [])
            listing = fixture.run_cmd(['git','-C',str(repo),'config','--list','--show-origin']).stdout
            self.assertNotIn('Ambient Git Identity',listing)
            self.assertNotIn('protocol.https.allow',listing)
            global_name = fixture.run_cmd(['git','config','--global','--get','user.name'],ok=False)
            self.assertEqual(global_name.returncode,1)
            self.assertEqual(global_name.stdout,'')
            fixture.git(repo,'config','user.name','Owned Local Identity')
            self.assertEqual(fixture.git(repo,'config','--get','user.name'),'Owned Local Identity')
            self.assertIn('Git It Test <test@example.invalid>',fixture.git(repo,'var','GIT_AUTHOR_IDENT'))
            self.assertEqual(fixture.git(repo,'config','--get','protocol.file.allow'),'always')
            # Transport policy is inspected here, never exercised against a
            # network destination. POSIX cases below test refusal with fakes.

    @posix_transport
    def test_ambient_startup_agents_and_configuration_are_not_inherited(self):
        with tempfile.TemporaryDirectory(prefix='dots git ambient ') as directory:
            root = Path(directory)
            marker = root/'startup-ran'
            startup = root/'startup'
            startup.write_text('printf ran > '+shlex.quote(str(marker))+'\n')
            unwanted = dict(BASH_ENV=str(startup), ENV=str(startup), PYTHONPATH=str(root),
                            PYTHONHOME=str(root), SSH_AUTH_SOCK=str(root/'agent'), SSH_ASKPASS=str(startup),
                            SSH_AGENT_PID='123', GIT_SSH_COMMAND=str(startup), GIT_EXEC_PATH=str(root),
                            GIT_ALLOW_PROTOCOL='https:ssh', DOTS=str(root), DOTS_PROFILE='unexpected',
                            _DOTS_ROOT=str(root), ZDOTDIR=str(root))
            fixture = self.fixture(unwanted)
            for key in unwanted:
                if key != 'GIT_ALLOW_PROTOCOL': self.assertNotIn(key, fixture.env)
            self.assertEqual(fixture.env['GIT_ALLOW_PROTOCOL'],'file')
            command = [shutil.which('bash'),'--noprofile','--norc','-c',':']
            # The poison is real, but it can affect only this owned marker.
            fixture.run_cmd(command,env=dict(fixture.env,BASH_ENV=str(startup)))
            self.assertTrue(marker.is_file()); marker.unlink()
            fixture.run_cmd(command)
            self.assertFalse(marker.exists())
            for key in ('HOME','USERPROFILE','APPDATA','LOCALAPPDATA','TMPDIR','TMP','TEMP',
                        'XDG_CONFIG_HOME','XDG_DATA_HOME','XDG_STATE_HOME','XDG_CACHE_HOME','XDG_RUNTIME_DIR'):
                self.assertTrue(Path(fixture.env[key]).is_relative_to(fixture.base),key)

    @posix_transport
    def test_forbidden_transports_refuse_before_owned_helpers_execute(self):
        fixture = self.fixture()
        helpers = fixture.base/'helpers'; helpers.mkdir()
        marker = fixture.base/'transport-ran'
        script = '#!'+shutil.which('bash')+'\nprintf ran > '+shlex.quote(str(marker))+'\nexit 77\n'
        for name in ('git-remote-http','git-remote-https','fake-ssh'):
            helper = helpers/name; helper.write_text(script); helper.chmod(0o700)
        env = dict(fixture.env, GIT_EXEC_PATH=str(helpers),
                   GIT_SSH_COMMAND=shlex.quote(str(helpers/'fake-ssh')), GIT_SSH_VARIANT='ssh')
        for protocol in ('http','https','ssh'):
            command = ['git','ls-remote',protocol+'://fixture.invalid/owned']
            # Each control uses a fake helper: no real network provider can run.
            control = fixture.run_cmd(command,env=dict(env,GIT_ALLOW_PROTOCOL=protocol),ok=False)
            self.assertNotEqual(control.returncode,0)
            self.assertTrue(marker.exists(),protocol); marker.unlink()
            result = fixture.run_cmd(command,env=env,ok=False)
            self.assertEqual(result.returncode,128)
            self.assertFalse(marker.exists(),protocol)

    @posix_transport
    def test_owned_remote_enables_only_local_ssh_and_preserves_push(self):
        fixture = self.fixture()
        _, bare, repo = fixture.remote_repo('transport')
        self.assertEqual(fixture.env['GIT_ALLOW_PROTOCOL'],'file')
        self.assertNotIn('GIT_SSH_COMMAND',fixture.env)
        fixture.owned_remote(repo,bare)
        self.assertEqual(fixture.env['GIT_ALLOW_PROTOCOL'],'file:ssh')
        self.assertEqual(shlex.split(fixture.env['GIT_SSH_COMMAND']),[str(fixture.base/'ssh-test')])
        (repo/'selected').write_text('owned transport fixture\n')
        fixture.git(repo,'add','selected'); fixture.git(repo,'commit','-m','owned change')
        fixture.git(repo,'push','origin','HEAD:refs/heads/main')
        self.assertEqual(fixture.git(repo,'rev-parse','HEAD'),fixture.git(bare,'rev-parse','main'))


if __name__ == '__main__': unittest.main(verbosity=2)
