#!/usr/bin/env python3
"""Package Config bindings and actual consumers in disposable roots."""
import contextlib
import io
import json
import os
from pathlib import Path
import re
import sys
import unittest
from unittest.mock import patch

import test_style_config as fixtures
from style_config import Styles
import style_config
from style_catalog import PKGS
from resources import cells

sys.path.insert(0,str(fixtures.ROOT/'plugins/pkgs'))
from pkgs_lib import presentation, reports, ui, upgrade_output, streams
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
            self.assertEqual(presentation.styles()['preview.label'],'0;36')


if __name__=='__main__':unittest.main()
