"""Truthful compact update names, scoped warning filtering and theme spans."""
import contextlib
import io
import json
import os
import re
import sys
import unittest
from unittest.mock import patch

import test_workflows as fixtures
import test_install_output as install_fixtures
from test_upgrade_output import Terminal
from pkgs_lib import streams, upgrade_output, workflows
from pkgs_lib.backends import Backend
from pkgs_lib.common import Error, Package


class UpgradeSummary(unittest.TestCase):
    setUp = fixtures.Workflows.setUp
    invoke = fixtures.Workflows.invoke
    styled_config = install_fixtures.InstallOutput.styled_config

    def test_native_upgrade_lists_only_changed_installed_versions(self):
        self.styled_config()
        (self.home/'db.json').write_text('{"hello":"1.0","current":"2.0"}')
        result = self.invoke('up','--manager','npm','--global','hello','current')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Updated', result.stdout)
        summary = result.stdout.split('Updated', 1)[1]
        self.assertIn('hello', summary)
        self.assertNotIn('current', summary)
        again = self.invoke('up','--manager','npm','--global','hello','current')
        self.assertEqual(again.returncode, 0, again.stderr)
        self.assertRegex(again.stdout, r'Updated:?\s+none')
        with patch.dict(os.environ, TEST_FAIL='1'):
            failed = self.invoke('up','--manager','npm','hello')
        self.assertEqual(failed.returncode, 42, failed.stderr)
        self.assertNotIn('Updated', failed.stdout)

    def test_system_scope_selected_skipped_and_new_dependencies(self):
        item = workflows.Plan(Backend('apt'), 'upgrade', commands=[['native-upgrade']],
                              skipped=[dict(package='held',reason='policy')])
        before = {'libfoo:arm64':('libfoo:arm64','1'), 'held:arm64':('held:arm64','1'), 'same':('same','1')}
        after = dict(before, **{'libfoo:arm64':('libfoo:arm64','2'), 'held:arm64':('held:arm64','2'),
                               'dependency':('dependency','1')})
        self.assertEqual(workflows.changed_packages(item,before,after), ['libfoo:arm64'])
        item.names = ['same']
        self.assertEqual(workflows.changed_packages(item,before,after), [])
        item.names = ['libfoo']
        self.assertEqual(workflows.changed_packages(item,before,after), ['libfoo:arm64'])
        for manager, old, new in (('pip','Hello_Tool','hello-tool'), ('winget','Vendor.App','vendor.app')):
            backend = Backend(manager)
            with patch.object(backend,'installed',side_effect=[[Package(old,'1')],[Package(new,'2')]]):
                initial, final = workflows.installed_versions(backend), workflows.installed_versions(backend)
            selected = workflows.Plan(backend,'upgrade',names=[old])
            self.assertEqual(workflows.changed_packages(selected,initial,final),[new])

    def test_snapshots_are_bounded_and_unknown_versions_not_guessed(self):
        from pkgs_lib.common import remaining
        backend = Backend('npm')
        def installed():
            self.assertLessEqual(remaining(), 15)
            return [Package('hello','1')]
        with patch.object(backend,'installed',side_effect=installed):
            self.assertEqual(workflows.installed_versions(backend), {'hello':('hello','1')})
        for rows in ([Package('hello')], [Package('hello','1'), Package('hello','2')]):
            with patch.object(backend,'installed',return_value=rows):
                self.assertIsNone(workflows.installed_versions(backend))
        with patch.object(backend,'installed',side_effect=Error('query timed out')):
            self.assertIsNone(workflows.installed_versions(backend))

    def test_inventory_failure_preserves_native_result_and_runs_once(self):
        for snapshots in ((None,), ({}, None)):
            out, err = io.StringIO(), io.StringIO()
            item = workflows.Plan(Backend('npm'),'upgrade',names=['hello'],commands=[['native-upgrade']])
            with patch.object(workflows,'installed_versions',side_effect=snapshots) as inventory, \
                 patch.object(workflows,'apply',return_value=0) as apply, \
                 contextlib.redirect_stdout(out),contextlib.redirect_stderr(err):
                self.assertEqual(workflows.apply_compact(item,self.cfg),0)
            self.assertEqual(apply.call_count,1)
            self.assertEqual(inventory.call_count,len(snapshots))
            self.assertIn('complete',out.getvalue())
            self.assertRegex(out.getvalue(),r'Updated:\s+unavailable')
            self.assertEqual(err.getvalue(),'')
        item = workflows.Plan(Backend('npm'),'upgrade',commands=[['native-upgrade']])
        with patch.object(workflows,'installed_versions',return_value={}) as inventory, \
             patch.object(workflows,'apply',return_value=17),contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(workflows.apply_compact(item,self.cfg),17)
        self.assertEqual(inventory.call_count,1)

    def test_raw_redirect_and_dry_run_add_no_snapshot_queries(self):
        for mode, options in (('auto', []), ('styled', ['--raw']), ('styled', ['--dry-run'])):
            self.styled_config()
            (self.home/'config/pkgs/config.json').write_text(json.dumps({'output':mode}))
            (self.home/'calls.jsonl').unlink(missing_ok=True)
            result = self.invoke('up','--manager','npm','--global','hello',*options)
            self.assertEqual(result.returncode,0,result.stderr)
            path = self.home/'calls.jsonl'
            calls = [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []
            self.assertTrue(all(call[0] != 'ls' for call in calls), calls)
            self.assertNotIn('Updated', result.stdout)

    def test_deprecations_do_not_fill_warning_counts_or_failure_tail(self):
        for action in ('install','upgrade','uninstall'):
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out),contextlib.redirect_stderr(err):
                summary = upgrade_output.Output('npm',self.cfg,action=action)
                formatter = streams.Formatter(err,dict(self.cfg,_manager='npm'),summary)
                for number in range(30):
                    formatter.feed(('npm WARN deprec').encode())
                    formatter.feed(('ated old-'+str(number)+'@1: retired\n').encode())
                formatter.feed(b'npm warn blocked-scripts Important approval needed\n')
                formatter.feed(b'npm error Registry failed\n')
                formatter.feed(b'npm warn deprecated final@1: retired',final=True)
                summary.result(19)
            self.assertIn('Important approval needed',err.getvalue())
            self.assertIn('Registry failed',err.getvalue())
            self.assertNotIn('deprecated',out.getvalue()+err.getvalue())
            self.assertNotIn('more diagnostic',err.getvalue())
            self.assertEqual(summary.extra,0)
            self.assertFalse(any('deprecated' in line for line in summary.tail))
        # Other managers do not acquire npm-specific filtering.
        summary = upgrade_output.Output('pip',self.cfg)
        summary.line('warning: deprecated option','\n',io.StringIO())
        self.assertEqual(summary.warnings,['deprecated option'])

    def test_native_warning_is_still_present_in_raw_and_redirected_output(self):
        self.styled_config()
        fake = self.bin/'npm'
        fake.write_text(fake.read_text().replace("print('warning: fixture detail',file=sys.stderr)",
                                              "print('npm warn deprecated old@1: retired',file=sys.stderr)"))
        for options, mode in (([], 'styled'), (['--raw'],'styled'), ([], 'auto')):
            (self.home/'config/pkgs/config.json').write_text(json.dumps({'output':mode}))
            result = self.invoke('up','--manager','npm','hello',*options)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual('deprecated old@1' in result.stderr, bool(options) or mode=='auto')

    def test_skipped_suffix_uses_theme_foreground_independently(self):
        import style_config
        from resources import cells
        root = self.home/'theme'; (root/'default').mkdir(parents=True)
        profile = root/'profiles/test'; profile.mkdir(parents=True)
        (root/'default/colors.toml').write_text('[ui.muted]\nfg="muted"\n')
        (profile/'colors.toml').write_text('[apps.cli.ui.muted]\nfg="#123456"\n')
        for layers, expected in (([], '38;2;171;205;239'), ([{'root':str(profile)}], '38;2;18;52;86')):
            prefs = style_config.Styles(root, selected={'layers':layers}, palette={'muted':'#abcdef'})
            for width in (40,80,120):
                for mode in ('always','never'):
                    out = Terminal()
                    with patch.object(style_config,'current',return_value=prefs), \
                         patch.dict(os.environ,DOTS_COLOR=mode,DOTS_ICONS='never',COLUMNS=str(width),NO_COLOR='1'), \
                         contextlib.redirect_stdout(out):
                        summary = upgrade_output.Output('pip',self.cfg)
                        summary.updated = ['hello', 'second']
                        summary.result(0,skipped=15)
                    text = out.getvalue();plain = re.sub(r'\x1b\[[0-9;]*m','',text)
                    self.assertIn('complete · 15 skipped',plain)
                    self.assertTrue(all(cells(line)<=width for line in plain.splitlines()),plain)
                    if mode=='always':
                        self.assertIn('\x1b['+expected+'m · 15 skipped\x1b[0m',text)
                        self.assertIn('\x1b[92mcomplete\x1b[0m',text)
                    else:self.assertNotIn('\x1b',text)
            out = Terminal()
            with patch.object(style_config,'current',return_value=prefs), \
                 patch.dict(os.environ,DOTS_COLOR='always',DOTS_ICONS='never',COLUMNS='80'),contextlib.redirect_stdout(out):
                upgrade_output.Output('npm',self.cfg).result(42,skipped=1)
            self.assertIn('\x1b[91mfailed (exit 42)\x1b[0m',out.getvalue())
            self.assertIn('\x1b['+expected+'m · 1 skipped\x1b[0m',out.getvalue())

    def test_exact_npm_notices_are_filtered_without_hiding_other_warnings(self):
        notices = ('npm warn using --force Recommended protections disabled.',
                   'npm warn install-scripts .npmrc allow-scripts setting is being ignored because '
                   '--allow-scripts was passed on the command line')
        summary = upgrade_output.Output('npm', self.cfg)
        out, err = io.StringIO(), io.StringIO()
        formatter = streams.Formatter(err, dict(self.cfg, _manager='npm'), summary)
        for line in notices * 10:
            for byte in (line+'\n').encode(): formatter.feed(bytes([byte]))
        formatter.feed(b'npm warn using --force Different warning\n')
        formatter.feed(b'npm error actual failure\n')
        formatter.feed(notices[-1].encode(), final=True)
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err): summary.result(1)
        self.assertIn('Different warning', err.getvalue())
        self.assertIn('actual failure', err.getvalue())
        self.assertNotIn('Recommended protections', err.getvalue())
        self.assertNotIn('allow-scripts', err.getvalue())
        self.assertEqual(summary.extra, 0)
        self.assertEqual(list(summary.tail), ['npm warn using --force Different warning', 'npm error actual failure'])
        self.styled_config()
        fake = self.bin/'npm'
        fake.write_text(fake.read_text().replace("print('warning: fixture detail',file=sys.stderr)",
                        ';'.join('print('+repr(line)+',file=sys.stderr)' for line in notices)))
        for options, mode in (([], 'styled'), (['--raw'], 'styled'), ([], 'auto')):
            (self.home/'config/pkgs/config.json').write_text(json.dumps({'output': mode}))
            result = self.invoke('up', '--manager', 'npm', 'hello', *options)
            self.assertEqual(result.returncode, 0, result.stderr)
            for line in notices: self.assertEqual(line in result.stderr, bool(options) or mode=='auto')

    def test_yellow_is_palette_color_only_for_package_identities(self):
        import style_config
        from resources import cells
        from progress import Progress
        root = self.home/'theme'; (root/'default').mkdir(parents=True)
        (root/'default/colors.toml').write_text('[status.warning]\nfg="#aa0000"\n[ui.identity]\nfg="#00aa00"\n')
        for palette, expected in (({'yellow':'#abcd12'}, '38;2;171;205;18'), ({}, '38;5;3')):
            prefs = style_config.Styles(root, selected={'layers':[]}, palette=palette)
            cfg = dict(self.cfg)
            with patch.object(style_config, 'current', return_value=prefs):
                for width in (40,80,120):
                    for mode in ('always','never','auto'):
                        out = Terminal()
                        with patch.dict(os.environ, DOTS_COLOR=mode, DOTS_ICONS='never', COLUMNS=str(width), NO_COLOR='1'), contextlib.redirect_stdout(out):
                            for label in ('Installed','Removed','Updated','Scripts','Scripts ran','Scripts blocked'):
                                upgrade_output.packages(cfg,label,['first','@scope/very-long-package-identity@1.2.3'])
                            upgrade_output.packages(cfg,'Failed',['broken (exit 1)'])
                            upgrade_output.packages(cfg,'Updated',['none'],placeholder=True)
                            upgrade_output.packages(cfg,'Updated',['unavailable'],placeholder=True)
                        text=out.getvalue(); plain=re.sub(r'\x1b\[[0-9;]*m','',text)
                        self.assertTrue(all(cells(line)<=width for line in plain.splitlines()),plain)
                        if mode=='always':
                            self.assertIn('\x1b['+expected+'mfirst\x1b[0m, ',text)
                            self.assertIn('\x1b['+expected+'mbroken\x1b[0m (exit 1)',text)
                            for neutral in ('none','unavailable',', ', ' (exit 1)'):
                                self.assertNotIn('\x1b['+expected+'m'+neutral,text)
                        else: self.assertNotIn('\x1b',text)
                meter=Progress(''); summary=upgrade_output.Output('pip',cfg,meter)
                summary.package='package'; summary.stage='Building'; summary.last_activity=0
                with patch.object(style_config,'current',side_effect=AssertionError('theme read during tick')):
                    summary.tick(now=65)
                    self.assertEqual(meter.state[0], (('pip · 1:05 · Building',None),(' · ',None),('package',expected)))
                    summary.last_activity=65; summary.tick(now=65)
                    self.assertNotIn('1:05',str(meter.state))


if __name__ == '__main__': unittest.main()
