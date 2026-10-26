#!/usr/bin/env python3
"""Isolated managed-destination repair, ownership and recovery acceptance."""
from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import unittest
from unittest.mock import patch

import test_installation as fixtures

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'lib/dots/files'))
import repair
import repair_picker
import transactions
from install import Installation
from transactions import Store, digest


class RepairTests(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.InstallationTests()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.repo, self.home = self.f.repo, self.f.home
        self.source, self.target = self.f.source, self.f.target
        self.env = dict(self.f.env, DOTS_PROGRESS='never', TMPDIR=str(self.f.base))
        self.patch = patch.dict(os.environ, self.env)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.store = Store(self.home / '.state/dots')

    def cli(self, *args, code=0, **env):
        out = subprocess.run([sys.executable, '-B', str(ROOT/'lib/dots/files/repair.py'), *args],
                             env=dict(self.env, **env), capture_output=True, text=True, timeout=30)
        self.assertEqual(out.returncode, code, out.stdout + out.stderr)
        return out

    def doc(self):
        return json.loads((self.repo/'.dots/files.json').read_text())

    def save(self, doc):
        self.f.write('.dots/files.json', doc)

    def plan(self, *args):
        plan = repair.Repair(repair.parser().parse_args(list(args)))
        plan.inspect()
        return plan

    def extra(self, name, **fields):
        doc = self.doc()
        row = dict(doc['resources'][0], id=name, target='${CONFIG}/' + name, **fields)
        doc['resources'].append(row)
        self.save(doc)
        return self.home/'.config'/name

    def link(self, value=None):
        self.target.parent.mkdir(parents=True, exist_ok=True)
        self.target.symlink_to(value or self.source)

    def move_source(self):
        new = self.source.with_name('-new source ü')
        self.source.rename(new)
        doc = self.doc()
        doc['resources'][0]['source'] = new.relative_to(self.repo).as_posix()
        self.save(doc)
        return new

    def undo(self, transaction):
        ops, guards, catalogs = self.store.inverse(transaction)
        self.store.apply('undo', ops, guards, catalogs=catalogs, retain=True)

    def test_preview_forced_json_no_state_and_idempotent_apply(self):
        before = digest(self.repo)
        preview = self.cli('--dry-run', '--yes', '--json', DOTS_COLOR='always', DOTS_ICONS='always').stdout
        self.assertNotIn('\x1b', preview)
        self.assertEqual(json.loads(preview)['items'][0]['outcome'], 'would-link')
        self.assertFalse((self.home/'.state').exists())
        self.assertFalse(self.target.parent.exists())
        output = self.cli('--yes', '--json', '-v', DOTS_COLOR='always', DOTS_ICONS='always').stdout
        self.assertNotIn('\x1b', output)
        applied = json.loads(output)
        self.assertEqual(applied['counts']['repaired'], 1)
        self.assertEqual(self.target.resolve(), self.source)
        self.assertEqual(digest(self.repo), before)
        state = digest(self.home/'.state')
        self.assertEqual(json.loads(self.cli('--yes', '--json').stdout)['status'], 'unchanged')
        self.assertEqual(digest(self.home/'.state'), state)
        self.undo(applied['transaction']['id'])
        self.assertFalse(self.target.is_symlink())
        self.assertFalse((self.home/'.state/dots/installation.json').exists())

    def test_receipt_missing_target_keeps_first_install_backup(self):
        self.target.parent.mkdir(parents=True)
        self.target.write_text('original user file')
        self.f.cli('install', '--yes')
        baseline = self.f.receipt()['entries'][str(self.target)].copy()
        self.target.unlink()
        self.cli('--yes')
        entry = self.f.receipt()['entries'][str(self.target)]
        for key in ('before', 'backup', 'index'):
            self.assertEqual(entry[key], baseline[key])
        self.f.cli('uninstall', '--yes')
        self.assertEqual(self.target.read_text(), 'original user file')

    def test_receipt_broken_link_relink_undo_and_uninstall(self):
        self.target.parent.mkdir(parents=True)
        self.target.write_text('baseline')
        self.f.cli('install', '--yes')
        old_link = os.readlink(self.target)
        new = self.move_source()
        out = json.loads(self.cli('--yes', '--json').stdout)
        self.assertEqual(out['items'][0]['repair_action'], 'relink')
        self.assertEqual(self.target.resolve(), new)
        self.undo(out['transaction']['id'])
        self.assertEqual(os.readlink(self.target), old_link)
        self.assertFalse(self.target.exists())
        self.cli('--yes')
        self.f.cli('uninstall', '--yes')
        self.assertEqual(self.target.read_text(), 'baseline')

    def test_transaction_proof_without_receipt_and_undo_baseline(self):
        self.store.apply('link', [dict(path=str(self.target), link=str(self.source))],
                         {str(self.target): None, str(self.source): digest(self.source)})
        new = self.move_source()
        out = json.loads(self.cli('--yes', '--json').stdout)
        self.assertEqual(self.target.resolve(), new)
        self.undo(out['transaction']['id'])
        self.assertEqual(os.readlink(self.target), str(self.source))
        self.assertFalse(self.target.exists())

    def test_superseded_transaction_is_not_ownership(self):
        self.store.apply('link', [dict(path=str(self.target), link=str(self.source))], {str(self.target): None})
        # A later non-catalog operation writes the same link identity: an old
        # matching digest must not override this newer ownership evidence.
        self.store.apply('theme-connect', [dict(path=str(self.target), link=str(self.source))],
                         {str(self.target): digest(self.target)})
        self.move_source()
        out = json.loads(self.cli('--yes', '--json', code=1).stdout)
        self.assertEqual(out['counts']['eligible'], 0)
        self.assertIn('ownership', out['items'][0]['reason'])
        self.assertFalse(self.plan().findings['dots:example'].resolution)

    def test_receiptless_checkout_relocation_is_not_inferred(self):
        self.store.apply('link', [dict(path=str(self.target), link=str(self.home/'old checkout/config/settings'))],
                         {str(self.target): None})
        out = json.loads(self.cli('--yes', '--json', code=1).stdout)
        self.assertIn('relocation', out['items'][0]['reason'])
        self.assertFalse(self.target.exists())

    def test_receipt_drift_does_not_fall_back_to_history(self):
        self.f.cli('install', '--yes')
        self.target.unlink()
        self.link('foreign missing')
        self.store.apply('link', [dict(path=str(self.target), link='foreign missing')],
                         {str(self.target): digest(self.target)})
        self.cli('--yes', code=1)
        self.assertEqual(os.readlink(self.target), 'foreign missing')

    def test_protected_objects_and_partial_success(self):
        targets = {}
        for name in ('regular', 'directory', 'foreign', 'broken', 'generated'):
            targets[name] = self.extra(name)
        targets['regular'].parent.mkdir(parents=True)
        targets['regular'].write_text('keep local bytes')
        targets['directory'].mkdir()
        targets['foreign'].symlink_to(targets['regular'])
        targets['broken'].symlink_to('unknown missing')
        targets['generated'].symlink_to(self.home/'.state/dots/current/theme/example')
        before = {k: digest(v) for k, v in targets.items()}
        out = json.loads(self.cli('--yes', '--json', code=1).stdout)
        self.assertEqual(out['status'], 'partial')
        self.assertEqual(out['counts']['repaired'], 1)
        self.assertEqual(out['counts']['unresolved'], 5)
        self.assertEqual(before, {k: digest(v) for k, v in targets.items()})

    def test_missing_theme_owned_destination_is_protected(self):
        install = Installation(self.repo)
        install.add('theme:example', self.target, link=self.source)
        install.apply('theme-connect')
        self.target.unlink()
        self.cli('--yes', code=1)
        self.assertFalse(self.target.is_symlink())

    def test_missing_and_symlink_sources_preserve_catalog(self):
        self.source.unlink()
        before = digest(self.repo)
        self.cli('--yes', code=1)
        self.assertEqual(before, digest(self.repo))
        self.source.symlink_to('missing')
        self.cli('--yes', code=1)
        self.assertTrue(self.source.is_symlink())
        self.assertFalse((self.home/'.state').exists())

    def test_directory_link_with_spaces_unicode_and_missing_parents(self):
        doc = self.doc()
        doc['resources'][0].update(source='config/example', strategy='directory-link', target='${CONFIG}/-long ü parent/app')
        self.save(doc)
        self.cli('--yes')
        target = self.home/'.config/-long ü parent/app'
        self.assertTrue(target.is_dir())
        self.assertEqual(target.resolve(), self.source.parent)
        self.f.cli('uninstall', '--yes')
        self.assertFalse(target.is_symlink())

    def test_windows_app_destination_controller_fixture(self):
        import platform_info
        facts = dict(platform_info.detect(), platform='windows', runtime='native', distro='windows', family=[])
        doc = self.doc()
        doc['resources'][0]['target'] = '${APP_CONFIG:yazi}/settings'
        self.save(doc)
        destination = self.home/'Roaming/yazi/config'
        with patch.object(platform_info, 'detect', return_value=facts), patch.dict(os.environ, YAZI_CONFIG_HOME=str(destination)):
            plan = self.plan()
            self.assertEqual(plan.items[0]['target'], str(destination/'settings'))
            plan.apply()
        self.assertTrue((destination/'settings').is_symlink())
        self.assertFalse(self.target.exists())

    def test_disabled_inactive_filters_and_unknown_ids(self):
        disabled = self.extra('disabled', enabled=False)
        doc = self.doc()
        other = next(p for p in ('termux', 'linux', 'wsl', 'windows') if p != repair.platform())
        doc['resources'].append(dict(doc['resources'][0], id='inactive', platforms=[other]))
        self.save(doc)
        out = json.loads(self.cli('dots:disabled', 'dots:inactive', '--dry-run', '--json').stdout)
        self.assertEqual(out['counts']['skipped'], 2)
        self.cli('dots:unknown', '--yes', code=1)
        self.cli('--repo', 'unknown', '--yes', code=1)
        self.cli('androidots:example', '--yes', code=2)
        out = json.loads(self.cli('dots:example', '--app', 'other', '--yes', '--json').stdout)
        self.assertEqual(out['counts']['checked'], 0)
        self.cli('--repo', 'dots', '--app', 'example', '--category', 'config', '--yes')
        self.assertFalse(disabled.exists())

    def test_conflicting_claims_and_copy_strategy(self):
        doc = self.doc()
        doc['resources'].append(dict(doc['resources'][0], id='conflict'))
        self.save(doc)
        out = json.loads(self.cli('--yes', '--json', code=1).stdout)
        self.assertEqual(out['counts']['unresolved'], 2)
        doc['resources'] = [dict(doc['resources'][0], strategy='copy')]
        self.save(doc)
        self.cli('--yes', code=1)
        self.assertFalse((self.home/'.state').exists())

    def test_unavailable_excluded_sources_are_read_only(self):
        sources = json.loads((self.repo/'.dots/sources.json').read_text())
        for name in ('optional', 'private'):
            sources['sources'].append(dict(id=name, path=name, roots=['config'],
                                          platforms=['termux','linux','wsl','windows'], excluded=name=='private'))
        self.f.write('.dots/sources.json', sources)
        out = json.loads(self.cli('--dry-run', '--json').stdout)
        self.assertEqual([s['status'] for s in out['sources']], ['available', 'unavailable', 'excluded'])
        self.assertFalse((self.repo/'optional').exists())
        self.assertFalse((self.home/'.state').exists())

    def test_matching_relative_links_are_not_adopted(self):
        self.link(os.path.relpath(self.source, self.target.parent))
        self.cli('--yes')
        self.assertFalse((self.home/'.state').exists())

    def test_source_target_catalog_and_receipt_drift_refuse_apply(self):
        for field in ('source', 'target', 'catalog', 'receipt'):
            with self.subTest(field=field):
                plan = self.plan()
                if field == 'source': self.source.write_text('changed')
                elif field == 'target':
                    self.target.parent.mkdir(parents=True, exist_ok=True)
                    self.target.write_text('keep')
                elif field == 'catalog':
                    doc = self.doc(); doc['custom'] = True; self.save(doc)
                else:
                    path = self.home/'.state/dots/installation.json'
                    path.parent.mkdir(parents=True)
                    path.write_text('{}')
                with self.assertRaisesRegex(ValueError, 'changed after preview'):
                    plan.apply()
                self.assertFalse(self.target.is_symlink())
                if field == 'target': self.target.unlink()

    def test_target_appearing_while_source_is_hashed_is_never_replaced(self):
        import install
        original = install.digest
        def appear(path):
            if Path(path) == self.source:
                self.target.parent.mkdir(parents=True, exist_ok=True)
                self.target.write_text('appeared during inspection')
            return original(path)
        with patch.object(install, 'digest', appear):
            with self.assertRaisesRegex(ValueError, 'changed after preview'):
                self.plan()
        self.assertEqual(self.target.read_text(), 'appeared during inspection')
        self.assertFalse((self.home/'.state').exists())

    def test_new_transaction_and_changed_evidence_block_apply(self):
        self.store.apply('link', [dict(path=str(self.target), link=str(self.source))], {str(self.target): None})
        self.move_source()
        plan = self.plan()
        self.store.apply('theme-connect', [dict(path=str(self.target), link=os.readlink(self.target))],
                         {str(self.target): digest(self.target)})
        with self.assertRaisesRegex(ValueError, 'history changed'):
            plan.apply()
        self.assertFalse(self.target.exists())

    def test_corrupt_receipt_blocks_other_safe_candidates(self):
        self.f.cli('install', '--yes')
        doc = self.f.receipt()
        del doc['entries'][str(self.target)]['backup']
        (self.home/'.state/dots/installation.json').write_text(json.dumps(doc))
        extra = self.extra('safe')
        self.cli('--yes', code=1)
        self.assertFalse(extra.exists())

    def test_unsafe_parents_and_permissions_preserve_destination(self):
        self.target.parent.parent.mkdir(parents=True)
        self.target.parent.symlink_to(self.source.parent, target_is_directory=True)
        out = json.loads(self.cli('--yes', '--json', code=1).stdout)
        self.assertIn('symlinked parent', out['items'][0]['reason'])
        self.target.parent.unlink()
        original = repair.object_kind
        def denied(path):
            if path == self.source: raise PermissionError('fixture permission denied')
            return original(path)
        with patch.object(repair, 'object_kind', denied):
            plan = self.plan()
        self.assertEqual(plan.items[0]['repair_action'], 'unresolved')
        self.assertFalse(plan.install.operations)

    @unittest.skipIf(os.name == 'nt', 'POSIX special-file fixture')
    def test_special_source_is_never_opened(self):
        self.source.unlink()
        os.mkfifo(self.source)
        self.cli('--yes', code=1)
        self.assertFalse((self.home/'.state').exists())

    def test_failure_rolls_back_links_and_receipt(self):
        self.extra('second')
        plan = self.plan()
        original = transactions.os.rename
        calls = 0
        def fail(source, target):
            nonlocal calls
            calls += 1
            if calls == 2: raise OSError('fixture failure')
            return original(source, target)
        with patch.object(transactions.os, 'rename', fail):
            with self.assertRaisesRegex(OSError, 'fixture failure'):
                plan.apply()
        self.assertFalse(self.target.is_symlink())
        self.assertFalse((self.home/'.config/second').is_symlink())
        self.assertFalse((self.home/'.state/dots/installation.json').exists())
        self.assertEqual(self.store.records()[-1]['status'], 'rolled-back')

    def test_interruption_recovery_and_unfinished_refusal(self):
        script = '''import os,sys
sys.path.insert(0,sys.argv[1])
import repair,transactions
p=repair.Repair(repair.parser().parse_args([]));p.inspect()
original=transactions.os.rename
def crash(a,b):
 original(a,b)
 os._exit(77)
transactions.os.rename=crash
p.apply()
'''
        out = subprocess.run([sys.executable, '-B', '-c', script, str(ROOT/'lib/dots/files')], env=self.env)
        self.assertEqual(out.returncode, 77)
        self.cli('--yes', code=1)
        record = self.store.records()[-1]
        self.store.recover(record['id'])
        self.assertFalse(self.target.is_symlink())
        self.cli('--yes')
        self.assertTrue(self.target.is_symlink())

    def test_undo_refuses_post_repair_drift(self):
        out = json.loads(self.cli('--yes', '--json').stdout)
        self.target.unlink(); self.target.write_text('keep new user settings')
        with self.assertRaises(ValueError): self.undo(out['transaction']['id'])
        self.assertEqual(self.target.read_text(), 'keep new user settings')

    def test_link_capability_refusal_leaves_targets_absent(self):
        plan = self.plan()
        with patch.object(Path, 'symlink_to', side_effect=OSError('no link privilege')):
            with self.assertRaisesRegex(ValueError, 'symbolic links unavailable'):
                plan.apply()
        self.assertFalse(self.target.is_symlink())
        self.assertFalse((self.home/'.state/dots/installation.json').exists())

    def test_confirmation_cancel_eof_and_nonterminal_modes(self):
        self.cli(code=2)
        self.cli('--json', code=2)
        with patch.object(repair, 'terminal', return_value=True), patch.object(repair, 'gum_confirm', return_value=False), redirect_stdout(io.StringIO()):
            self.assertEqual(repair.main([]), 0)
        self.assertFalse((self.home/'.state').exists())
        with patch.object(repair, 'gum_confirm', return_value=None), patch.object(sys, 'stdin', io.StringIO('')):
            with self.assertRaises(KeyboardInterrupt): repair.confirm()
        with patch.object(repair, 'gum_confirm', return_value=None), patch.object(sys, 'stdin', io.StringIO('no\n')):
            self.assertFalse(repair.confirm())

    def test_reported_five_resources_and_explicit_relocation(self):
        platforms = ['termux', 'linux', 'wsl', 'windows']
        base = self.doc()['resources'][0]
        bat, nvim, termux = self.repo/'config/bat', self.repo/'config/nvim', self.repo/'profiles/termux'
        bat.mkdir(); (nvim/'.dots').mkdir(parents=True); (termux/'.dots').mkdir(parents=True)
        self.save(dict(schema=1, repository='dots', resources=[dict(base, id='bat', source='config/bat',
                       target='${CONFIG}/bat', strategy='directory-link', replaces=['termux:bat'])]))
        (nvim/'.dots/files.json').write_text(json.dumps(dict(schema=1, repository='nvim', resources=[
            dict(base, id='nvim', source='.', target='${CONFIG}/nvim', strategy='directory-link', replaces=['termux:nvim'])])))
        rows = []
        for name in ('fastfetch', 'htop', 'pip'):
            (termux/'config'/name).mkdir(parents=True)
            rows.append(dict(base, id=name, source='config/'+name, target='${CONFIG}/'+name, strategy='directory-link'))
        (termux/'.dots/files.json').write_text(json.dumps(dict(schema=1, repository='termux', resources=rows)))
        self.f.write('.dots/sources.json', dict(schema=1, sources=[
            dict(id=name, path=path, roots=['.'], platforms=platforms)
            for name, path in (('dots', '.'), ('nvim', 'config/nvim'), ('termux', 'profiles/termux'))]))
        config = self.home/'.config'; config.mkdir()
        for name, source in (('bat', bat), ('nvim', nvim)):
            (config/name).symlink_to(source, target_is_directory=True)
        old = {}
        for name in ('fastfetch', 'htop', 'pip'):
            old[name] = str(self.repo/'androidots/config'/name)
            (config/name).symlink_to(old[name], target_is_directory=True)
        result = json.loads(self.cli('--yes', '--json', code=1).stdout)
        self.assertEqual(result['counts'], dict(checked=5, eligible=0, repaired=0, unchanged=2, skipped=0, unresolved=3))
        self.assertFalse((self.home/'.state').exists())
        plan = self.plan()
        for name in old:
            self.assertEqual(plan.findings['termux:'+name].issue, 'historical-link')
            plan.select('termux:'+name, 'relink')
        transaction = plan.apply()
        for name in old:
            self.assertEqual((config/name).resolve(), termux/'config'/name)
        self.undo(transaction['id'])
        for name in old:
            self.assertEqual(os.readlink(config/name), old[name])
        self.assertEqual((config/'bat').resolve(), bat)
        self.assertEqual((config/'nvim').resolve(), nvim)

    def test_explicit_file_directory_and_working_link_replacement_and_undo(self):
        self.target.parent.mkdir(parents=True)
        for kind in ('file', 'directory', 'link'):
            with self.subTest(kind=kind):
                if kind == 'file': self.target.write_text('local settings')
                elif kind == 'directory':
                    self.target.mkdir(); (self.target/'-ü settings').write_text('directory contents')
                else:
                    other = self.home/'foreign source'; other.write_text('foreign contents')
                    self.target.symlink_to(other)
                before = digest(self.target)
                plan = self.plan()
                self.assertFalse(plan.install.operations)
                plan.select('dots:example', 'replace-with-backup')
                self.assertEqual(digest(self.target), before)
                self.assertEqual(len(plan.install.operations), 1)
                result = plan.apply()
                self.assertEqual(self.target.resolve(), self.source)
                self.undo(result['id'])
                self.assertEqual(digest(self.target), before)
                if kind == 'directory':
                    (self.target/'-ü settings').unlink(); self.target.rmdir()
                else: self.target.unlink()

    def test_explicit_same_resource_drift_retains_uninstall_baseline(self):
        self.target.parent.mkdir(parents=True); self.target.write_text('first baseline')
        self.f.cli('install', '--yes')
        baseline = self.f.receipt()['entries'][str(self.target)]
        self.target.unlink(); self.target.write_text('edited replacement')
        plan = self.plan(); plan.select('dots:example', 'replace-with-backup')
        result = plan.apply()
        entry = self.f.receipt()['entries'][str(self.target)]
        for key in ('before', 'backup', 'index'): self.assertEqual(entry[key], baseline[key])
        self.undo(result['id'])
        self.assertEqual(self.target.read_text(), 'edited replacement')
        plan = self.plan(); plan.select('dots:example', 'replace-with-backup'); plan.apply()
        self.f.cli('uninstall', '--yes')
        self.assertEqual(self.target.read_text(), 'first baseline')

    def test_manual_choices_reject_target_source_catalog_and_receipt_drift(self):
        self.link(self.home/'old checkout/settings')
        for field in ('source', 'target', 'catalog', 'receipt'):
            with self.subTest(field=field):
                plan = self.plan(); plan.prepare('dots:example')
                if field == 'source': self.source.write_text('changed source')
                elif field == 'target': self.target.unlink(); self.target.write_text('appeared')
                elif field == 'catalog':
                    doc = self.doc(); doc['changed'] = True; self.save(doc)
                else:
                    receipt = self.home/'.state/dots/installation.json'
                    receipt.parent.mkdir(parents=True); receipt.write_text('{}')
                with self.assertRaisesRegex(ValueError, 'changed after preview'):
                    plan.select('dots:example', 'relink')
                self.assertFalse(plan.install.operations)
                if field == 'target': self.target.unlink(); self.link(self.home/'old checkout/settings')

    def test_occupied_directory_content_drift_after_selection_blocks_apply(self):
        self.target.mkdir(parents=True)
        content = self.target/'settings'; content.write_text('before')
        plan = self.plan(); plan.select('dots:example', 'replace-with-backup')
        content.write_text('after')
        with self.assertRaisesRegex(ValueError, 'changed after preview'):
            plan.apply()
        self.assertEqual(content.read_text(), 'after')
        self.assertFalse((self.home/'.state').exists())

    def test_target_replaced_between_scan_and_action_requires_new_review(self):
        self.target.parent.mkdir(parents=True); self.target.write_text('before')
        plan = self.plan()
        self.target.write_text('after')
        with self.assertRaisesRegex(ValueError, 'changed after preview'):
            plan.prepare('dots:example')
        self.assertEqual(self.target.read_text(), 'after')
        self.assertFalse((self.home/'.state').exists())

    def test_hard_blocks_never_offer_a_mutation(self):
        for owner in ('theme:example', 'dots:other'):
            install = Installation(self.repo)
            install.add(owner, self.target, link=self.source, managed=True)
            result = install.apply('install')
            self.target.unlink()
            plan = self.plan()
            self.assertFalse(plan.findings['dots:example'].resolution)
            with self.assertRaisesRegex(ValueError, 'unavailable'):
                plan.select('dots:example', 'link')
            # Restore the link identity before undoing the fixture install.
            self.target.symlink_to(self.source)
            self.undo(result['id'])
        self.link(self.home/'.state/dots/current/theme/settings')
        plan = self.plan()
        self.assertEqual(plan.findings['dots:example'].issue, 'protected-theme')
        self.assertFalse(plan.findings['dots:example'].resolution)
        self.target.unlink()
        self.source.unlink()
        self.assertFalse(self.plan().findings['dots:example'].resolution)

    def scripted(self, choices, *, backend='plain', approve=True):
        selector = repair_picker.RichSelector(backend)
        snapshots = []
        def pick(title, labels, **kwargs):
            if backend == 'fzf':
                preview = kwargs['preview']
                snapshot = Path(preview[2]['DOTS_REPAIR_SNAPSHOT'])
                snapshots.append(snapshot)
                self.assertTrue(snapshot.is_file())
                with redirect_stdout(io.StringIO()) as output:
                    repair_picker.preview(str(snapshot), '2' if len(labels) > 2 else '0')
                self.assertIn('File repair review', output.getvalue())
            value = next(choices)
            if isinstance(value, BaseException): raise value
            return value
        selector.pick = pick
        with patch.object(repair, 'terminal', return_value=True), \
             patch.object(repair_picker, 'RichSelector', return_value=selector), \
             patch.object(repair, 'confirm', return_value=approve) as confirmation, redirect_stdout(io.StringIO()) as output:
            code = repair.main([])
        for snapshot in snapshots: self.assertFalse(snapshot.exists())
        return code, output.getvalue(), confirmation

    def test_helper_queues_reviews_and_applies_one_transaction(self):
        self.link(self.home/'old checkout/settings')
        # Root issue; Relink; root Review; one final approval.
        code, output, confirmation = self.scripted(iter([[2], [2], [1]]), backend='fzf')
        self.assertEqual(code, 0)
        confirmation.assert_called_once()
        self.assertEqual(self.target.resolve(), self.source)
        self.assertEqual(len(self.store.records()), 1)
        self.assertIn('File repair complete', output)

    def test_helper_removes_automatic_and_skips_unresolved(self):
        occupied = self.extra('occupied'); occupied.parent.mkdir(parents=True); occupied.write_text('preserve')
        code, _, confirmation = self.scripted(iter([[2], [1], [3], [1], [1]]))
        self.assertEqual(code, 1)
        confirmation.assert_not_called()
        self.assertFalse(self.target.exists())
        self.assertEqual(occupied.read_text(), 'preserve')
        self.assertFalse((self.home/'.state').exists())

    def test_helper_back_queue_cancel_and_final_cancel_write_nothing(self):
        self.link('old missing')
        for choices, approve in (([[2], [0], [0]], True), ([[2], [2], [0]], True), ([[2], [2], [1]], False)):
            with self.subTest(choices=choices):
                code, output, _ = self.scripted(iter(choices), approve=approve)
                self.assertEqual(code, 0)
                self.assertIn('cancelled', output)
                self.assertEqual(os.readlink(self.target), 'old missing')
                self.assertFalse((self.home/'.state').exists())

    def test_helper_invalid_token_abort_eof_and_backend_failure_write_nothing(self):
        self.link('old missing')
        for result in ([], [99], [-1], [True], [0, 1], repair.SelectionEnded(130), EOFError(), ValueError('tool failed')):
            with self.subTest(result=result):
                expected = type(result) if isinstance(result, BaseException) else ValueError
                with self.assertRaises(expected): self.scripted(iter([result]))
                self.assertFalse((self.home/'.state').exists())
                self.assertEqual(os.readlink(self.target), 'old missing')

    def test_plain_fallback_without_optional_tools_can_apply(self):
        self.link('old missing')
        # Controller entries supply Cancel/Back: issue #3, relink #3, review #2.
        with patch('interaction.shutil.which', return_value=None), \
             patch('interaction.terminal', return_value=True), patch.object(repair, 'terminal', return_value=True), \
             patch('builtins.input', side_effect=['3', '3', '2']), patch.object(repair, 'confirm', return_value=True), \
             redirect_stdout(io.StringIO()):
            self.assertEqual(repair.main([]), 0)
        self.assertEqual(self.target.resolve(), self.source)

    def test_plain_helper_defaults_to_back_then_explicit_cancel(self):
        self.link('old missing')
        with patch('interaction.shutil.which', return_value=None), \
             patch('interaction.terminal', return_value=True), patch.object(repair, 'terminal', return_value=True), \
             patch('builtins.input', side_effect=['3', '', '']), redirect_stdout(io.StringIO()):
            self.assertEqual(repair.main([]), 0)
        self.assertEqual(os.readlink(self.target), 'old missing')
        self.assertFalse((self.home/'.state').exists())

    def test_script_modes_never_open_helper_and_json_shape_is_unchanged(self):
        self.link('old missing')
        with patch.object(repair_picker, 'RepairHelper', side_effect=AssertionError('unexpected helper')), \
             patch.object(repair, 'terminal', return_value=True):
            for args in (['--yes'], ['--dry-run'], ['--dry-run', '--json'], ['--yes', '--json']):
                with redirect_stdout(io.StringIO()) as output:
                    self.assertEqual(repair.main(args), 1)
                if '--json' in args:
                    doc = json.loads(output.getvalue())
                    self.assertEqual(set(doc), {'schema','action','platform','dry_run','status','items','sources','counts'})
                    self.assertNotIn('resolution', doc['items'][0])
        self.assertFalse((self.home/'.state').exists())

    def test_selected_replacements_rollback_in_reverse_order(self):
        self.target.parent.mkdir(parents=True); self.target.write_text('first original')
        second = self.extra('second'); second.write_text('second original')
        plan = self.plan()
        for identity in plan.rows: plan.select(identity, 'replace-with-backup')
        original = transactions.os.rename
        installed = []
        def fail(source, target):
            if Path(target) in (self.target, second):
                installed.append(Path(target))
                if len(installed) == 2: raise OSError('selected fixture failure')
            return original(source, target)
        with patch.object(transactions.os, 'rename', fail):
            with self.assertRaisesRegex(OSError, 'selected fixture failure'): plan.apply()
        self.assertEqual(self.target.read_text(), 'first original')
        self.assertEqual(second.read_text(), 'second original')
        self.assertEqual(self.store.records()[-1]['status'], 'rolled-back')
        self.assertFalse((self.home/'.state/dots/installation.json').exists())

    def test_selected_replacement_abrupt_exit_recovers_original(self):
        self.target.parent.mkdir(parents=True); self.target.write_text('retained original')
        script = '''import os,sys
sys.path.insert(0,sys.argv[1])
import repair,transactions
p=repair.Repair(repair.parser().parse_args([]));p.inspect()
p.select('dots:example', 'replace-with-backup')
original=transactions.os.rename
def crash(a,b):
 original(a,b)
 os._exit(77)
transactions.os.rename=crash
p.apply()
'''
        out = subprocess.run([sys.executable, '-B', '-c', script, str(ROOT/'lib/dots/files')], env=self.env, timeout=30)
        self.assertEqual(out.returncode, 77)
        self.cli('--yes', code=1)
        self.store.recover(self.store.records()[-1]['id'])
        self.assertEqual(self.target.read_text(), 'retained original')
        self.assertFalse((self.home/'.state/dots/installation.json').exists())

    def test_drift_at_final_approval_does_not_rebuild_selected_batch(self):
        self.link('old missing')
        selector = repair_picker.RichSelector('plain')
        with patch.object(repair, 'terminal', return_value=True), \
             patch.object(repair_picker, 'RichSelector', return_value=selector), \
             patch.object(selector, 'pick', side_effect=[[2], [2], [1]]), redirect_stdout(io.StringIO()):
            def approve():
                self.target.unlink(); self.target.write_text('arrived during approval')
                return True
            with patch.object(repair, 'confirm', side_effect=approve):
                with self.assertRaisesRegex(ValueError, 'changed after preview'): repair.main([])
        self.assertEqual(self.target.read_text(), 'arrived during approval')
        self.assertFalse((self.home/'.state').exists())

    def test_helper_partial_selection_preserves_skipped_issue(self):
        self.link('old missing')
        other = self.extra('second'); other.write_text('preserve')
        code, output, confirmation = self.scripted(iter([[2], [2], [3], [1], [1]]), backend='gum')
        self.assertEqual(code, 1)
        self.assertIn('File repair partial', output)
        confirmation.assert_called_once()
        self.assertEqual(self.target.resolve(), self.source)
        self.assertEqual(other.read_text(), 'preserve')

    def test_helper_preview_widths_and_literal_paths(self):
        from resources import cells
        self.link('missing\n\x1b[31m$(touch should-not-run)')
        plan = self.plan(); helper = repair_picker.RepairHelper(plan)
        for width in (40, 80, 120):
            output = io.StringIO(); ui = repair.Presentation(output); ui.width = width
            repair_picker.details(ui, helper.item('dots:example'))
            for line in output.getvalue().splitlines(): self.assertLessEqual(cells(line), width)
            self.assertNotIn('\x1b', output.getvalue())
            self.assertIn('Backup', output.getvalue())
        self.assertFalse((self.repo/'should-not-run').exists())

    @unittest.skipIf(os.name == 'nt', 'POSIX terminal acceptance')
    def test_helper_native_fzf_and_plain_terminal_queue_cancel(self):
        import test_theme_picker as terminal_fixture
        self.link('old missing')
        runner = self.f.base/'repair terminal.py'
        runner.write_text('''import sys
sys.path.insert(0, sys.argv[1])
import repair, repair_picker
selector=repair_picker.RichSelector(sys.argv[2])
repair_picker.RichSelector=lambda: selector
repair.gum_confirm=lambda *a,**kw: None
try:
 raise SystemExit(repair.main([]))
except repair.SelectionEnded as e:
 raise SystemExit(e.status)
''')
        for backend in ('plain', 'fzf'):
            if backend == 'fzf' and not shutil.which('fzf'): continue
            for width in (40, 80, 120):
                with self.subTest(backend=backend, width=width):
                    script = shlex.join([sys.executable, '-B', str(runner), str(ROOT/'lib/dots/files'), backend])
                    steps = ((b'Number', b'3\n'), (b'Number', b'3\n'), (b'Number', b'2\n'), (b'[y/N]', b'n\n'))
                    if backend == 'fzf':
                        steps = ((b'File repair issues:', b'dots:example'), (b'1/3', b'\r'),
                                 (b'Review dots:example:', b'Relink'), (b'1/3', b'\r'),
                                 (b'File repair issues:', b'Review queued'), (b'1/3', b'\r'), (b'[y/N]', b'n\n'))
                    output = terminal_fixture.Picker.terminal(self, script, steps=steps, width=width,
                              env=dict(self.env, TERM='xterm-256color', COLUMNS=str(width)))
                    self.assertIn(b'File repair cancelled', output)
                    self.assertFalse((self.home/'.state').exists())
                    self.assertEqual(os.readlink(self.target), 'old missing')
                    self.assertFalse(list(self.f.base.glob('dots-repair-picker-*')))
            if backend == 'fzf':
                for key in (b'\x1b', b'\x03'):
                    terminal_fixture.Picker.terminal(self, script, steps=((b'File repair issues:', key),), code=130,
                        env=dict(self.env, TERM='xterm-256color'))
                    self.assertFalse((self.home/'.state').exists())

    @unittest.skipIf(os.name == 'nt', 'POSIX terminal acceptance')
    def test_owned_terminal_widths_and_cancel(self):
        import fcntl
        import pty
        import re
        import struct
        import termios
        from resources import cells
        script = '''import sys,time
sys.path.insert(0,sys.argv[1])
import repair
repair.gum_confirm=lambda *a,**kw: None
original=repair.Repair.classify
def slow(self,row):
 time.sleep(0.65)
 return original(self,row)
repair.Repair.classify=slow
raise SystemExit(repair.main(sys.argv[2:]))
'''
        for width in (40, 80, 120):
            for preview in (True, False):
                master, slave = pty.openpty()
                try:
                    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 24, width, 0, 0))
                    child = subprocess.Popen([sys.executable,'-B','-c',script,str(ROOT/'lib/dots/files'),
                                              *(['--dry-run'] if preview else [])],
                                             stdin=slave, stdout=slave, stderr=slave,
                                             env=dict(self.env, TERM='xterm-256color', COLUMNS=str(width),
                                                      DOTS_COLOR='always' if preview else 'never', DOTS_PROGRESS='auto'))
                    os.close(slave); slave = None
                    if not preview: os.write(master, b'n\n')
                    chunks = []
                    while True:
                        try: block = os.read(master, 65536)
                        except OSError: break
                        if not block: break
                        chunks.append(block)
                    self.assertEqual(child.wait(timeout=5), 0)
                    text = b''.join(chunks).decode()
                    plain = re.sub(r'\x1b\[[0-9;]*m', '', text).replace('\r\n', '\n')
                    for line in plain.splitlines(): self.assertLessEqual(cells(line), width, repr(line))
                    self.assertIn('Preview only' if preview else 'cancelled', plain)
                    if preview:
                        self.assertNotIn('\r', text.replace('\r\n', '\n'))
                    else:
                        self.assertIn('\r', text.replace('\r\n', '\n'))
                    self.assertFalse((self.home/'.state').exists())
                finally:
                    os.close(master)
                    if slave is not None: os.close(slave)


if __name__ == '__main__':
    unittest.main()
