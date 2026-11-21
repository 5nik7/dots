#!/usr/bin/env python3
"""Disposable native setup, updater and restore acceptance tests."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from vivid_fixture import install_vivid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'lib/dots/files'))
from install import Installation
from transactions import Store, digest


class InstallationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='dots setup ü ')
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.home = self.base/'home'
        self.repo = self.base/'checkout'
        self.home.mkdir()
        for name in ('.dots', 'bin', 'config/example'):
            (self.repo/name).mkdir(parents=True)
        (self.repo/'bin/dots').write_text('#!/bin/sh\nexit 0\n')
        (self.repo/'bin/dots.ps1').write_text('exit 0\n')
        self.source = self.repo/'config/example/settings'
        self.source.write_text('repository settings\n')
        self.target = self.home/'.config/example/settings'
        self.env = dict(os.environ, HOME=str(self.home), USERPROFILE=str(self.home),
                        DOTS=str(self.repo), XDG_CONFIG_HOME=str(self.home/'.config'),
                        XDG_STATE_HOME=str(self.home/'.state'), LOCALAPPDATA=str(self.home/'Local'),
                        APPDATA=str(self.home/'Roaming'), DOTS_COLOR='never', DOTS_ICONS='never',
                        TERM='dumb', PYTHONDONTWRITEBYTECODE='1', GIT_CONFIG_GLOBAL=os.devnull,
                        GIT_CONFIG_NOSYSTEM='1', GIT_TERMINAL_PROMPT='0')
        self.env.update(CODEX_HOME=str(self.home/'.codex'), PI_CODING_AGENT_DIR=str(self.home/'.pi/agent'),
                        XDG_CACHE_HOME=str(self.home/'.cache'), XDG_DATA_HOME=str(self.home/'.data'))
        for key in ('EZA_CONFIG_DIR', 'DOTS_APP_EZA_CONFIG', 'TELEVISION_CONFIG', 'DOTS_APP_TELEVISION_CONFIG', 'DOTS_APP_LEAF_CONFIG'):
            self.env.pop(key, None)
        self.write('.dots/sources.json', {'schema':1,'sources':[dict(id='dots',path='.',roots=['config','bin'],platforms=['termux','linux','wsl','windows'])]})
        self.write('.dots/files.json', {'schema':1,'repository':'dots','resources':[dict(id='example',source='config/example/settings',target='${CONFIG}/example/settings',strategy='link',app='example',category='config',platforms=['termux','linux','wsl','windows'])]})
        # Native Windows positive cases require explicit link capability.
        if os.name == 'nt':
            probe = self.base/'probe'
            try:
                probe.symlink_to(self.source)
                probe.unlink()
            except OSError:
                self.skipTest('native Windows symbolic links unavailable; refusal tested separately')

    def write(self, name, data):
        (self.repo/name).write_text(json.dumps(data))

    def cli(self, *args, ok=True):
        result = subprocess.run([sys.executable,'-B',str(ROOT/'lib/dots/files/install.py'),*args],env=self.env,
                                input='',capture_output=True,text=True,timeout=90)
        if ok:
            self.assertEqual(result.returncode,0,result.stderr+'\n'+result.stdout)
        else:
            self.assertNotEqual(result.returncode,0,result.stdout)
        return result

    def receipt(self):
        return json.loads((self.home/'.state/dots/installation.json').read_text())

    def yazi_profile(self):
        scoped = mock.patch.dict(os.environ, self.env, clear=True)
        scoped.start()
        self.addCleanup(scoped.stop)
        from catalog import platform
        selected = platform()
        self.write('.dots/files.json', dict(schema=3, resources=[], renames={}))
        profiles = self.repo/'profiles'/selected
        profiles.mkdir(parents=True)
        rows = [dict(id='yazi', app='yazi', category='config', strategy='directory-link',
                     source='${DOTS}/config/yazi', target='${CONFIG}/yazi'),
                dict(id='yazi', app='yazi', category='theme', strategy='directory-link',
                     source='${THEME}/yazi', target='${CONFIG}/yazi/flavors/dots.yazi')]
        self.write('profiles/'+selected+'/profile.json', dict(schema=1, id=selected, files=rows))
        self.state = Installation(self.repo).state
        self.active = self.state/'current/theme'
        generation = self.state/'themes/generations/g.check'
        (generation/'yazi').mkdir(parents=True)
        for name in ('flavor.toml','tmtheme.xml'):
            (generation/'yazi'/name).write_text('published '+name)
        (generation/'status').write_text('committed\n')
        (self.state/'themes/current').write_text(generation.name+'\n')
        self.active.parent.mkdir()
        self.active.symlink_to(generation,target_is_directory=True)
        config = self.repo/'config/yazi'
        (config/'flavors').mkdir(parents=True)
        self.flavor = config/'flavors/dots.yazi'
        live = self.home/'.config/yazi'
        live.parent.mkdir()
        live.symlink_to(config, target_is_directory=True)
        self.logical_flavor = live/'flavors/dots.yazi'

    def yazi_action(self, action):
        preview = Installation(self.repo)
        getattr(preview, 'plan_'+action)({'files'}, {'theme:yazi'})
        return preview.apply(action)

    def test_yazi_migrate_child_receipts_and_restore_original_payloads(self):
        self.yazi_profile()
        from backup_catalog import BackupPlan
        self.flavor.mkdir(mode=0o750)
        original_mode = self.flavor.stat().st_mode & 0o777
        flavor, syntax = self.flavor/'flavor.toml', self.flavor/'tmtheme.xml'
        flavor.write_text('my original flavor')
        legacy = Installation(self.repo)
        legacy.add('theme:yazi-flavor', flavor, link=self.active/'yazi/flavor.toml')
        legacy.add('theme:yazi-syntax', syntax, link=self.active/'yazi/tmtheme.xml')
        legacy.apply('install')
        # Real old receipts may spell a child via its app directory link.
        doc = self.receipt()
        doc['entries'][str(self.logical_flavor/flavor.name)] = doc['entries'].pop(str(flavor))
        legacy.receipt_path.write_text(json.dumps(doc))
        before = digest(self.flavor)
        first_id = doc['entries'][str(self.logical_flavor/flavor.name)]['backup_id']
        result = self.yazi_action('install')
        self.assertEqual(self.flavor.readlink(), self.active/'yazi')
        self.assertEqual(set(self.receipt()['entries']), {str(self.flavor)})
        with self.assertRaisesRegex(ValueError, 'no separate uninstall receipt'):
            Installation(self.repo).plan_uninstall({'files','themes'}, {'theme:yazi-flavor'})
        self.assertIn(first_id, BackupPlan(self.state).protected())
        with self.assertRaisesRegex(ValueError, 'required for uninstall'):
            BackupPlan(self.state).delete([first_id])
        self.assertEqual(self.yazi_action('install')['status'], 'unchanged')
        store = Store(self.state)
        inverse, guards, catalogs = store.inverse(result['id'])
        store.apply('undo', inverse, guards, catalogs=catalogs, retain=True)
        self.assertEqual(digest(self.flavor), before)
        self.assertEqual(self.receipt(), doc)
        self.yazi_action('install')
        self.yazi_action('uninstall')
        self.assertFalse(self.flavor.is_symlink())
        self.assertEqual(self.flavor.stat().st_mode & 0o777, original_mode)
        self.assertEqual(flavor.read_text(), 'my original flavor')
        self.assertFalse(syntax.exists())
        self.assertNotIn(first_id, BackupPlan(self.state).protected())
        self.assertFalse(self.receipt()['entries'])

    def test_yazi_partially_owned_split_restores_relative_unowned_link(self):
        self.yazi_profile()
        self.flavor.mkdir()
        foreign = self.flavor/'tmtheme.xml'
        spelling = os.path.relpath(self.active/'yazi/tmtheme.xml', self.flavor)
        foreign.symlink_to(spelling)
        owner = Installation(self.repo)
        owner.add('theme:yazi-flavor', self.flavor/'flavor.toml', link=self.active/'yazi/flavor.toml')
        owner.apply('install')
        self.yazi_action('install')
        self.yazi_action('uninstall')
        self.assertEqual(list(self.flavor.iterdir()), [foreign])
        self.assertEqual(os.readlink(foreign), spelling)

    def test_yazi_setup_created_split_is_removed_and_observed_link_stays_unowned(self):
        self.yazi_profile()
        legacy = Installation(self.repo)
        for name, identity in [('flavor.toml','theme:yazi-flavor'), ('tmtheme.xml','theme:yazi-syntax')]:
            legacy.add(identity, self.flavor/name, link=self.active/'yazi'/name)
        legacy.apply('install')
        receipt = legacy.receipt_path.read_bytes()
        damaged = json.loads(receipt)
        damaged['entries'][str(self.flavor/'tmtheme.xml')]['backup'] = '0'*32
        legacy.receipt_path.write_text(json.dumps(damaged))
        with self.assertRaisesRegex(ValueError, 'original setup transaction is missing'):
            self.yazi_action('install')
        self.assertFalse(self.flavor.is_symlink())
        legacy.receipt_path.write_bytes(receipt)
        self.yazi_action('install')
        self.yazi_action('uninstall')
        self.assertFalse(os.path.lexists(self.flavor))
        self.flavor.symlink_to(os.path.relpath(self.active/'yazi', self.flavor.parent), target_is_directory=True)
        self.assertEqual(self.yazi_action('install')['status'], 'unchanged')
        self.assertFalse(self.receipt()['entries'])
        self.assertEqual(self.yazi_action('uninstall')['status'], 'unchanged')
        self.assertTrue(self.flavor.is_symlink())

    def test_yazi_unowned_split_and_previous_grouped_parent_restore_first_baseline(self):
        self.yazi_profile()
        self.flavor.mkdir()
        for name in ('flavor.toml','tmtheme.xml'):
            (self.flavor/name).symlink_to(self.active/'yazi'/name)
        before = digest(self.flavor)
        self.yazi_action('install')
        self.yazi_action('uninstall')
        self.assertEqual(digest(self.flavor), before)
        for child in self.flavor.iterdir():
            child.unlink()
        self.flavor.rmdir()
        self.flavor.symlink_to(self.active/'yazi', target_is_directory=True)
        legacy = Installation(self.repo)
        legacy.add('theme:yazi', self.flavor, managed=True, yazi_pair=True)
        legacy.entries[str(self.flavor)]['catalog_ids'] = ['theme:yazi-flavor', 'theme:yazi-syntax']
        legacy.apply('install')
        oldest = self.receipt()['entries'][str(self.flavor)]
        self.yazi_action('install')
        now = self.receipt()['entries'][str(self.flavor)]
        self.assertEqual([now[k] for k in ('before','backup','index','backup_id')],
                         [oldest[k] for k in ('before','backup','index','backup_id')])
        self.assertEqual(now['catalog_ids'], ['theme:yazi'])
        self.yazi_action('uninstall')
        self.assertEqual(self.flavor.readlink(), self.active/'yazi')

    def test_yazi_refuses_unexpected_files_and_missing_first_backup(self):
        self.yazi_profile()
        self.flavor.mkdir()
        flavor = self.flavor/'flavor.toml'
        flavor.write_text('original')
        syntax = self.flavor/'tmtheme.xml'
        syntax.symlink_to(self.active/'yazi/tmtheme.xml')
        legacy = Installation(self.repo)
        legacy.add('theme:yazi-flavor', flavor, link=self.active/'yazi/flavor.toml')
        legacy.apply('install')
        before = self.receipt()
        extra = self.flavor/'README'
        extra.write_text('local edits')
        with self.assertRaisesRegex(ValueError, 'preserve and review'):
            self.yazi_action('install')
        self.assertEqual(extra.read_text(), 'local edits')
        extra.unlink()
        syntax.unlink()
        syntax.write_text('edited syntax')
        with self.assertRaisesRegex(ValueError, 'preserve and review'):
            self.yazi_action('install')
        self.assertEqual(syntax.read_text(), 'edited syntax')
        syntax.unlink()
        syntax.symlink_to(self.active/'yazi/tmtheme.xml')
        from backup_catalog import BackupPlan
        catalog = BackupPlan(self.state)
        payload = catalog.verified_payload(catalog.entry(before['entries'][str(flavor)]['backup_id']))
        payload.write_text('damaged backup')
        with self.assertRaisesRegex(ValueError, 'backup is missing or changed'):
            self.yazi_action('install')
        self.assertEqual(self.receipt(), before)
        self.assertFalse(self.flavor.is_symlink())

    @unittest.skipUnless(os.name == 'nt', 'native Windows restart argv and status')
    def test_source_restart_preserves_literal_arguments_and_child_status(self):
        entry = self.repo/'lib/dots/files/install.py'
        entry.parent.mkdir(parents=True)
        entry.write_text('import json,sys\nprint(json.dumps(sys.argv[1:]))\nprint("child diagnostic",file=sys.stderr)\nsys.exit(47)\n')
        arguments = ['install','--update','--with-source','nvim','--with-source=windows',
                     '--yes','--json','--resource','literal "雪"', '--resource','', '--resource=-dash']
        code = '''
import sys
from unittest.mock import patch
sys.path.insert(0, sys.argv[1])
import install
with patch.object(install, 'source_plan', return_value=[{}]), patch.object(install, 'update_sources'):
    sys.exit(install.main(sys.argv[2:]))
'''
        result = subprocess.run([sys.executable,'-B','-c',code,str(ROOT/'lib/dots/files'),*arguments],
                                env=self.env,stdin=subprocess.DEVNULL,capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode, 47, result.stderr)
        self.assertEqual(json.loads(result.stdout), ['install','--yes','--json','--resource',
            'literal "雪"','--resource','','--resource=-dash'])
        self.assertIn('child diagnostic', result.stderr)
        self.assertEqual(list(self.home.iterdir()), [])

    def test_dry_run_and_idempotent_install_restore(self):
        before = list(self.home.rglob('*'))
        plan = json.loads(self.cli('install','--dry-run','--json').stdout)
        self.assertEqual(plan['status'],'preview')
        self.assertEqual(list(self.home.rglob('*')),before)
        self.cli('install','--yes')
        self.assertTrue(self.target.is_symlink())
        first = self.receipt()
        self.assertEqual(json.loads(self.cli('install','--yes','--json').stdout)['status'],'unchanged')
        self.assertEqual(first,self.receipt())
        self.cli('uninstall','--yes')
        self.assertFalse(self.target.exists())
        self.assertFalse((self.home/'.config').exists())
        self.assertTrue(self.source.exists())
        self.assertFalse(self.receipt()['entries'])

    def test_fonts_command_install_and_restore(self):
        for name in ('fonts', 'fonts.ps1'):
            shutil.copy2(ROOT/'bin'/name, self.repo/'bin'/name)
        with mock.patch.dict(os.environ, self.env), mock.patch('install.platform', return_value='windows'):
            native = Installation(self.repo)
            native.plan_install()
            operation = next(op for op in native.operations if Path(op['path']).name == 'fonts.ps1')
            self.assertIn(str(self.repo/'bin/fonts.ps1').replace("'", "''"), operation['text'])
            self.assertNotIn('bash', operation['text'])
        name = 'fonts.ps1' if os.name == 'nt' else 'fonts'
        command = self.home/'.local/bin'/name
        command.parent.mkdir(parents=True)
        command.write_text('Previous fonts command\n')
        self.cli('install', '--yes')
        if os.name != 'nt': self.assertEqual(command.resolve(), self.repo/'bin/fonts')
        self.assertEqual(json.loads(self.cli('install','--yes','--json').stdout)['status'],'unchanged')
        self.cli('uninstall','--yes')
        self.assertEqual(command.read_text(),'Previous fonts command\n')

    def test_codex_usage_core_launcher_lifecycle(self):
        (self.repo/'scripts').mkdir()
        for name in ('codex-usage', 'codex-usage.ps1'):
            shutil.copy2(ROOT/'scripts'/name, self.repo/'scripts'/name)
        with mock.patch.dict(os.environ, self.env), mock.patch('install.platform', return_value='windows'):
            native = Installation(self.repo)
            native.plan_install(components=['core'])
            launcher = next(op for op in native.operations if Path(op['path']).name == 'codex-usage.ps1')
            self.assertIn(str(self.repo/'scripts/codex-usage.ps1').replace("'", "''"), launcher['text'])
        name = 'codex-usage.ps1' if os.name == 'nt' else 'codex-usage'
        target = self.home/'.local/bin'/name
        self.cli('install', '--component', 'core', '--yes')
        self.assertTrue(target.is_file())
        if os.name != 'nt':
            self.assertEqual(target.resolve(), self.repo/'scripts'/name)
        self.assertEqual(json.loads(self.cli('install', '--component', 'core', '--yes', '--json').stdout)['status'], 'unchanged')
        self.cli('uninstall', '--component', 'core', '--yes')
        self.assertFalse(target.exists())

    def test_todo_command_and_skill_lifecycle(self):
        for name in ('todo', 'todo.ps1'):
            shutil.copy2(ROOT/'bin'/name, self.repo/'bin'/name)
        names = {'todo-skill': 'dots-todo', 'todo-planning-skill': 'dots-todo-planning',
                 'todo-maintenance-skill': 'dots-todo-maintenance'}
        definitions = []
        for platform in ('termux', 'linux', 'wsl', 'windows'):
            profile = json.loads((ROOT/'profiles'/platform/'profile.json').read_text())
            resources = [dict(r, source=r['source'].removeprefix('${DOTS}/')) for r in profile['files']
                         if r['id'] in names and r['source'].startswith('${DOTS}/')]
            self.assertEqual({r['id'] for r in resources}, set(names))
            if definitions: self.assertEqual(resources, definitions)
            definitions = resources
        registry = {row['id']:row['platforms'] for row in json.loads((ROOT/'.dots/files.json').read_text())['resources']}
        definitions = [dict(row,platforms=registry['dots:'+row['id']]) for row in definitions]
        for name in names.values():
            shutil.copytree(ROOT/'.codex/skills'/name, self.repo/'.codex/skills'/name)
        sources = json.loads((self.repo/'.dots/sources.json').read_text())
        sources['sources'][0]['roots'].extend('.codex/skills/' + name for name in names.values())
        self.write('.dots/sources.json', sources)
        catalog = json.loads((self.repo/'.dots/files.json').read_text())
        catalog['resources'].extend(definitions)
        self.write('.dots/files.json', catalog)
        project_goals = self.repo/'.dots/todo.json'
        project_goals.write_text('{"schema": 1, "goals": []}\n')
        global_goals = self.home/'.state/dots/todo/global.json'
        global_goals.parent.mkdir(parents=True)
        global_goals.write_text('{"schema": 1, "goals": []}\n')
        with mock.patch.dict(os.environ, self.env), mock.patch('install.platform', return_value='windows'):
            native = Installation(self.repo)
            native.plan_install()
            operation = next(op for op in native.operations if Path(op['path']).name == 'todo.ps1')
            self.assertIn(str(self.repo/'bin/todo.ps1').replace("'", "''"), operation['text'])
            self.assertNotIn('bash', operation['text'])
            for name in names.values():
                self.assertTrue(any(Path(op['path']).name == name for op in native.operations))
        name = 'todo.ps1' if os.name == 'nt' else 'todo'
        command = self.home/'.local/bin'/name
        command.parent.mkdir(parents=True)
        command.write_text('Original command\n')
        original = self.home/'.codex/skills/dots-todo-planning'
        original.mkdir(parents=True)
        (original/'SKILL.md').write_text('Original planning skill\n')
        before = list(self.home.rglob('*'))
        self.cli('install', '--dry-run', '--json')
        self.assertEqual(before, list(self.home.rglob('*')))
        self.cli('install', '--yes')
        for name in names.values():
            self.assertEqual((self.home/'.codex/skills'/name).resolve(), self.repo/'.codex/skills'/name)
        if os.name != 'nt': self.assertEqual(command.resolve(), self.repo/'bin/todo')
        self.assertEqual(json.loads(self.cli('install', '--yes', '--json').stdout)['status'], 'unchanged')
        self.cli('uninstall', '--yes')
        self.assertEqual(command.read_text(), 'Original command\n')
        for name in names.values():
            if name != 'dots-todo-planning': self.assertFalse((self.home/'.codex/skills'/name).exists())
            self.assertTrue((self.repo/'.codex/skills'/name).exists())
        self.assertFalse(original.is_symlink())
        self.assertEqual((original/'SKILL.md').read_text(), 'Original planning skill\n')
        self.assertEqual(project_goals.read_text(), '{"schema": 1, "goals": []}\n')
        self.assertEqual(global_goals.read_text(), '{"schema": 1, "goals": []}\n')

    def test_backup_survives_reconciliation(self):
        self.target.parent.mkdir(parents=True)
        self.target.write_text('before installation')
        self.cli('install','--yes')
        first = self.receipt()['entries'][str(self.target)]
        self.source.write_text('updated repository')
        self.cli('install','--yes')
        self.assertEqual(first,self.receipt()['entries'][str(self.target)])
        self.cli('uninstall','--yes')
        self.assertEqual(self.target.read_text(),'before installation')
        self.assertEqual(self.source.read_text(),'updated repository')

    def test_preserves_preexisting_matching_link_and_user_drift(self):
        self.target.parent.mkdir(parents=True)
        self.target.symlink_to(self.source)
        self.cli('install','--yes')
        self.assertNotIn(str(self.target),self.receipt()['entries'])
        self.cli('uninstall','--yes')
        self.assertTrue(self.target.is_symlink())
        self.target.unlink()
        self.cli('install','--yes')
        self.target.unlink()
        self.target.write_text('user replacement')
        result=json.loads(self.cli('uninstall','--yes','--json',ok=False).stdout)
        self.assertEqual(result['status'],'incomplete')
        self.assertEqual(self.target.read_text(),'user replacement')
        self.assertIn(str(self.target),self.receipt()['entries'])

    def test_reviewed_foreign_link_is_backed_up_and_restored(self):
        self.target.parent.mkdir(parents=True)
        missing = self.home/'missing'
        self.target.symlink_to(missing)
        original_link = os.readlink(self.target)
        self.cli('install','--yes')
        self.assertEqual(self.target.resolve(), self.source)
        entry = self.receipt()['entries'][str(self.target)]
        self.assertIn('backup_id', entry)
        self.cli('uninstall','--yes')
        self.assertEqual(os.readlink(self.target), original_link)

    def test_catalog_drift_after_preview(self):
        with mock.patch.dict(os.environ,self.env,clear=True):
            install=Installation(self.repo)
            install.plan_install()
            self.write('.dots/files.json',dict(schema=1,repository='dots',resources=[]))
            with self.assertRaisesRegex(ValueError,'changed after preview'):
                install.apply('install')
        self.assertFalse(self.target.exists())

    def test_failure_rolls_back_links_and_receipt(self):
        self.target.parent.mkdir(parents=True)
        self.target.write_text('original')
        with mock.patch.dict(os.environ,self.env,clear=True):
            install=Installation(self.repo)
            install.plan_install()
            save=install.store.save
            failed=False
            def fail(doc):
                nonlocal failed
                save(doc)
                if not failed and doc['status']=='applying' and any(e['phase']=='done' for e in doc['operations']):
                    failed=True
                    raise OSError('injected failure')
            with mock.patch.object(install.store,'save',side_effect=fail):
                with self.assertRaisesRegex(OSError,'injected failure'):
                    install.apply('install')
        self.assertEqual(self.target.read_text(),'original')
        self.assertFalse((self.home/'.state/dots/installation.json').exists())

    def test_undo_install_restores_receipt(self):
        result=json.loads(self.cli('install','--yes','--json').stdout)
        store=Store(self.home/'.state/dots')
        ops,guards,catalogs=store.inverse(result['transaction'])
        store.apply('undo',ops,guards,retain=True,catalogs=catalogs)
        self.assertFalse(self.target.exists())
        self.assertFalse((self.home/'.state/dots/installation.json').exists())

    def test_declined_noninteractive_and_bad_options(self):
        self.cli('install',ok=False)
        self.cli('uninstall','--update',ok=False)
        self.assertFalse((self.home/'.state').exists())

    def git(self, root, *args):
        result=subprocess.run(['git','-C',str(root),*args],env=self.env,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        return result.stdout.strip()

    def git_fixture(self):
        # The updated child controller must have its full dependency closure.
        # Omit publishers so this fixture cannot activate application themes.
        shutil.copytree(ROOT/'lib/dots', self.repo/'lib/dots',
                        ignore=shutil.ignore_patterns('themes','__pycache__','*.pyc'))
        self.git(self.repo,'init','--initial-branch=main')
        self.git(self.repo,'config','user.email','fixture@example.invalid')
        self.git(self.repo,'config','user.name','Fixture')
        self.git(self.repo,'add','.')
        self.git(self.repo,'commit','-m','Initial fixture')
        remote=self.base/'remote.git'
        self.git(self.base,'clone','--bare',str(self.repo),str(remote))
        self.git(self.repo,'remote','add','origin',str(remote))
        self.git(self.repo,'fetch','origin')
        self.git(self.repo,'branch','--set-upstream-to=origin/main')
        author=self.base/'author'
        self.git(self.base,'clone',str(remote),str(author))
        self.git(author,'config','user.email','fixture@example.invalid')
        self.git(author,'config','user.name','Fixture')
        return author

    def test_update_fast_forward_and_original_backup(self):
        author=self.git_fixture()
        self.target.parent.mkdir(parents=True)
        self.target.write_text('pre-install')
        self.cli('install','--yes')
        (author/'config/example/settings').write_text('remote update')
        self.git(author,'add','.')
        self.git(author,'commit','-m','Update fixture')
        self.git(author,'push','origin','HEAD:refs/heads/main')
        oldhead=self.git(self.repo,'rev-parse','HEAD')
        oldfetch=(self.repo/'.git/FETCH_HEAD').read_bytes()
        self.cli('install','--update','--dry-run')
        self.assertEqual(oldfetch,(self.repo/'.git/FETCH_HEAD').read_bytes())
        self.assertEqual(oldhead,self.git(self.repo,'rev-parse','HEAD'))
        result=self.cli('install','--update','--yes','--verbose')
        self.assertIn('Unchanged',result.stderr)  # Survives the updated Python process.
        self.assertEqual(self.target.read_text(),'remote update')
        self.cli('uninstall','--yes')
        self.assertEqual(self.target.read_text(),'pre-install')

    def test_update_dirty_and_diverged_refused(self):
        author=self.git_fixture()
        self.source.write_text('dirty')
        self.cli('install','--update','--yes',ok=False)
        self.assertEqual(self.source.read_text(),'dirty')
        self.git(self.repo,'add','.')
        self.git(self.repo,'commit','-m','Local branch')
        (author/'remote-only').write_text('remote')
        self.git(author,'add','.')
        self.git(author,'commit','-m','Diverge')
        self.git(author,'push','origin','HEAD:refs/heads/main')
        head=self.git(self.repo,'rev-parse','HEAD')
        self.cli('install','--update','--yes',ok=False)
        self.assertEqual(head,self.git(self.repo,'rev-parse','HEAD'))
        self.assertFalse(self.target.exists())

    def test_update_preserves_ignored_content(self):
        (self.repo/'.gitignore').write_text('private-file\n')
        author=self.git_fixture()
        (self.repo/'private-file').write_text('local content')
        (author/'private-file').write_text('remote content')
        self.git(author,'add','--force','private-file')
        self.git(author,'commit','-m','Add formerly ignored path')
        self.git(author,'push','origin','HEAD:refs/heads/main')
        head=self.git(self.repo,'rev-parse','HEAD')
        self.cli('install','--update','--yes',ok=False)
        self.assertEqual((self.repo/'private-file').read_text(),'local content')
        self.assertEqual(head,self.git(self.repo,'rev-parse','HEAD'))

    def test_source_drift_after_preview(self):
        with mock.patch.dict(os.environ,self.env,clear=True):
            install=Installation(self.repo)
            install.plan_install()
            self.source.write_text('changed')
            with self.assertRaisesRegex(ValueError,'changed after preview'):
                install.apply('install')
        self.assertFalse(self.target.exists())

    def test_interrupted_transaction_recovers_before_retry(self):
        code = '''
import os,sys
sys.path.insert(0,sys.argv[1])
from install import Installation
p=Installation(os.environ['DOTS']);p.plan_install()
save=p.store.save
def crash(doc):
    save(doc)
    if doc['status']=='applying' and any(e['phase']=='done' for e in doc['operations']):
        os._exit(17)
p.store.save=crash
p.apply('install')
'''
        result=subprocess.run([sys.executable,'-B','-c',code,str(ROOT/'lib/dots/files')],env=self.env,capture_output=True,text=True)
        self.assertEqual(result.returncode,17,result.stderr)
        self.cli('install','--yes',ok=False)
        store=Store(self.home/'.state/dots')
        doc=store.records()[0]
        store.recover(doc['id'])
        self.assertFalse(self.target.exists())
        self.cli('install','--yes')
        self.assertTrue(self.target.is_symlink())

    def test_link_capability_refusal_preserves_existing_config(self):
        self.target.parent.mkdir(parents=True)
        self.target.write_text('before')
        with mock.patch.dict(os.environ,self.env,clear=True):
            install=Installation(self.repo)
            install.plan_install()
            with mock.patch.object(Path,'symlink_to',side_effect=OSError('link privilege unavailable')):
                with self.assertRaisesRegex(ValueError,'symbolic links unavailable'):
                    install.apply('install')
        self.assertEqual(self.target.read_text(),'before')
        self.assertFalse((self.home/'.state/dots/installation.json').exists())

    def test_optional_source_download_is_explicit_and_nonrecursive(self):
        if not shutil.which('git'):
            self.skipTest('Git unavailable')
        author=self.git_fixture()
        child=self.base/'child'
        child.mkdir()
        self.git(child,'init','--initial-branch=main')
        self.git(child,'config','user.email','fixture@example.invalid')
        self.git(child,'config','user.name','Fixture')
        (child/'.dots').mkdir()
        (child/'settings').write_text('optional config')
        (child/'.dots/files.json').write_text(json.dumps(dict(schema=1,repository='nvim',resources=[dict(id='optional',app='nvim',category='config',source='settings',target='${CONFIG}/optional',strategy='link',platforms=['termux','linux','wsl','windows'])])))
        self.git(child,'add','.')
        self.git(child,'commit','-m','Optional fixture')
        nested=self.base/'nested source'
        nested.mkdir()
        self.git(nested,'init','--initial-branch=main')
        self.git(nested,'config','user.email','fixture@example.invalid')
        self.git(nested,'config','user.name','Fixture')
        (nested/'sentinel').write_text('nested source must stay uninitialized')
        self.git(nested,'add','.')
        self.git(nested,'commit','-m','Nested fixture')
        self.git(child,'-c','protocol.file.allow=always','submodule','add',str(nested),'nested')
        self.git(child,'commit','-am','Record nested fixture')
        self.git(self.repo,'-c','protocol.file.allow=always','submodule','add',str(child),'optional')
        sources=json.loads((self.repo/'.dots/sources.json').read_text())
        sources['sources'].append(dict(id='nvim',path='optional',platforms=['termux','linux','wsl','windows'],roots=['.']))
        self.write('.dots/sources.json',sources)
        self.git(self.repo,'add','.')
        self.git(self.repo,'commit','-m','Record optional source')
        pin=self.git(self.repo,'rev-parse','HEAD:optional')
        # A fresh clone has no cached optional checkout. Advancing its source
        # proves acquisition uses the parent's pin rather than the remote tip.
        fresh=self.base/'fresh checkout space 雪'
        self.git(self.base,'clone',str(self.repo),str(fresh))
        self.repo=fresh
        self.env['DOTS']=str(fresh)
        self.source=fresh/'config/example/settings'
        self.assertFalse((fresh/'.git/modules/optional').exists())
        (child/'settings').write_text('unrecorded upstream change')
        self.git(child,'commit','-am','Advance optional upstream')
        self.assertNotEqual(self.git(child,'rev-parse','HEAD'),pin)
        self.cli('install','--yes')
        self.assertFalse((self.repo/'optional/.git').exists())
        self.cli('install','--with-source','nvim','--dry-run')
        self.assertFalse((self.repo/'optional/.git').exists())
        # Local fixture transport is enabled for this test only.
        self.env['GIT_ALLOW_PROTOCOL']='file'
        self.cli('install','--with-source','nvim','--yes')
        self.assertEqual((self.home/'.config/optional').read_text(),'optional config')
        self.assertEqual(self.git(self.repo/'optional','rev-parse','HEAD'),pin)
        self.assertFalse((self.repo/'optional/nested/.git').exists())
        self.assertFalse((self.repo/'optional/nested/sentinel').exists())

    def theme_fixture(self):
        for name in ('lib', 'themes', 'default'):
            shutil.copytree(ROOT/name, self.repo/name, symlinks=True)
        (self.repo/'config/fsh').mkdir()
        shutil.copy2(ROOT/'config/fsh/README.md', self.repo/'config/fsh/README.md')
        doc=json.loads((self.repo/'.dots/files.json').read_text())
        doc['resources'].append(dict(id='fsh',source='config/fsh',target='${CONFIG}/fsh',strategy='directory-link',app='fsh',category='config',platforms=['termux','linux','wsl']))
        self.write('.dots/files.json',doc)

    def test_eza_setup_respects_destination_and_restore(self):
        self.theme_fixture()
        source = self.repo / 'config/eza'
        source.mkdir()
        (source / 'reference.yml').write_text('colourful: true\n')
        doc = json.loads((self.repo / '.dots/files.json').read_text())
        doc['resources'].append(dict(id='eza', source='config/eza',
            target='${APP_CONFIG:eza}' if os.name == 'nt' else '${CONFIG}/eza',
            strategy='directory-link', app='eza', category='config',
            platforms=['termux','linux','wsl','windows']))
        self.write('.dots/files.json', doc)
        if os.name != 'nt':
            self.env['EZA_CONFIG_DIR'] = str(self.home / 'other eza')
            preview = self.cli('install', '--dry-run', '--json').stdout
            self.assertNotIn(str(source / 'theme.yml'), preview)
            self.env.pop('EZA_CONFIG_DIR')
        self.cli('install', '--yes')
        target = source / 'theme.yml'
        self.assertTrue(target.is_symlink())
        self.assertIn('colourful: true', target.read_text())
        self.cli('uninstall', '--yes')
        self.assertFalse(target.is_symlink())
        self.assertEqual((source / 'reference.yml').read_text(), 'colourful: true\n')

    def test_leaf_setup_two_connectors_and_restore(self):
        self.theme_fixture()
        source = self.repo / 'config/leaf'
        source.mkdir()
        (source / 'config.toml').write_text('theme = "themes/dots.toml"\n')
        doc = json.loads((self.repo / '.dots/files.json').read_text())
        doc['resources'].append(dict(id='leaf', source='config/leaf',
            target='${APP_CONFIG:leaf}' if os.name == 'nt' else '${CONFIG}/leaf',
            strategy='directory-link', app='leaf', category='config',
            platforms=['termux','linux','wsl','windows']))
        self.write('.dots/files.json', doc)
        self.env['DOTS_APP_LEAF_CONFIG'] = str(self.home / 'other leaf')
        preview = self.cli('install', '--dry-run', '--json').stdout
        if os.name != 'nt':
            self.assertNotIn(str(source / 'themes/dots.toml'), preview)
        self.env.pop('DOTS_APP_LEAF_CONFIG')
        self.cli('install', '--yes')
        ui = source / 'themes/dots.toml'
        syntax = source / 'themes/dots.tmTheme'
        self.assertTrue(ui.is_symlink())
        self.assertTrue(syntax.is_symlink())
        self.assertIn('syntax = "dots.tmTheme"', ui.read_text())
        self.assertIn('<plist', syntax.read_text())
        self.assertEqual(json.loads(self.cli('install','--yes','--json').stdout)['status'], 'unchanged')
        self.cli('uninstall', '--yes')
        self.assertFalse(ui.is_symlink())
        self.assertFalse(syntax.is_symlink())
        self.assertEqual((source / 'config.toml').read_text(), 'theme = "themes/dots.toml"\n')

    @unittest.skipIf(os.name == 'nt', 'POSIX theme publication')
    def test_legacy_vivid_setup_notice_json_and_repeat(self):
        self.theme_fixture()
        install_vivid(self.repo/'bin')
        self.env['PATH'] = str(self.repo/'bin') + os.pathsep + self.env['PATH']
        self.env['DOTS_COLOR'] = self.env['DOTS_ICONS'] = 'always'
        preview = self.cli('install', '--dry-run', '--json')
        self.assertEqual(json.loads(preview.stdout)['status'], 'preview')
        self.assertNotIn('compatibility mode', preview.stderr)
        self.assertFalse((self.home/'.state').exists())
        result = self.cli('install', '--yes', '--json')
        self.assertEqual(json.loads(result.stdout)['status'], 'complete')
        self.assertEqual(result.stderr.count('Vivid compatibility mode'), 1)
        self.assertNotIn('\x1b', result.stderr + result.stdout)
        active = self.home/'.state/dots/current/theme'
        self.assertEqual((self.home/'.config/fsh/dots.ini').resolve(), active.resolve()/'fsh.ini')
        self.assertTrue((active/'fsh.ini').is_file())
        doc = json.loads((active/'colors.json').read_text())
        for kind in ('tw', 'ow'):
            style = doc['ls_rules']['types'][kind]['style']
            self.assertTrue(style['bold'] and style['underline'])
        receipt = self.receipt()
        repeated = self.cli('install', '--yes', '--json')
        self.assertEqual(json.loads(repeated.stdout)['status'], 'unchanged')
        self.assertNotIn('compatibility mode', repeated.stderr)
        self.assertEqual(self.receipt(), receipt)

    @unittest.skipIf(os.name == 'nt', 'POSIX theme publication')
    def test_legacy_vivid_setup_human_notice_and_custom_failure(self):
        self.theme_fixture()
        install_vivid(self.repo/'bin')
        self.env['PATH'] = str(self.repo/'bin') + os.pathsep + self.env['PATH']
        self.env['DOTS_COLOR'] = 'always'
        result = self.cli('install', '--yes')
        self.assertEqual(result.stderr.count('Vivid compatibility mode'), 1)
        self.assertRegex(result.stderr, r'\x1b\[[0-9;]+mVivid compatibility mode\x1b\[0m')
        active = self.home/'.state/dots/current/theme'
        previous = active.resolve(); receipt = self.receipt()
        template = self.home/'.config/dots/themed/vivid.yml.tpl'
        template.parent.mkdir(parents=True)
        theme = json.loads((active/'vivid.yml').read_text())
        theme['archives']['font-style'] = ['bold', 'underline']
        template.write_text(json.dumps(theme, indent=2))
        result = self.cli('install', '--yes', ok=False)
        self.assertIn(str(template), result.stderr)
        self.assertIn('Vivid 0.9.0', result.stderr)
        self.assertEqual(active.resolve(), previous)
        self.assertEqual(self.receipt(), receipt)

    @unittest.skipIf(os.name == 'nt', 'POSIX fresh-checkout publication')
    @unittest.skipUnless(shutil.which('git'), 'Git required to enumerate tracked sources')
    def test_fresh_checkout_wsl_setup_connectors_check_and_restore(self):
        self.full_checkout_lifecycle()

    @unittest.skipIf(os.name == 'nt', 'POSIX complete-checkout lifecycle')
    def test_full_checkout_bundled_install_repeat_and_restore(self):
        self.full_checkout_lifecycle(bundled_only=True)

    @unittest.skipIf(os.name == 'nt', 'POSIX Termux-profile full-checkout lifecycle')
    @unittest.skipUnless(shutil.which('git'), 'Git required to enumerate tracked sources')
    def test_fresh_checkout_termux_setup_connectors_check_and_restore(self):
        # A non-Android POSIX host is explicitly a profile simulation. Native
        # Termux acceptance must run this same case on the phone independently.
        self.full_checkout_lifecycle(profile='termux')

    def full_checkout_lifecycle(self, bundled_only=False, profile='wsl'):
        self.assertIn(profile, ('wsl', 'termux'))
        # Copy only versioned public inputs, never ignored connectors or local
        # submodule contents. Include this change's new source files before commit.
        names=set(subprocess.check_output(['git','-C',str(ROOT),'ls-files','--cached','--others','--exclude-standard','-z','--',
            '.dots','.codex/skills/dots-todo','.codex/skills/dots-todo-planning',
            '.codex/skills/dots-todo-maintenance','bin','lib','plugins','default','themes','config','shells','ruby',
            'install.sh','uninstall.sh']).decode().rstrip('\0').split('\0'))
        # Profile implementations and visual inputs accompany the core registry.
        for filename in ('profile.json','config.json','colors.toml','icons.toml'):
            names.update(str(p.relative_to(ROOT)) for p in (ROOT/'profiles').glob('*/'+filename))
        names.update(('config/fsh/README.md','default/themed/eza.yml.tpl','default/themed/television.toml.tpl','default/themed/leaf.toml.tpl','lib/dots/themes/generation.bash',
                      'lib/dots/files/events.py', 'lib/dots/verbose.bash', 'lib/dots/files/app_paths.py'))
        names.update(str(p.relative_to(ROOT)) for p in (ROOT/'lib/dots/metadata').glob('*.meta'))
        external_termux_links = {'profiles/termux/config/termux/colors.properties',
                                'profiles/termux/config/termux/shell'}
        if profile == 'termux':
            names.update(subprocess.check_output(['git','-C',str(ROOT),'ls-files','-z','--',
                'profiles/termux/config','man']).decode().rstrip('\0').split('\0'))
        shutil.rmtree(self.repo)
        self.repo.mkdir()
        for name in sorted(names):
            source=ROOT/name
            if source.is_dir() and not source.is_symlink():
                continue  # An uninitialized optional submodule is not a source.
            if not source.exists() and not source.is_symlink():
                continue
            target=self.repo/name
            target.parent.mkdir(parents=True,exist_ok=True)
            if source.is_symlink():
                link=os.readlink(source)
                if name in external_termux_links and os.path.isabs(link):
                    continue  # Never follow the shipped phone-local links.
                self.assertFalse(os.path.isabs(link),name)
                self.assertTrue(Path(os.path.abspath(target.parent/link)).is_relative_to(self.repo),name)
                target.symlink_to(link)
            else:
                shutil.copy2(source,target)
        termux_version = self.env.get('TERMUX_VERSION') or 'fixture'
        self.env={k:v for k,v in self.env.items() if k in (
            'PATH','TERMUX__PREFIX','LD_PRELOAD','LD_LIBRARY_PATH','TMPDIR','TMP','TEMP','HOME','USERPROFILE',
            'DOTS','XDG_CONFIG_HOME','XDG_STATE_HOME','XDG_DATA_HOME','XDG_CACHE_HOME',
            'XDG_RUNTIME_DIR','LANG','LC_ALL','LC_CTYPE','PYTHONNOUSERSITE','PYTHONUTF8','PYTHONIOENCODING',
            'CODEX_HOME','PI_CODING_AGENT_DIR','GIT_CONFIG_GLOBAL','GIT_CONFIG_NOSYSTEM',
            'GIT_TERMINAL_PROMPT','GIT_EXEC_PATH','DOTS_COLOR','DOTS_ICONS','TERM','PYTHONDONTWRITEBYTECODE')}
        # On Android, both fixtures need the shebang adapter. A private prefix
        # keeps it available without forcing platform detection to choose Termux.
        if profile == 'termux' or self.env.get('TERMUX__PREFIX'):
            prefix = self.base/'prefix/usr'
            bindir = prefix/'bin'
            bindir.mkdir(parents=True)
            # Termux's shebang redirection must find native env/interpreters
            # beneath the owned prefix, without exposing its real package tree.
            for name in ('env', 'sh', 'bash', 'python', 'python3'):
                native = sys.executable if name in ('python', 'python3') else shutil.which(name, path=self.env['PATH'])
                self.assertTrue(native, 'required native runtime: '+name)
                (bindir/name).symlink_to(native)
            self.env['TERMUX__PREFIX'] = str(prefix)
            self.env['PATH'] = str(bindir)+os.pathsep+self.env['PATH']
        if profile == 'termux':
            self.env.update(PREFIX=str(prefix), TERMUX_VERSION=termux_version)
        else:
            self.env['WSL_DISTRO_NAME']='Fixture'
        self.env['DOTS_PROGRESS']='never'
        from platform_info import detect
        self.assertEqual(detect(env=self.env)['platform'], profile,
                         'the selected profile must match the owned prefix/runtime fixture')
        templates=self.base/'git-templates'; templates.mkdir()
        hooks=self.base/'git-hooks'; hooks.mkdir()
        build_tmp=self.base/'build-tmp'; build_tmp.mkdir()
        self.env.update(GIT_ALLOW_PROTOCOL='file', GIT_TEMPLATE_DIR=str(templates),
                        GIT_CONFIG_COUNT='5', GIT_CONFIG_KEY_0='core.hooksPath', GIT_CONFIG_VALUE_0=str(hooks),
                        GIT_CONFIG_KEY_1='commit.gpgsign', GIT_CONFIG_VALUE_1='false',
                        GIT_CONFIG_KEY_2='tag.gpgsign', GIT_CONFIG_VALUE_2='false',
                        GIT_CONFIG_KEY_3='gc.auto', GIT_CONFIG_VALUE_3='0',
                        GIT_CONFIG_KEY_4='maintenance.auto', GIT_CONFIG_VALUE_4='false',
                        GOENV='off', GOWORK='off', GOTOOLCHAIN='local', GOPROXY='off', GOSUMDB='off',
                        GOVCS='*:off', CGO_ENABLED='0', GOTMPDIR=str(build_tmp))
        legacy_bin = self.base/'legacy-bin'
        legacy_bin.mkdir()
        install_vivid(legacy_bin)
        self.env['PATH'] = str(legacy_bin) + os.pathsep + self.env['PATH']
        self.assertEqual(list((self.repo/'config/fsh').iterdir()),[self.repo/'config/fsh/README.md'])
        def snapshot(root):
            result = {}
            for path in root.rglob('*'):
                info = path.lstat()
                content = ('link', os.readlink(path)) if path.is_symlink() else (
                    ('directory',) if path.is_dir() else ('file', path.read_bytes()))
                result[str(path.relative_to(root))] = (info.st_mode, content)
            return result
        originals = {}
        if profile == 'termux':
            originals = {
                self.home/'.termux/colors.properties': b'# Original owned terminal colors\nbackground=#010203\n',
                self.home/'.termux/preserved-note': b'Original owned terminal directory\n',
                prefix/'share/figlet/dots.flf': b'Original owned Figlet font\n',
                prefix/'share/figlet/dots-mixed.flf': b'Original owned mixed Figlet font\n',
                prefix/'share/man/man1/dots.1': b'Original owned manual\n',
            }
            for path, data in originals.items():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
            before_home, before_prefix = snapshot(self.home), snapshot(prefix)
            termux_source = self.repo/'profiles/termux/config/termux'
            self.assertTrue(termux_source.is_dir())
            self.assertFalse(os.path.lexists(termux_source/'colors.properties'))
            self.assertFalse(os.path.lexists(termux_source/'shell'))
            (termux_source/'colors.properties').write_bytes(b'# Owned source color baseline\nbackground=#040506\n')
            before_source = snapshot(self.repo)
        def run(script,*args):
            preparation=['--offline'] if script == 'install.sh' else []
            result=subprocess.run(['sh',str(self.repo/script),*args,*preparation,'--json'],env=self.env,
                                  capture_output=True,text=True,timeout=600)
            self.assertEqual(result.returncode,0,result.stderr + result.stdout)
            self.assertNotIn('\x1b',result.stdout)
            doc = json.loads(result.stdout)
            # Refuse a bad preview before any subsequent apply is launched.
            for row in doc['items']:
                if row.get('target'):
                    target = Path(row['target'])
                    self.assertTrue(target.is_absolute() and target.is_relative_to(self.base)
                                    and target.resolve().is_relative_to(self.base), row)
            return doc
        preview=run('install.sh','--dry-run')
        self.assertEqual(preview['platform'],profile)
        if profile == 'termux':
            self.assertEqual(snapshot(self.home), before_home)
            self.assertEqual(snapshot(prefix), before_prefix)
            self.assertEqual(snapshot(self.repo), before_source)
            mapping = next(r for r in preview['items'] if r['id']=='termux:termux')
            self.assertEqual(Path(mapping['target']), self.home/'.termux')
            self.assertEqual(set(preview['components']), {'core','files','themes','anodize','blastoff','pkgs'})
        else:
            self.assertEqual(list(self.home.iterdir()),[])
        fsh=next(row for row in preview['items'] if row['id']=='dots:fsh')
        self.assertEqual(fsh['status'],'create')
        # Go telemetry is controlled by a file, not a GOTELEMETRY env override.
        # Seed it only after the no-write preview assertion and before compilation.
        telemetry=self.home/'.config/go/telemetry'
        telemetry.mkdir(parents=True)
        (telemetry/'mode').write_text('off\n', encoding='utf-8')
        result=run('install.sh','--yes')
        active=self.home/'.state/dots/current/theme'
        first_receipt = self.receipt()
        self.assertEqual((self.home/'.local/bin/patina').resolve(), self.repo/'bin/patina')
        if profile == 'termux':
            self.assertEqual((self.home/'.termux').resolve(), termux_source)
            self.assertTrue((termux_source/'colors.properties').is_symlink())
            self.assertEqual((self.home/'.termux/colors.properties').resolve(), (active/'termux.properties').resolve())
            self.assertIn(str(termux_source/'colors.properties'), first_receipt['entries'])
            self.assertNotIn(str(self.home/'.termux/colors.properties'), first_receipt['entries'])
            for name in ('dots', 'dots-mixed'):
                self.assertEqual((prefix/('share/figlet/'+name+'.flf')).resolve(),
                                 self.repo/('config/figlet/'+name+'.flf'))
            self.assertEqual((prefix/'share/man/man1/dots.1').resolve(), self.repo/'man/dots.1')
            binary = self.repo/'plugins/anodize/engine/.build/anodize-engine'
            self.assertTrue(binary.is_file())
            self.assertTrue(os.access(binary, os.X_OK))
            for target in first_receipt['entries']:
                self.assertTrue(Path(target).is_relative_to(self.base)
                                and Path(target).resolve().is_relative_to(self.base), target)
        self.assertTrue((self.home/'.config/fsh').is_symlink())
        self.assertTrue((self.home/'.config/fsh/dots.ini').is_file())
        manifest = json.loads((self.repo/'profiles'/profile/'profile.json').read_text())
        for mapping in manifest['files']:
            if not mapping['source'].startswith('${THEME}/'):
                continue
            artifact = mapping['source'].removeprefix('${THEME}/')
            row = next((r for r in result['items'] if r['id'] == 'theme:'+mapping['id']), None)
            if row and row['status'] != 'skipped':
                self.assertTrue(Path(row['target']).is_symlink(), mapping['id'])
                self.assertTrue(Path(row['target']).exists(), mapping['id'])
                self.assertTrue((active/artifact).exists(), mapping['id'])
        for template in (self.repo/'default/themed').glob('*.tpl'):
            self.assertTrue((active/template.name[:-4]).is_file(),template.name)
        self.assertFalse((self.repo/'config/btop/themes/dots.theme').exists())  # Stashed.
        self.assertFalse((self.repo/'config/nvim/.git').exists())
        check=subprocess.run([sys.executable,'-B',str(self.repo/'lib/dots/files/check.py'),
                              '--dry-run','--json','--app','fsh'],env=self.env,capture_output=True,text=True)
        self.assertEqual(check.returncode,0,check.stderr)
        self.assertNotIn('"eligible": true',check.stdout)
        self.assertIn('dots:fsh',check.stdout)
        repeated = run('install.sh','--yes')
        changes = [row for row in repeated['items'] if row['status'] not in ('unchanged', 'skipped')]
        if bundled_only:
            # Keep the strict whole-theme check above. Its baseline fingerprint
            # failure must not prevent verifying the new applications' removal.
            self.assertTrue(all(row['id'].startswith('theme:') for row in changes), changes)
            for app in ('blastoff', 'pkgs'):
                assets = [row for row in repeated['items'] if row['id'].startswith('dots:'+app+':')]
                self.assertGreaterEqual(len(assets), 4)
                self.assertTrue(all(row['status'] == 'unchanged' for row in assets), assets)
        else:
            self.assertEqual(repeated['status'], 'unchanged', json.dumps(changes, indent=2))
        if profile == 'termux':
            self.assertEqual(self.receipt(), first_receipt)
            for app in ('blastoff', 'pkgs'):
                assets = [row for row in repeated['items'] if row['id'].startswith('dots:'+app+':')]
                self.assertGreaterEqual(len(assets), 4)
                self.assertTrue(all(row['status']=='unchanged' for row in assets), assets)
        run('uninstall.sh','--yes')
        if profile == 'termux':
            self.assertFalse(self.receipt()['entries'])
            self.assertFalse((self.home/'.termux').is_symlink())
            for path, data in originals.items():
                self.assertFalse(path.is_symlink(), str(path))
                self.assertEqual(path.read_bytes(), data)
            self.assertEqual(snapshot(prefix), before_prefix)
            self.assertEqual(snapshot(self.repo), before_source)
            self.assertFalse(active.exists())
        self.assertFalse((self.home/'.config/fsh').is_symlink())
        self.assertFalse((self.repo/'config/fsh/dots.ini').is_symlink())
        self.assertTrue((self.repo/'config/fsh/README.md').is_file())
        for app in ('blastoff', 'pkgs'):
            self.assertFalse((self.home/'.local/bin'/app).exists())
            self.assertTrue((self.repo/'bin'/app).is_file())

    @unittest.skipIf(os.name == 'nt', 'POSIX theme publication')
    def test_theme_output_and_pointer_repair_retains_baseline(self):
        self.theme_fixture()
        self.cli('install','--yes')
        active=self.home/'.state/dots/current/theme'
        initial=active.resolve()
        baseline=self.receipt()['entries'][str(active)]['before']
        for relative in ('fsh.ini', 'colors.json', 'yazi/tmtheme.xml'):
            with self.subTest(artifact=relative):
                old=active.resolve()
                (old/relative).unlink()
                preview=json.loads(self.cli('install','--dry-run','--json').stdout)
                row=next(r for r in preview['items'] if r['id']=='theme:catppuccin-mocha')
                self.assertEqual(row['status'],'prepare')
                self.assertIn(relative,row['target'])
                self.assertEqual(active.resolve(),old)
                self.assertFalse((old/relative).exists())
                self.cli('install','--yes')
                self.assertNotEqual(active.resolve(),old)
                self.assertTrue((active/relative).is_file())
        active.unlink()
        self.cli('install','--yes')
        self.assertTrue(active.is_symlink())
        self.assertEqual(self.receipt()['entries'][str(active)]['before'],baseline)
        self.assertEqual(json.loads(self.cli('install','--yes','--json').stdout)['status'],'unchanged')
        self.cli('uninstall','--yes')
        self.assertFalse(active.exists())
        self.assertTrue(initial.is_dir())
        self.assertFalse((self.home/'.config/fsh').is_symlink())
        self.assertFalse((self.repo/'config/fsh/dots.ini').is_symlink())
        self.assertTrue((self.repo/'config/fsh/README.md').is_file())

    @unittest.skipIf(os.name == 'nt', 'POSIX theme publication')
    def test_failed_theme_repair_does_not_publish_or_change_receipt(self):
        self.theme_fixture()
        self.cli('install','--yes')
        active=self.home/'.state/dots/current/theme'
        old=active.resolve(); receipt=self.receipt()
        (old/'fsh.ini').unlink()
        (self.repo/'default/themed/fsh.ini.tpl').write_text('{{ unknown_fsh_color }}')
        result=self.cli('install','--yes',ok=False)
        self.assertIn('unknown template color',result.stderr)
        self.assertEqual(active.resolve(),old)
        self.assertEqual(self.receipt(),receipt)
        self.assertFalse((old/'fsh.ini').exists())

    @unittest.skipIf(os.name == 'nt', 'POSIX theme publication')
    def test_theme_repair_publication_failure_rolls_back(self):
        self.theme_fixture()
        self.cli('install','--yes')
        active=self.home/'.state/dots/current/theme'
        old=active.resolve(); receipt=self.receipt()
        (old/'fsh.ini').unlink()
        with mock.patch.dict(os.environ,self.env,clear=True):
            install=Installation(self.repo)
            install.plan_install()
            save=install.store.save
            failed=False
            def fail(doc):
                nonlocal failed
                save(doc)
                if not failed and doc['status']=='applying' and any(
                        row['path']==str(active) and row['phase']=='done' for row in doc['operations']):
                    failed=True
                    raise OSError('injected theme publication failure')
            with mock.patch.object(install.store,'save',side_effect=fail):
                with self.assertRaisesRegex(OSError,'injected theme publication failure'):
                    install.apply('install')
        self.assertTrue(failed)
        self.assertEqual(active.resolve(),old)
        self.assertEqual(self.receipt(),receipt)
        self.assertFalse((old/'fsh.ini').exists())
        self.cli('install','--yes')
        self.assertTrue((active/'fsh.ini').is_file())

    @unittest.skipIf(os.name == 'nt', 'POSIX theme publication')
    def test_incomplete_preparation_and_foreign_pointer_are_refused(self):
        self.theme_fixture()
        render=self.repo/'lib/dots/themes/render.bash'
        with render.open('a') as stream:
            stream.write("\neval \"$(declare -f dt_render | sed '1s/dt_render/dt_original_render/')\"\n"
                         'dt_render() { dt_original_render "$1" && rm "$1/fsh.ini"; }\n')
        result=self.cli('install','--yes',ok=False)
        self.assertIn('incomplete prepared theme',result.stderr)
        self.assertFalse(self.target.exists())
        self.assertFalse((self.home/'.state/dots/installation.json').exists())
        shutil.copy2(ROOT/'lib/dots/themes/render.bash',render)
        self.cli('install','--yes')
        active=self.home/'.state/dots/current/theme'
        active.unlink(); active.symlink_to(self.home)
        result=self.cli('install','--yes',ok=False)
        self.assertIn('invalid active theme',result.stderr)
        self.assertEqual(active.readlink(),self.home)

    @unittest.skipIf(os.name == 'nt', 'POSIX theme publication')
    def test_real_theme_install_repeat_and_restore(self):
        for mask in (0o22, 0o77):
            with self.subTest(umask=oct(mask)):
                previous = os.umask(mask)
                fixture = type(self)()
                try:
                    fixture.setUp()
                    fixture.check_real_theme_install_repeat_and_restore()
                finally:
                    fixture.doCleanups()
                    os.umask(previous)

    def check_real_theme_install_repeat_and_restore(self):
        shutil.copytree(ROOT/'lib',self.repo/'lib',symlinks=True)
        shutil.copytree(ROOT/'themes',self.repo/'themes',symlinks=True)
        shutil.copytree(ROOT/'default',self.repo/'default',symlinks=True)
        (self.repo/'config/kitty').mkdir()
        (self.repo/'config/kitty/kitty.conf').write_text('include dots-theme.conf\n')
        doc=json.loads((self.repo/'.dots/files.json').read_text())
        doc['resources'].append(dict(id='kitty',source='config/kitty',target='${CONFIG}/kitty',strategy='directory-link',app='kitty',category='config',platforms=['termux','linux','wsl']))
        self.write('.dots/files.json',doc)
        self.cli('install','--dry-run')
        self.assertFalse((self.home/'.state').exists())
        self.cli('install','--yes')
        active=self.home/'.state/dots/current/theme'
        connector=self.repo/'config/kitty/dots-theme.conf'
        self.assertTrue(active.is_symlink())
        self.assertTrue(connector.is_file())
        self.assertIn('background',connector.read_text())
        receipt=self.receipt()
        self.assertEqual(json.loads(self.cli('install','--yes','--json').stdout)['status'],'unchanged')
        self.assertEqual(receipt,self.receipt())
        # Normal publication remains compatible with setup-owned generations.
        # Suppress external app effects explicitly, including on Termux hosts.
        script='''DT_LIB="$DOTS/lib/dots/themes"
source "$DT_LIB/core.bash"
source "$DT_LIB/views.bash"
source "$DT_LIB/state.bash"
dt_apps_reload() { :; }
dt_plugins_after_publish() { :; }
dt_set rose-pine-dawn
'''
        switched=subprocess.run(['bash','-c',script],env=self.env,capture_output=True,text=True)
        self.assertEqual(switched.returncode,0,switched.stderr)
        template=self.repo/'lib/dots/themes/setup.bash'
        template.write_text(template.read_text()+'\n# Updated checkout fixture\n')
        self.cli('install','--yes')
        self.assertEqual((active/'id').read_text().strip(),'rose-pine-dawn')
        self.assertEqual(self.receipt()['entries'][str(active)]['before'],receipt['entries'][str(active)]['before'])
        for path, entry in self.receipt()['entries'].items():
            self.assertEqual(digest(path), entry['after'], path)
        self.cli('uninstall','--yes')
        self.assertFalse(active.is_symlink())
        self.assertFalse(connector.is_symlink())
        self.assertTrue((self.repo/'config/kitty/kitty.conf').exists())


if __name__=='__main__':
    unittest.main(verbosity=2)
