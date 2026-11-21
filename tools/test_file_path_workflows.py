#!/usr/bin/env python3
"""Flat-profile add/link/find routes dispatch through disposable catalog fixtures."""
import json
import io
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

import test_profile_backend as backend
from file_platform import state_root


class PathWorkflows(unittest.TestCase):
    write = backend.ProfileBackend.write
    files = backend.ProfileBackend.files
    undo = backend.ProfileBackend.undo

    def setUp(self):
        backend.ProfileBackend.setUp(self)
        for p in self.root.glob('profiles/*/profile.json'):
            row = json.loads(p.read_text())
            row['files'] = []
            self.write(p, row)
        self.config = Path(self.env['XDG_CONFIG_HOME'])
        self.config.mkdir()
        self.write(self.root/'.dots/file-locations.json', dict(schema=1, repository='dots', locations=[
            dict(id='apps', kind='root', target='${CONFIG}', source='config', platforms=self.resource['platforms'])]))

    def rows(self):
        return json.loads(self.path.read_text())['files']

    def run_json(self, *args):
        return json.loads(self.files(*args, '--json').stdout)

    def published(self):
        active = state_root()/'current/theme'
        generation = state_root()/'themes/generations/g.first'
        generation.mkdir(parents=True)
        (generation/'id').write_text('testing')
        (generation/'status').write_text('committed\n')
        (state_root()/'themes/current').write_text(generation.name+'\n')
        active.parent.mkdir(parents=True)
        active.symlink_to(generation, target_is_directory=True)
        return active, generation

    def test_add_scope_unmapped_and_existing_sources(self):
        for name, flags, owner, token in [('local', (), self.path.parent, 'PROFILE'),
                                         ('global', ('-g',), self.root, 'DOTS')]:
            target = self.config / name
            target.write_text(name)
            result = self.run_json('add', str(target), *flags, '--yes')
            self.assertEqual(target.resolve(), owner / 'config' / name)
            self.assertIn('${' + token + '}/config/' + name, {r['source'] for r in self.rows()})
            self.undo(result['id'])
            self.assertFalse(target.is_symlink())
            self.assertEqual(target.read_text(), name)
        target = self.home / '.unknown'
        target.write_text('my settings')
        self.assertEqual(self.run_json('add', str(target), '--dry-run')['items'][0]['status'], 'needs-source')
        self.files('add', str(target), '--yes', code=1)
        for flags, base in [((), self.path.parent), (('-g',), self.root)]:
            args = ('add', str(target), '--source', 'custom/.toolrc', *flags, '--yes')
            result = self.run_json(*args)
            self.assertEqual(target.resolve(), base/'custom/.toolrc')
            self.assertEqual(self.run_json(*args)['status'], 'unchanged')
            self.undo(result['id'])
        source = self.root/'config'/'already-owned'
        source.write_text('shared settings')
        self.run_json('add', str(source), '-t', str(self.config/'existing'), '--yes')
        self.assertEqual(self.rows()[-1]['source'], '${DOTS}/config/already-owned')
        self.assertFalse((self.path.parent/'config/already-owned').exists())
        local = self.path.parent/'owned.conf'
        local.write_text('profile setting')
        live = self.config/'known-local'
        live.symlink_to(local)
        for path in (local, live):
            result = self.files('add',str(path),'-g','--yes',code=1)
            self.assertIn('omit --global',result.stderr)
        skipped = self.run_json('add','--scan','--global','--dry-run')['items']
        self.assertTrue(any(row['status']=='skipped' and row.get('path')==str(live) for row in skipped))
        self.assertTrue(live.is_symlink())

    def test_link_forms_exact_paths_protection_and_repeat(self):
        source = self.root/'config/app'
        target = self.config/'new'
        for args in [('ln', '${DOTS}/config/app', '${CONFIG}/new'),
                     ('link', '-t', '${CONFIG}/new', str(source)),
                     ('ln', '-s', str(source), str(target)),
                     ('link', '--target', str(target), '--source', str(source))]:
            preview = self.run_json(*args, '--dry-run')
            self.assertEqual(preview['items'][0]['source'], str(source))
            self.assertEqual(preview['items'][0]['target'], str(target))
        self.assertFalse(target.exists())
        self.files('ln', '-s', str(source), '-s', str(source), '-t', str(target),code=2)
        self.files('ln', str(source), str(self.config/'absent/leaf'), '--yes',code=1)
        target.write_text('original')
        self.files('link', str(source), str(target), '--yes',code=1)
        result = self.run_json('ln', str(source), str(target), '--backup', '--yes')
        self.assertEqual(target.resolve(), source)
        self.assertEqual(self.run_json('ln', str(source), str(target), '--yes')['status'], 'unchanged')
        self.undo(result['id'])
        self.assertEqual(target.read_text(),'original')

    def test_find_default_roots_explicit_roots_and_receipts(self):
        source = self.root/'config/app'
        root = self.home/'nested'
        root.mkdir()
        extra = self.root/'config/extra'
        extra.write_text('extra')
        outside = root/'custom'
        outside.symlink_to(extra)
        target = self.config/'app'
        target.symlink_to(os.path.relpath(source,target.parent))
        original = os.readlink(target), target.stat(follow_symlinks=False).st_ino
        (self.config/'ordinary').write_text('ignored')
        (self.config/'broken').symlink_to(self.home/'missing')
        (self.config/'other').symlink_to(self.config/'ordinary')
        for args,expected in [(('find','--dry-run'),target), (('fd',str(root)),outside)]:
            rows = self.run_json(*args)['items']
            self.assertEqual([r['path'] for r in rows],[str(expected)])
        self.assertFalse(state_root().exists())
        r = self.run_json('fd','--yes')
        self.assertEqual(self.run_json('find')['items'],[])
        self.assertEqual(self.run_json('fd','--yes')['status'],'unchanged')
        self.assertFalse((state_root()/'installation.json').exists())
        self.assertEqual((os.readlink(target),target.stat(follow_symlinks=False).st_ino),original)
        self.undo(r['id'])
        self.assertEqual(self.rows(),[])
        self.assertTrue(target.is_symlink())

    def test_find_path_repeats_and_mixes_with_positional_roots(self):
        outer = self.config/'-scope ü'
        inner = outer/'nested'
        inner.mkdir(parents=True)
        elsewhere = self.home/'another directory'
        elsewhere.mkdir()
        scoped = inner/'existing'
        other = elsewhere/'linked'
        for link in (scoped, other, self.config/'outside the selected roots'):
            link.symlink_to(self.root/'config/app')
        for route in ('find', 'fd'):
            args = (route, '--path', '${CONFIG}/-scope ü', str(elsewhere),
                    '--path=' + str(inner), '--path', str(outer), str(scoped))
            rows = self.run_json(*args, '--dry-run')['items']
            self.assertEqual([r['target'] for r in rows], sorted([str(scoped), str(other)]))
        self.assertFalse(state_root().exists())
        for bad, code in [(str(self.home/'missing'), 1), (str(self.root/'config/app'), 1), ('', 2)]:
            self.files('find', str(outer), '--path', bad, '--yes', code=code)
        self.files('fd','--path',code=2)
        self.files('add',str(scoped),'--path',str(outer),'--yes',code=2)
        self.assertFalse(state_root().exists())
        self.assertEqual(self.rows(), [])
        bash = [str(self.root/'bin/dots'), 'files', 'fd', str(scoped), '--path', str(outer), '--yes', '--json']
        applied = subprocess.run(bash, env=self.env, text=True, capture_output=True, timeout=20)
        self.assertEqual(applied.returncode, 0, applied.stderr)
        self.assertEqual(json.loads(applied.stdout)['status'], 'complete')
        self.assertEqual(self.run_json('find', '--path', str(outer))['items'], [])
        self.assertEqual(len(self.rows()), 1)

    def test_find_path_help_and_directory_completion(self):
        check = self.home/'completion'
        check.mkdir()
        (check/'choice dir').mkdir()
        (check/'choice-file').touch()
        for route in ('find','fd'):
            for frontend in ([str(self.root/'bin/dots')], [sys.executable,'-B',str(self.root/'lib/dots/cli.py')]):
                p = subprocess.run([*frontend,'files',route,'--help'], env=self.env, text=True, capture_output=True, timeout=15)
                self.assertEqual(p.returncode,0,p.stderr)
                self.assertIn('--path',p.stdout)
                self.assertIn('repeat',p.stdout.lower())
            tail = ['dots','files',route,'--path',str(check),'--path',str(check/'choice')]
            for shell in ('bash','zsh','fish','powershell','nu','xonsh'):
                native = shell in ('powershell','nu','xonsh')
                if native:
                    frontend = [sys.executable,'-B',str(self.root/'lib/dots/native_completion.py'),'--complete',shell]
                else:
                    frontend = [str(self.root/'bin/dots'),'__complete',shell,str(len(tail)-1),'--']
                p = subprocess.run([*frontend,*tail], env=self.env, text=True, capture_output=True, timeout=15)
                self.assertEqual(p.returncode,0,p.stderr)
                if native:
                    self.assertEqual([r['value'].rstrip('/\\') for r in json.loads(p.stdout)], [str(check/'choice dir')])
                else:
                    self.assertIn('directory\t',p.stdout)
                    self.assertNotIn('file\t',p.stdout)

    def test_maintenance_route_dispatch_and_metadata(self):
        import base64
        native = [sys.executable, '-B', str(self.root/'lib/dots/native.py'), 'cli']
        for action in ('relink','prune','sync'):
            words = ['files',action,'--json']
            encoded = base64.b64encode(json.dumps(words).encode()).decode('ascii')
            for invocation in ([str(self.root/'bin/dots'),*words], [*native,encoded]):
                result = subprocess.run(invocation,env=self.env,capture_output=True,text=True,timeout=15)
                self.assertEqual(result.returncode,0,result.stderr)
                report = json.loads(result.stdout)
                self.assertEqual((report['action'],report['status']), (action,'preview'))
        self.assertFalse(state_root().exists())
        controller = self.root/'lib/dots/files/maintenance.py'
        controller.write_text('import json, sys\nprint(json.dumps(sys.argv[1:]))\n')
        flags = ['-i','--interactive','--yes','--dry-run','--json','-v','--verbose','--repo','--app','--category']
        for action in ('relink', 'prune', 'sync'):
            args = [action, '-i', '--repo', 'dots', '--category', 'my category', '--app', 'app $(literal)']
            for tail in (args, [action, '--help']):
                argv = ['files', *tail]
                encoded = base64.b64encode(json.dumps(argv).encode()).decode('ascii')
                for invocation in ([str(self.root/'bin/dots'), *argv], [*native, encoded]):
                    result = subprocess.run(invocation, env=self.env, capture_output=True, text=True, timeout=15)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    if tail == args:
                        self.assertEqual(json.loads(result.stdout), args)
                    else:
                        for flag in flags:
                            self.assertIn(flag, result.stdout)
                        self.assertIn('default', result.stdout)

    def list_fixture(self):
        profile = json.loads(self.path.read_text())
        profile['files'] = [dict(id='app', source='${DOTS}/config/app', target='${CONFIG}/app',
                                 app='testapp', category='test-config', strategy='link')]
        self.write(self.path, profile)

    def test_list_alias_routes(self):
        import base64
        self.list_fixture()
        bash = str(self.root/'bin/dots')
        lib = self.root/'lib/dots'
        for flags in (['--json'],['--short'],['--default'],['--view','verbose']):
            outputs = []
            for action in ('list','ls'):
                words = ['files',action,*flags]
                encoded = base64.b64encode(json.dumps(words).encode()).decode('ascii')
                for argv in ([bash,*words], [sys.executable,'-B',str(lib/'native.py'),'cli',encoded]):
                    result = subprocess.run(argv, env=self.env, text=True, capture_output=True, timeout=15)
                    self.assertEqual(result.returncode,0,result.stderr)
                    outputs.append(result.stdout)
            self.assertTrue(outputs[0].strip())
            self.assertEqual(outputs,[outputs[0]]*4)
        result = subprocess.run([bash,'files','ls','-s','--view','verbose'],
                                env=self.env,text=True,capture_output=True,timeout=15)
        self.assertEqual(result.returncode,2)
        self.assertIn('not allowed with argument',result.stderr)
        self.assertFalse(state_root().exists())

    def test_list_view_completion_and_help(self):
        self.list_fixture()
        bash = str(self.root/'bin/dots')
        lib = self.root/'lib/dots'
        from command_metadata import read
        canonical = read(self.root/'bin/dots-files-list')
        alias = read(self.root/'bin/dots-files-ls')
        for field in ('usage','option','argument'):
            self.assertEqual(alias[field],canonical[field])
        for action in ('list','ls'):
            for frontend in ([bash],[sys.executable,'-B',str(lib/'cli.py')]):
                help_view = subprocess.run([*frontend,'files',action,'--help'],env=self.env,text=True,capture_output=True,check=True)
                for flag in ('-s','--short','--default','-v','--verbose','--view','--sort','--status','--all-platforms'):
                    self.assertIn(flag,help_view.stdout)
            for shell in ('bash','zsh','fish','powershell','nu','xonsh'):
                for extra, expected in ((['--'],['--short','--default','--verbose','--view']),
                                        (['--view',''],['short','default','verbose']),
                                        (['--app','test'],['testapp']), (['--category','test'],['test-config'])):
                    words = ['dots','files',action,*extra]
                    if shell in ('bash','zsh','fish'):
                        argv = [bash,'__complete',shell,str(len(words)-1),'--',*words]
                    else:
                        argv = [sys.executable,'-B',str(lib/'native_completion.py'),'--complete',shell,*words]
                    result = subprocess.run(argv, env=self.env, text=True, capture_output=True, timeout=15)
                    with self.subTest(action=action, shell=shell, args=extra):
                        self.assertEqual(result.returncode,0,result.stderr)
                        for value in expected:
                            self.assertIn(value,result.stdout)
        self.assertFalse(state_root().exists())

    def test_maintenance_filter_completions(self):
        profile = json.loads(self.path.read_text())
        profile['files'] = [dict(id='app', source='${DOTS}/config/app',target='${CONFIG}/app',
                                 app='testapp',category='test-config',strategy='link')]
        self.write(self.path, profile)
        for action in ('relink','prune','sync'):
            for shell in ('bash','zsh','fish','powershell','nu','xonsh'):
                for extra, expected in ((['--inter'],'--interactive'), (['--repo','dot'],'dots'),
                                        (['--repo','dots','--app','test'],'testapp'),
                                        (['--category','test'],'test-config')):
                    words = ['dots','files',action,*extra]
                    if shell in ('bash','zsh','fish'):
                        frontend = [str(self.root/'bin/dots'),'__complete',shell,str(len(words)-1),'--']
                    else:
                        frontend = [sys.executable,'-B',str(self.root/'lib/dots/native_completion.py'),'--complete',shell]
                    result = subprocess.run([*frontend,*words], env=self.env, capture_output=True, text=True, timeout=15)
                    with self.subTest(action=action, shell=shell, extra=extra):
                        self.assertEqual(result.returncode, 0, result.stderr)
                        self.assertIn(expected, result.stdout)

    def test_theme_link_find_through_verified_directory(self):
        active, generation = self.published()
        (generation/'yazi').mkdir()
        (generation/'yazi/flavor.toml').write_text('first')
        source_dir = self.root/'config/yazi'
        source_dir.mkdir()
        logical = self.config/'yazi'
        logical.symlink_to(source_dir, target_is_directory=True)
        self.run_json('add',str(logical),'--yes')
        child = logical/'flavor.toml'
        child.symlink_to(active/'yazi/flavor.toml')
        rows = self.run_json('fd')['items']
        self.assertEqual([r['target'] for r in rows],[str(child)])
        self.run_json('find','--yes')
        row = next(r for r in self.rows() if r['source'] == '${THEME}/yazi/flavor.toml')
        self.assertEqual(row['target'],'${CONFIG}/yazi/flavor.toml')
        child.unlink()
        self.run_json('ln','theme:'+row['id'],'--yes')
        self.assertEqual(os.readlink(child), str(active/'yazi/flavor.toml'))
        self.run_json('remove','theme:'+row['id'],'--yes')
        self.assertFalse(child.is_symlink())
        self.assertEqual(child.read_text(),'first')

    def test_find_reuses_source_for_multiple_distinct_destinations(self):
        source = self.root/'config/app'
        for name in ('first', 'second'):
            (self.config/name).symlink_to(source)
        first = self.run_json('find', '--dry-run')['items']
        ids = {r['target']:r['id'] for r in first}
        self.assertEqual(len(set(ids.values())), 2)
        self.run_json('fd','--yes')
        (self.config/'another').symlink_to(source)
        later, = self.run_json('find')['items']
        self.assertNotIn(later['id'], ids.values())
        self.run_json('find','--yes')
        self.assertEqual(self.run_json('find')['items'], [])
        self.assertEqual({r['id'] for r in self.rows()},
                         {i.split(':')[1] for i in [*ids.values(), later['id']]})

    def test_find_respects_generated_directory_ownership_before_migration(self):
        active, generation = self.published()
        (generation/'yazi').mkdir()
        app = self.config/'yazi'
        flavor = app/'flavors/dots.yazi'
        flavor.mkdir(parents=True)
        for name in ('flavor.toml', 'tmtheme.xml'):
            (generation/'yazi'/name).write_text(name)
            (flavor/name).symlink_to(active/'yazi'/name)
        profile = json.loads(self.path.read_text())
        directory = dict(id='yazi', app='yazi', category='theme', strategy='directory-link',
                         source='${THEME}/yazi', target='${CONFIG}/yazi/flavors/dots.yazi')
        self.write(self.path, dict(profile, files=[directory]))
        for managed in (False, True):
            with self.subTest(managed_app=managed):
                if managed:
                    source = self.root/'config/yazi'
                    app.rename(source)
                    app.symlink_to(source, target_is_directory=True)
                    self.run_json('add', str(app), '--yes')
                before = self.rows()
                for args in (('--path', str(app)), ('--path', str(flavor)), (str(flavor/'flavor.toml'),)):
                    self.assertEqual(self.run_json('fd', *args, '--dry-run')['items'], [])
                self.assertEqual(self.run_json('find', str(app), '--yes')['status'], 'unchanged')
                self.assertEqual(self.rows(), before)

    def test_link_generated_directory_and_preserve_its_pointer(self):
        active, generation = self.published()
        (generation/'collection').mkdir()
        target = self.config/'collection'
        self.run_json('ln', '${THEME}/collection', str(target), '--yes')
        self.assertEqual(self.rows()[0]['strategy'], 'directory-link')
        self.assertEqual(os.readlink(target), str(active/'collection'))
        self.assertEqual(self.run_json('fd',str(target))['items'], [])
        whole = self.rows()[0]
        child = dict(whole, id='entry', source=whole['source']+'/entry', target=whole['target']+'/entry',
                     strategy='link')
        (generation/'collection/entry').write_text('color')
        profile = json.loads(self.path.read_text())
        self.write(self.path, dict(profile, files=[child]))
        issue, = self.run_json('fd',str(target))['items']
        self.assertEqual(issue['status'], 'conflict')
        self.assertIn('theme:entry', issue['reason'])

    def test_import_directory_with_explicit_profile_source(self):
        nested = self.config/'sample/nested'
        nested.mkdir(parents=True)
        live = nested/'local.toml'
        live.write_text('color=true')
        self.run_json('add',str(nested.parent),'--source','${PROFILE}/my-config','--yes')
        row, = self.rows()
        self.assertEqual(row['source'], '${PROFILE}/my-config/nested/local.toml')
        self.assertEqual(live.resolve(), self.path.parent/'my-config/nested/local.toml')

    def test_find_application_theme_locations_and_skip_pinned_generation(self):
        active, generation = self.published()
        (generation/'bat.tmTheme').write_text('published')
        for directory in [self.home/'.codex/themes', self.home/'.pi/agent/themes']:
            directory.mkdir(parents=True)
            (directory/'custom.tmTheme').symlink_to(active/'bat.tmTheme')
            (directory/'pinned.tmTheme').symlink_to(generation/'bat.tmTheme')
        (self.home/'outside-scoped-locations').symlink_to(active/'bat.tmTheme')
        rows = self.run_json('fd')['items']
        self.assertEqual({row['target'] for row in rows}, {
            str(self.home/'.codex/themes/custom.tmTheme'), str(self.home/'.pi/agent/themes/custom.tmTheme')})
        self.assertEqual({row['app'] for row in rows}, {'codex', 'pi'})
        self.assertEqual({row['category'] for row in rows}, {'theme'})

    def test_find_conflicts_stay_visible_and_individual_approvals(self):
        from find_links import review
        claimed = self.config/'claimed'
        self.run_json('link','${DOTS}/config/app',str(claimed),'--yes')
        other = self.root/'config/other'
        other.write_text('different')
        claimed.unlink()
        claimed.symlink_to(other)
        ready = self.config/'ready'
        ready.symlink_to(other)
        third = self.config/'third'
        third.symlink_to(self.root/'config/app')
        inventory = self.run_json('find')['items']
        self.assertEqual({r['status'] for r in inventory},{'conflict','register-existing-link'})
        with patch('sys.stdin.isatty', return_value=True), patch('sys.stderr', new=io.StringIO()), \
                patch('find_links.gum_confirm', side_effect=[False, True]) as prompt:
            accepted = review(inventory,False,False)
        self.assertEqual(len(accepted),1)
        self.assertEqual(prompt.call_count,2)
        result = self.run_json('fd','--yes')
        self.assertEqual([r['target'] for r in result['skipped']],[str(claimed)])
        self.assertEqual(claimed.resolve(),other)
        self.assertEqual(len(self.run_json('find')['items']),1)

    def test_find_rechecks_accepted_link_after_review(self):
        import manage
        import find_links
        target = self.config/'under-review'
        target.symlink_to(self.root/'config/app')
        other = self.root/'config/other'
        other.write_text('a different source')
        def changed(found, yes, json_mode):
            target.unlink()
            target.symlink_to(other)
            return found
        with patch.object(sys,'argv',['files','find','--yes','--json']), patch.object(find_links,'review',changed):
            with self.assertRaisesRegex(ValueError,'changed after discovery'):
                manage.main()
        self.assertEqual(self.rows(),[])
        self.assertEqual(target.resolve(),other)

    def test_find_declared_submodule_root_as_one_directory_link(self):
        nested = self.root/'config/editor'
        nested.mkdir()
        (nested/'.git').write_text('gitdir: ../../.git/modules/editor\n')
        (nested/'config').write_text('editor settings')
        source_file = self.root/'.dots/sources.json'
        sources = json.loads(source_file.read_text())
        sources['sources'].append(dict(id='editor',path='config/editor',roots=['.'],platforms=[self.platform]))
        self.write(source_file,sources)
        target = self.config/'editor'
        target.symlink_to(nested, target_is_directory=True)
        view, = self.run_json('fd')['items']
        self.assertEqual((view['repository'],view['strategy']),('editor','directory-link'))
        self.run_json('find','--yes')
        self.assertEqual(self.rows()[0]['source'],'${DOTS}/config/editor')
        self.assertTrue(target.is_symlink())

    def test_bash_entrypoint_aliases_and_option_completions(self):
        for route in ('ln','link'):
            args = [str(self.root/'bin/dots'), 'files', route, '-s', '${DOTS}/config/app', '-t', '${CONFIG}/new', '--dry-run', '--json']
            result = subprocess.run(args, env=self.env, capture_output=True, text=True,timeout=15)
            self.assertEqual(result.returncode, 0,result.stderr)
            self.assertEqual(json.loads(result.stdout)['items'][0]['path'], str(self.config/'new'))
        for route, opt in [('ln','--source'),('fd','--dry-run'),('add','--global')]:
            for shell in ('bash','zsh','fish','powershell','nu','xonsh'):
                if shell in ('bash','zsh','fish'):
                    prefix = [str(self.root/'bin/dots'),'__complete',shell,'3','--']
                else:
                    prefix = [sys.executable,'-B',str(self.root/'lib/dots/native_completion.py'),'--complete',shell]
                result = subprocess.run([*prefix,'dots','files',route,opt[:3]], env=self.env,
                                        capture_output=True, text=True,timeout=15)
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertIn(opt,result.stdout)


if __name__ == '__main__':
    unittest.main(verbosity=2)
