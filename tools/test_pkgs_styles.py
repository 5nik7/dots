#!/usr/bin/env python3
"""Package Config bindings and actual consumers in disposable roots."""
import contextlib
import io
import json
import os
from pathlib import Path
import re
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import test_style_config as fixtures
from style_config import Styles
import style_config
from style_catalog import PKGS
from resources import cells

sys.path.insert(0,str(fixtures.ROOT/'plugins/pkgs'))
from pkgs_lib import presentation, reports, ui, upgrade_output, streams, workflows, outdated, manifests, grammar
from pkgs_lib.common import Package
from pkgs_lib.backends import Backend
from progress import Progress


class Terminal(io.StringIO):
    def isatty(self): return True


class PackageStyles(unittest.TestCase):
    setUp=fixtures.StyleConfig.setUp
    run_config=fixtures.StyleConfig.run_config

    def test_canonical_config_save_get_explain_reset_and_no_publication(self):
        key='colors.apps.pkgs.package.fg'
        self.assertEqual(self.run_config('get',key).stdout,'accent\n')
        before=self.path.read_bytes()
        self.run_config('set',key,'#123456','--dry-run','--json')
        self.assertEqual(self.path.read_bytes(),before)
        result=json.loads(self.run_config('set',key,'#123456','--json').stdout)
        self.assertEqual(self.run_config('get',key,native=True).stdout,'#123456\n')
        self.assertFalse((self.home/'state/dots/current/theme').exists())
        explained=json.loads(self.run_config('explain',key,'--json').stdout)
        self.assertEqual(explained['consumers'][0]['refresh'],'next invocation')
        self.assertEqual(explained['consumers'][0]['resolved_color'],'#123456')
        self.run_config('unset',key)
        self.assertEqual(self.run_config('get',key).stdout,'accent\n')
        self.run_config('set','colors.apps.pkgs.progress.bg','#010203',native=True)
        self.run_config('set','colors.apps.pkgs.package.bold','true')
        key='colors.apps.pkgs.manager.fg'
        self.assertEqual(self.run_config('get',key).stdout,'magenta\n')
        self.run_config('set',key,'#234567','--json')
        self.assertEqual(self.run_config('get',key,native=True).stdout,'#234567\n')
        explained=json.loads(self.run_config('explain',key,'--json').stdout)
        self.assertEqual(explained['consumers'][0]['refresh'],'next invocation')
        self.assertEqual(explained['consumers'][0]['resolved_color'],'#234567')
        self.run_config('unset',key)
        self.assertEqual(self.run_config('get',key).stdout,'magenta\n')
        self.run_config('check',native=True)

    def test_every_role_reaches_reports_previews_streams_and_progress(self):
        profile=self.path.parent/'colors.toml'
        profile.write_text('\n'.join('[apps.pkgs.'+role+']\nfg="#123456"\nbg="#654321"\nbold=true\ndim=false\n' for role in PKGS))
        prefs=Styles(self.root,selected={'layers':[{'root':str(profile.parent)}]},palette={'accent':'#abcdef'})
        expected='0;1;38;2;18;52;86;48;2;101;67;33'
        with patch.object(style_config,'current',return_value=prefs):
            for role in PKGS:self.assertEqual(presentation.styles()[role],expected,role)
            for width in (40,80,120):
                for mode in ('always','never','auto'):
                    out,err=Terminal(),Terminal()
                    with patch.dict(os.environ,DOTS_COLOR=mode,DOTS_ICONS='never',TERM='xterm',COLUMNS=str(width),NO_COLOR='1'), \
                         contextlib.redirect_stdout(out),contextlib.redirect_stderr(err):
                        report=reports.report();report.heading('Packages',2)
                        reports.packages(report,[Package('@scope/long-package','2',installed=True)],Backend('npm'))
                        meter=Progress('');summary=upgrade_output.Output('npm',{},meter)
                        summary.package='@scope/long-package';summary.tick()
                        self.assertTrue(all(code==expected for _,code in meter.state[0]))
                        summary.updated=['@scope/long-package'];summary.result(0,skipped=1)
                        formatter=streams.Formatter(err,{'output':'styled'});formatter.feed(b'warning: diagnostic\nordinary output\n',final=True)
                        preview=ui.render(Package('@scope/tool','2'),Backend('npm'),mode,True)
                        text=out.getvalue()+err.getvalue()
                        plain=re.sub(r'\x1b\[[0-9;]*m','',text)
                        self.assertTrue(all(cells(line)<=width for line in plain.splitlines()),plain)
                        if mode=='always':
                            self.assertIn('\x1b['+expected+'m@scope/',text)
                            self.assertIn('\x1b['+expected+'mwarning:',err.getvalue())
                            self.assertIn('\x1b['+expected+'m@scope/tool',preview)
                        else:
                            self.assertNotIn('\x1b',text);self.assertNotIn('\x1b',preview)

    def test_profile_inheritance_and_literal_fallbacks(self):
        parent=self.home/'parent';parent.mkdir()
        (parent/'colors.toml').write_text('[apps.pkgs.package]\nfg="#111111"\n[apps.pkgs.error]\nfg="#222222"\n')
        child=self.path.parent
        (child/'colors.toml').write_text('[apps.pkgs.package]\nbold=true\n')
        prefs=Styles(self.root,selected={'layers':[{'root':str(parent)},{'root':str(child)}]},palette={'accent':'#abcdef'})
        with patch.object(style_config,'current',return_value=prefs):
            self.assertEqual(presentation.styles()['package'],'0;1;38;2;17;17;17')
            self.assertIn('38;2;34;34;34',presentation.styles()['error'])
        with patch.object(style_config,'current',return_value=None):
            self.assertEqual(presentation.styles()['heading'],'0;1;96')
            self.assertEqual(presentation.styles()['package'],'0;34')
            self.assertEqual(presentation.styles()['manager'],'0;35')
            self.assertEqual(presentation.styles()['preview.label'],'0;36')

    def test_manager_palette_is_independent_of_package_and_identity(self):
        prefs=Styles(self.root,selected={'layers':[]},
                     palette={'accent':'#abcdef','magenta':'#123456','blue':'#987654'})
        with patch.object(style_config,'current',return_value=prefs):
            self.assertEqual(presentation.styles()['manager'],'0;38;2;18;52;86')
            self.assertEqual(presentation.styles()['package'],'0;38;2;171;205;239')
            self.assertNotEqual(presentation.styles()['manager'],presentation.styles()['identity'])
        # A retained installation without Dots keeps an ANSI magenta fallback.
        with patch.dict(sys.modules, {'pkgs_lib.presentation':None}):
            self.assertEqual(ui.colored('uv','manager','always',True),'\x1b[35muv\x1b[0m')

    def test_manager_spans_cover_human_surfaces_without_recoloring_packages(self):
        profile=self.path.parent/'colors.toml'
        profile.write_text('[apps.pkgs.manager]\nfg="#123456"\n[apps.pkgs.package]\nfg="#abcdef"\n'
                           '[apps.pkgs.progress]\nfg="#654321"\n')
        prefs=Styles(self.root,selected={'layers':[{'root':str(profile.parent)}]})
        cfg={'color':'always','_explicit_color':'always'}
        with patch.object(style_config,'current',return_value=prefs), \
             patch.dict(os.environ,self.env,clear=True), \
             patch.dict(os.environ,DOTS_COLOR='always',TERM='xterm',COLUMNS='120'):
            colors=presentation.styles()
            marker='\x1b['+colors['manager']+'m'
            package='\x1b['+colors['package']+'m'
            for manager in sorted(presentation.MANAGER_LABELS):
                backend=SimpleNamespace(name=manager,scope='fixture scope')
                operations=(
                    lambda: reports.managers(reports.report(),[dict(manager=manager,scope='fixture',catalog='cached',actions='list')]),
                    lambda: reports.packages(reports.report(),[Package('apt','1')],backend),
                    lambda: workflows.display(workflows.Plan(backend,'install'),cfg),
                    lambda: outdated.display(dict(manager=manager,scope='fixture',error='',packages=[],skipped=[]),cfg),
                    lambda: reports.manager_heading(reports.report(),manager,'fixture',2),
                    lambda: manifests.preview([dict(group={'manager':manager},plan=None,status='failed',reason='fixture')],cfg),
                    lambda: upgrade_output.packages(cfg,'Manager',[manager]),
                )
                for operation in operations:
                    out=Terminal()
                    with contextlib.redirect_stdout(out): operation()
                    self.assertIn(marker+manager+'\x1b[0m',out.getvalue(),(manager,out.getvalue()))
                preview=ui.render(Package('apt','1'),backend,'always',True)
                self.assertIn(marker+manager+'\x1b[0m',preview)
                self.assertIn(package+'apt\x1b[0m',preview)
                meter=Progress('');summary=upgrade_output.Output(manager,cfg,meter)
                summary.package='apt';summary.tick()
                self.assertEqual(meter.state[0][0],(manager,colors['manager']))
                self.assertEqual(meter.state[0][-1],('apt',colors['package']))
                self.assertNotEqual(meter.state[0][1][1],colors['manager'])
                summary.errors=['fixture error'];summary.warnings=['fixture warning'];summary.extra=1
                out,err=Terminal(),Terminal()
                with contextlib.redirect_stdout(out),contextlib.redirect_stderr(err): summary.result(1)
                self.assertRegex(out.getvalue(),re.escape(marker)+r' *'+re.escape(manager)+r' *\x1b\[0m')
                self.assertIn(marker+manager+'\x1b[0m',err.getvalue())
                self.assertNotIn(marker+'fixture',err.getvalue())
                for label in (manager,manager+' · Preparing','Checking updates · '+manager,'Exporting '+manager):
                    transient=presentation.progress('',colors);transient.update(label)
                    self.assertIn((manager,colors['manager']),transient.state[0])
                    self.assertEqual(''.join(text for text,_ in transient.state[0]),label)
            # A package with the same name as another manager retains package styling.
            spans=presentation.activity_spans('npm · apt',colors)
            self.assertEqual(spans,[('npm',colors['manager']),(' · apt',colors['progress'])])
            out=Terminal()
            with contextlib.redirect_stdout(out),patch('pkgs_lib.common.config',return_value={'color':'always'}):
                reports.help_report(grammar.parser([]),[])
            for manager in grammar.MANAGERS:self.assertIn(marker+manager+'\x1b[0m',out.getvalue())
            if os.name != 'nt':
                backend=SimpleNamespace(name='npm',scope='global',global_scope=True)
                with patch.object(ui,'which',return_value='fixture-fzf'), \
                     patch.object(ui,'invocation',return_value=([],dict(os.environ))), \
                     patch.object(ui,'phase',return_value=contextlib.nullcontext()), \
                     patch.object(ui.subprocess,'run',return_value=SimpleNamespace(returncode=1,stdout='')) as native:
                    self.assertEqual(ui.pick([Package('apt')],backend,dict(color='always',preview='right',external_detection=False)),[])
                    header=next(arg for arg in native.call_args.args[0] if arg.startswith('--header='))
                    self.assertIn(marker+'npm\x1b[0m · global',header)

    def test_manager_styling_preserves_redirect_and_raw_bytes(self):
        cfg={'color':'auto','output':'auto'}
        out=io.StringIO()
        with patch.dict(os.environ,self.env,clear=True),contextlib.redirect_stdout(out):
            self.assertIsNone(reports.report())
            self.assertIsNone(reports.report(explicit='always',data=True))
            summary=upgrade_output.Output('npm',cfg);summary.result(0,unchanged=True)
            outdated.display(dict(manager='npm',scope='global',error='',packages=[],skipped=[]),cfg)
        self.assertEqual(out.getvalue(),'  npm: unchanged\n  npm · global · up to date\n')
        raw='npm\x1b[31m native\x1b[0m\rgo: literal\n'
        out=io.StringIO()
        with patch.dict(os.environ,self.env,clear=True), \
             patch.dict(os.environ,DOTS_COLOR='always',DOTS_MENU_CAPTURE='1'), \
             patch.object(sys,'stdin',io.StringIO(raw)),contextlib.redirect_stdout(out):
            self.assertEqual(streams.filter_stdin({'output':'raw','color':'always'}),0)
        self.assertEqual(out.getvalue(),raw)


if __name__=='__main__':unittest.main()
