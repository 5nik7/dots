#!/usr/bin/env python3
"""Profile-scoped relink, prune and sync, exercised against disposable checkouts."""
from contextlib import redirect_stderr, redirect_stdout
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import unittest
from unittest.mock import patch

import test_profile_backend as fixtures
from file_platform import state_root
from transactions import Store, digest


class FileMaintenance(unittest.TestCase):
    write = fixtures.ProfileBackend.write
    files = fixtures.ProfileBackend.files
    undo = fixtures.ProfileBackend.undo

    def setUp(self):
        fixtures.ProfileBackend.setUp(self)
        for path in self.root.glob('profiles/*/profile.json'):
            self.write(path, dict(schema=1, id=path.parent.name, files=[]))
        self.config = Path(self.env['XDG_CONFIG_HOME'])
        self.config.mkdir()
        self.state = state_root()
        self.env.update(DOTS_COLOR='always', DOTS_ICONS='always', DOTS_PROGRESS='never')

    def row(self, name, **changes):
        fields = dict(id=name, source='${DOTS}/config/' + name, target='${CONFIG}/' + name,
                      app='editor', category='config', strategy='link')
        return dict(fields, **changes)

    def save(self, *rows):
        self.write(self.path, dict(schema=1, id=self.platform, files=list(rows)))

    def json(self, action, *args, code=0):
        result = self.files(action, *args, '--json', code=code)
        self.assertNotIn('\x1b', result.stdout)
        doc = json.loads(result.stdout)
        self.assertEqual((doc['schema'], doc['action']), (1, action))
        return doc

    def planned(self, action):
        import maintenance
        plan = maintenance.Maintenance(maintenance.parser().parse_args([action, '--yes']))
        plan.inspect()
        return plan

    @unittest.skipIf(os.name == 'nt', 'POSIX terminal width fixture')
    def test_plain_terminal_preview_summary_at_three_widths(self):
        import errno
        import fcntl
        import pty
        import struct
        import termios
        self.save(self.row('app'))
        for width in (40, 80, 120):
            with self.subTest(width=width):
                master, slave = pty.openpty()
                try:
                    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 24, width, 0, 0))
                    env = dict(self.env, TERM='xterm-256color', COLUMNS=str(width),
                               DOTS_COLOR='never', DOTS_ICONS='never')
                    result = subprocess.run([sys.executable, '-B', str(self.root/'lib/dots/cli.py'),
                                             'files', 'sync'], stdin=subprocess.DEVNULL, stdout=slave,
                                            stderr=subprocess.PIPE, env=env, timeout=25)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    os.close(slave)
                    slave = None
                    output = bytearray()
                    while True:
                        try:
                            chunk = os.read(master, 8192)
                        except OSError as error:
                            if error.errno != errno.EIO:
                                raise
                            break
                        if not chunk:
                            break
                        output.extend(chunk)
                finally:
                    if slave is not None:
                        os.close(slave)
                    os.close(master)
                lines = output.decode().splitlines()
                self.assertTrue(all(len(line) <= width for line in lines), lines)
                for label in ('Files sync preview', 'dots:app', '1 checked', '1 to link', '--yes', '-i'):
                    self.assertIn(label, '\n'.join(lines))
        self.assertFalse(self.state.exists())

    def projection(self):
        winner = self.row('app', target='${CONFIG}/shared')
        absent = self.row('absent', target=winner['target'])
        self.save(absent, winner)
        return self.config/'shared', winner, absent

    def test_default_preview_apply_repeat_and_one_step_undo(self):
        directory = self.root/'config'/'-settings ü'
        directory.mkdir()
        (directory/'settings').write_text('managed\n')
        row = self.row('settings-dir', source='${DOTS}/config/-settings ü',
                       target='${CONFIG}/-settings ü', strategy='directory-link')
        self.save(self.row('app'), row)
        target = self.config/'-settings ü'
        profile, registry = self.path.read_bytes(), self.registry.read_bytes()
        for flags in [(), ('--dry-run', '-v')]:
            preview = self.json('relink', *flags)
            self.assertEqual(preview['status'], 'preview')
            self.assertEqual({r['outcome'] for r in preview['items']}, {'would-link'})
            self.assertTrue(preview['dry_run'])
        frontend = ([sys.executable, '-B', str(self.root/'lib/dots/cli.py')] if os.name == 'nt'
                    else [str(self.root/'bin/dots')])
        human = subprocess.run([*frontend, 'files', 'relink'], env=self.env,
                               capture_output=True, text=True, timeout=30)
        self.assertEqual(human.returncode, 0, human.stderr)
        self.assertIn('relink', human.stdout.lower())
        self.assertFalse(os.path.lexists(target))
        self.assertFalse(self.state.exists())
        applied = self.json('relink', '--yes')
        self.assertEqual({r['outcome'] for r in applied['items']}, {'linked'})
        self.assertEqual(target.resolve(), directory)
        self.assertEqual((target/'settings').read_text(), 'managed\n')
        self.assertEqual((self.config/'app').resolve(), self.root/'config/app')
        self.assertEqual((self.path.read_bytes(), self.registry.read_bytes()), (profile, registry))
        ids = [r['id'] for r in Store(self.state).records()]
        self.assertEqual(self.json('relink','--yes')['status'], 'unchanged')
        self.assertEqual([r['id'] for r in Store(self.state).records()], ids)
        self.undo(applied['transaction']['id'])
        self.assertFalse(os.path.lexists(target))
        self.assertFalse(os.path.lexists(self.config/'app'))
        self.assertTrue(directory.is_dir())

    def test_prune_keeps_unavailable_broken_and_generated_sources_and_all_targets(self):
        sources = self.root/'.dots/sources.json'
        composition = json.loads(sources.read_text())
        composition['sources'].append(dict(id='optional', path='optional', roots=['config'],
                                           platforms=[self.platform], optional=True))
        self.write(sources, composition)
        broken = self.root/'config/broken'
        broken.symlink_to('gone')
        missing = self.row('absent')
        missing_copy = self.row('missing-copy', strategy='copy')
        rows = [self.row('app'), self.row('broken'), self.row('copy', strategy='copy'),
                self.row('optional', source='${DOTS}/optional/config/tool'),
                self.row('colors', source='${THEME}/colors.json')]
        dangling = self.config/'absent'
        dangling.symlink_to(self.root/'config/absent')
        copied = self.config/'copy'
        copied.write_text('user copy\n')
        (self.root/'config/copy').write_text('new repository contents\n')
        (self.config/'missing-copy').write_text('only surviving copy\n')
        self.save(*rows, missing, missing_copy)
        before = self.path.read_bytes(), self.registry.read_bytes(), digest(self.config)
        preview = self.json('prune')
        self.assertEqual({r['id'] for r in preview['items'] if r['operation'] == 'prune'},
                         {'dots:absent','dots:missing-copy'})
        self.assertFalse(self.state.exists())
        applied = self.json('prune','--yes')
        self.assertEqual(json.loads(self.path.read_text())['files'], rows)
        self.assertEqual((self.registry.read_bytes(),digest(self.config)), before[1:])
        self.assertFalse(dangling.exists())
        self.assertTrue(dangling.is_symlink())
        self.assertTrue(broken.is_symlink())
        self.assertEqual(copied.read_text(), 'user copy\n')
        self.assertEqual((self.config/'missing-copy').read_text(), 'only surviving copy\n')
        self.assertEqual(self.json('prune','--yes')['status'], 'unchanged')
        self.undo(applied['transaction']['id'])
        self.assertEqual(json.loads(self.path.read_bytes()), json.loads(before[0]))
        self.assertEqual((self.registry.read_bytes(), digest(self.config)), before[1:])

    def test_filters_preserve_healthy_unowned_and_other_mappings(self):
        self.save(self.row('app'), self.row('healthy'), self.row('occupied'), self.row('broken'),
                  self.row('profile', source='${PROFILE}/config/other'), self.row('copy', strategy='copy'),
                  self.row('other-app', app='other'), self.row('script', category='script'))
        for name in ('healthy','occupied','broken','copy','other-app','script'):
            (self.root/'config'/name).write_text(name)
        healthy = self.config/'healthy'
        healthy.symlink_to(os.path.relpath(self.root/'config/healthy', self.config))
        occupied = self.config/'occupied'
        occupied.write_text('my bytes\n')
        foreign = self.config/'broken'
        foreign.symlink_to('foreign-missing')
        before = tuple(digest(p) for p in (healthy, occupied, foreign))
        flags = ('--repo','dots','--app','editor','--category','config')
        result = self.json('relink', *flags, '--yes', code=1)
        ops = {r['id']: r['operation'] for r in result['items']}
        self.assertEqual(set(ops), {'dots:'+n for n in ('app','healthy','occupied','broken','copy')})
        self.assertEqual(ops['dots:healthy'], 'unchanged')
        self.assertEqual([ops['dots:'+n] for n in ('occupied','broken')], ['unresolved','unresolved'])
        self.assertEqual((self.config/'app').resolve(), self.root/'config/app')
        self.assertEqual(tuple(digest(p) for p in (healthy, occupied, foreign)), before)
        for name in ('other-app','script','profile','copy'):
            self.assertFalse(os.path.lexists(self.config/name))

    def test_verified_dangling_link_retargets_and_undo_restores_spelling(self):
        self.save(self.row('app'))
        first = self.json('relink','--yes')
        target = self.config/'app'
        previous = target.readlink()
        original = self.root/'config/app'
        moved = original.with_name('-renamed ü')
        original.rename(moved)
        self.save(self.row('app', source='${DOTS}/config/-renamed ü'))
        self.assertFalse(target.exists())
        self.assertEqual(self.json('relink')['items'][0]['outcome'], 'would-relink')
        applied = self.json('relink','--yes')
        self.assertEqual(applied['items'][0]['outcome'], 'relinked')
        self.assertEqual(target.resolve(), moved)
        self.undo(applied['transaction']['id'])
        self.assertEqual(target.readlink(), previous)
        self.assertFalse(target.exists())
        self.undo(first['transaction']['id'])
        self.assertFalse(os.path.lexists(target))

    def test_generated_publication_and_pinned_target(self):
        self.save(self.row('colors', source='${THEME}/colors.json'))
        target = self.config/'colors'
        self.json('relink','--yes')
        self.assertFalse(self.state.exists())
        active = self.state/'current/theme'
        generation = self.state/'themes/generations/g.maintenance'
        generation.mkdir(parents=True)
        (generation/'status').write_text('committed\n')
        (generation/'colors.json').write_text('{}')
        (self.state/'themes/current').write_text(generation.name+'\n')
        active.parent.mkdir()
        active.symlink_to(generation, target_is_directory=True)
        plan = self.planned('relink')
        token = self.state/'themes/current'
        token.write_text('g.changed\n')
        with self.assertRaises(ValueError):
            plan.apply()
        self.assertFalse(os.path.lexists(target))
        token.write_text(generation.name+'\n')
        result = self.json('sync','--yes')
        self.assertEqual(target.readlink(), active/'colors.json')
        self.undo(result['transaction']['id'])
        target.symlink_to(generation/'colors.json')
        self.json('relink','--yes',code=1)
        self.assertEqual(target.readlink(), generation/'colors.json')

    def test_prune_removed_stashed_and_replaced_declarations_preserves_winner(self):
        losing = self.row('missing', source='${PROFILE}/config/missing', target='${CONFIG}/app')
        winning = self.row('app', replaces=[self.platform + ':missing'])
        stashed = self.row('stashed', enabled=False)
        self.save(losing, winning, stashed)
        self.json('relink','--yes')
        target = self.config/'app'
        receipt = self.state/'installation.json'
        original = digest(target), receipt.read_bytes(), self.path.read_bytes()
        preview = self.json('prune')
        self.assertEqual({r['id'] for r in preview['items'] if r['operation'] == 'prune'},
                         {'dots:stashed', self.platform + ':missing'})
        applied = self.json('prune','--yes')
        self.assertEqual(json.loads(self.path.read_text())['files'], [winning])
        self.assertEqual((digest(target), receipt.read_bytes()), original[:2])
        self.undo(applied['transaction']['id'])
        self.assertEqual((digest(target), receipt.read_bytes()), original[:2])
        self.assertEqual(json.loads(self.path.read_bytes()), json.loads(original[2]))

    def test_sync_reclassifies_conflict_after_prune_and_undoes_both(self):
        target, winner, _ = self.projection()
        original = self.path.read_bytes()
        self.json('relink','--dry-run',code=1)
        for flags in [(), ('--dry-run',)]:
            planned = self.json('sync', *flags)
            self.assertEqual({(r['id'],r['outcome']) for r in planned['items']},
                             {('dots:app','would-link'),('dots:absent','would-prune')})
        self.assertFalse(self.state.exists())
        result = self.json('sync','--yes')
        self.assertEqual(target.resolve(), self.root/'config/app')
        self.assertEqual(json.loads(self.path.read_text())['files'], [winner])
        self.assertEqual(len(Store(self.state).records()), 1)
        self.assertEqual(self.json('sync','--yes')['status'], 'unchanged')
        self.undo(result['transaction']['id'])
        self.assertEqual(json.loads(self.path.read_bytes()), json.loads(original))
        self.assertFalse(os.path.lexists(target))

    def test_sync_rejects_drift_and_rolls_back_partial_failure(self):
        import transactions
        target, _, _ = self.projection()
        profile = self.path.read_bytes()
        plan = self.planned('sync')
        appeared = self.root/'config/absent'
        appeared.write_text('arrived after preview')
        with self.assertRaises(ValueError):
            plan.apply()
        self.assertEqual(self.path.read_bytes(), profile)
        self.assertFalse(os.path.lexists(target))
        self.assertFalse(self.state.exists())
        appeared.unlink()
        plan = self.planned('sync')
        rename = os.rename
        published = []
        def fail_second(source, destination):
            if str(source).startswith(str(destination)+'.dots-new-') and len(published) < 2:
                published.append(destination)
                if len(published) == 2:
                    raise OSError('fixture failure during second publication')
            return rename(source, destination)
        with patch.object(transactions.os, 'rename', side_effect=fail_second):
            with self.assertRaisesRegex(OSError, 'fixture failure'):
                plan.apply()
        self.assertEqual(len(published), 2)
        self.assertEqual(self.path.read_bytes(), profile)
        self.assertFalse(os.path.lexists(target))
        self.assertFalse((self.state/'installation.json').exists())
        self.assertEqual([r['status'] for r in Store(self.state).records()], ['rolled-back'])

    def test_identical_regular_files_keep_restorable_originals(self):
        from backup_catalog import BackupPlan
        names = ('identical','empty','edited','working-link')
        self.save(*(self.row(name) for name in names))
        original = b'\x00\r\n\xff' * 16385
        for name in names:
            source, target = self.root/'config'/name, self.config/name
            source.write_bytes(b'' if name == 'empty' else original)
            if name == 'working-link':
                target.symlink_to(self.config/'identical')
            else:
                target.write_bytes((original[:-1] + b'!') if name == 'edited' else source.read_bytes())
                if os.name != 'nt':
                    source.chmod(0o600)
                    target.chmod(0o640)
        before = {name: digest(self.config/name) for name in names}
        original_mode = stat.S_IMODE((self.config/'identical').stat().st_mode)
        preview = self.json('relink', code=1)
        self.assertEqual({r['id'] for r in preview['items'] if r['outcome'] == 'would-relink'},
                         {'dots:identical','dots:empty'})
        self.assertFalse(self.state.exists())
        applied = self.json('relink','--yes',code=1)
        self.assertEqual({r['id'] for r in applied['items'] if r['outcome'] == 'relinked'},
                         {'dots:identical','dots:empty'})
        backup = BackupPlan(self.state)
        for name in ('identical', 'empty'):
            target = self.config/name
            self.assertEqual(target.resolve(), self.root/'config'/name)
            copies = [row for row in backup.document['entries'].values() if row['original'] == str(target)]
            self.assertEqual(len(copies), 1)
            self.assertEqual(digest(backup.verified_payload(copies[0])), before[name])
        for name in ('edited', 'working-link'):
            self.assertEqual(digest(self.config/name), before[name])
        self.undo(applied['transaction']['id'])
        self.assertEqual({name: digest(self.config/name) for name in names}, before)
        self.assertEqual(stat.S_IMODE((self.config/'identical').stat().st_mode), original_mode)

    def test_edit_to_reviewed_identical_file_cancels_apply(self):
        self.save(self.row('app'))
        source, target = self.root/'config/app', self.config/'app'
        target.write_bytes(source.read_bytes())
        plan = self.planned('relink')
        target.write_bytes(b'edited\n')
        with self.assertRaises(ValueError):
            plan.apply()
        self.assertFalse(target.is_symlink())
        self.assertEqual(target.read_bytes(), b'edited\n')
        self.assertEqual(Store(self.state).records(), [])

    def test_inherited_prune_masks_current_leaf_and_does_not_repeat(self):
        import maintenance
        from platform_info import detect
        base = self.root/'profiles/linux'
        middle = base/'distros/family'
        leaf = base/'distros/system'
        middle.mkdir(parents=True)
        leaf.mkdir()
        inherited = self.row('gone', source='${PROFILE}/config/gone')
        self.write(base/'profile.json', dict(schema=1,id='linux',files=[inherited]))
        self.write(middle/'profile.json', dict(schema=1,id='linux/family',files=[]))
        self.write(leaf/'profile.json', dict(schema=1,id='linux/system',extends=['linux/family'],files=[]))
        parents = [base/'profile.json', middle/'profile.json', self.registry]
        before = [p.read_bytes() for p in parents]
        old_leaf = (leaf/'profile.json').read_bytes()
        facts = dict(detect(), platform='linux', distro='system', family=['family'], runtime='linux')
        def run(*args):
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertIn(maintenance.main(['prune','--json',*args]), (None, 0))
            return json.loads(output.getvalue())
        with patch('platform_info.detect', return_value=facts):
            self.assertEqual(run()['profile'], 'linux/system')
            applied = run('--yes')
            self.assertEqual([p.read_bytes() for p in parents], before)
            mask = json.loads((leaf/'profile.json').read_text())['files']
            self.assertEqual(mask, [dict(inherited, source='${DOTS}/profiles/linux/config/gone', enabled=False)])
            self.assertFalse(any(r['operation'] == 'prune' for r in run()['items']))
            self.assertEqual(run('--yes')['status'], 'unchanged')
            self.assertEqual(len(Store(self.state).records()), 1)
            self.undo(applied['transaction']['id'])
        self.assertEqual(json.loads((leaf/'profile.json').read_bytes()), json.loads(old_leaf))
        self.assertEqual([p.read_bytes() for p in parents], before)

    def test_submodule_availability_and_ordinary_empty_owner(self):
        import shutil
        git = shutil.which('git')
        if git is None:
            self.skipTest('Git fixture for submodule initialization')
        sources = self.root/'.dots/sources.json'
        document = json.loads(sources.read_text())
        for owner in ('module', 'ordinary'):
            (self.root/owner).mkdir()
            document['sources'].append(dict(id=owner, path=owner, roots=['.'], platforms=[self.platform]))
        self.write(sources, document)
        (self.root/'.gitmodules').write_text('[submodule "registered"]\n\tpath = module\n')
        self.save(*(self.row(owner, source='${DOTS}/'+owner+'/missing') for owner in ('module','ordinary')))
        initial = self.path.read_bytes()
        preview = self.json('sync')['items']
        self.assertEqual({r['repository']: r['operation'] for r in preview},
                         {'module':'skipped', 'ordinary':'prune'})
        module = self.root/'module'
        subprocess.run([git, 'init', '--quiet', str(module)], check=True, env=self.env, capture_output=True)
        plan = self.planned('prune')
        self.assertEqual(plan.prunes, {'module:module', 'ordinary:ordinary'})
        (module/'.git').rename(self.home/'removed-git-directory')
        with self.assertRaisesRegex(ValueError, 'changed after preview'):
            plan.apply()
        self.assertEqual(self.path.read_bytes(), initial)
        self.assertFalse(self.state.exists())

    def test_interactive_selection_reprojects_then_requires_final_approval(self):
        import maintenance
        target, winner, _ = self.projection()
        original = self.path.read_bytes()
        def choose(answers):
            with patch.object(maintenance, 'terminal', return_value=True), \
                    patch.object(maintenance, 'confirm', side_effect=answers) as decisions, \
                    redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                code = maintenance.main(['sync','--interactive'])
            self.assertEqual(decisions.call_count, len(answers))
            return code
        # Declining the missing declaration keeps both claimants in conflict. No
        # link proposal or final approval prompt should follow that single answer.
        choose([False])
        self.assertEqual(self.path.read_bytes(), original)
        self.assertFalse(os.path.lexists(target))
        self.assertFalse(self.state.exists())
        with self.assertRaises(KeyboardInterrupt):
            choose([True, KeyboardInterrupt()])
        self.assertEqual(self.path.read_bytes(), original)
        self.assertFalse(self.state.exists())
        self.assertIn(choose([True,True,False]), (None,0))
        self.assertEqual(self.path.read_bytes(), original)
        self.assertFalse(os.path.lexists(target))
        self.assertFalse(self.state.exists())
        self.assertIn(choose([True,False,True]), (None,0))
        self.assertEqual(json.loads(self.path.read_text())['files'], [winner])
        self.assertFalse(os.path.lexists(target))

    def test_interactive_cli_rejects_nonterminal_and_conflicting_modes(self):
        self.save(self.row('app'))
        for route in ('relink','prune','sync'):
            for extra in ((), ('--yes',), ('--json',), ('--dry-run',)):
                with self.subTest(route=route, flags=extra):
                    self.files(route, '-i', *extra, code=2)
        self.assertFalse(os.path.lexists(self.config/'app'))
        self.assertFalse(self.state.exists())


if __name__ == '__main__':
    unittest.main()
