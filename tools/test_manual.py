#!/usr/bin/env python3
"""Static manual generation and managed manual lifecycle in disposable roots."""
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
from unittest.mock import patch

from test_wiki import WikiFixture, ROOT
import generate_dots_manual as generator
from wiki import Reader
from wiki_commands import inventory
import test_installation as fixtures
from install import Installation
from transactions import Store


class Generation(WikiFixture):
    def test_inert_static_metadata_options_operands_and_escaping(self):
        source=self.root/'bin/dots-sample'
        source.write_text('#!/bin/sh\n# dots:summary=.do not interpret this\n# dots:usage=FILE [--json]\n# dots:option=--json||flag|Structured output\n# dots:argument=1|file|Input file\n# dots:example=echo "literal"\ntouch '+str(self.base/'EXECUTED')+'\n')
        library=self.root/'lib/dots';library.mkdir(parents=True)
        (library/'catalog.bash').write_text("DOTS_GLOBAL_OPTIONS=(\n  '--color||choice:auto,always,never|Color mode'\n)\ntouch NEVER\n")
        first=generator.manual(self.root)
        self.assertEqual(first,generator.manual(self.root))
        self.assertIn(r'\&.do not interpret this',first)
        self.assertIn('Argument 1 (file)',first)
        self.assertIn(r'\-\-json',first)
        self.assertIn(r'\-\-color',first)
        self.assertIn(r'\(dqliteral\(dq',first)
        self.assertFalse((self.base/'EXECUTED').exists())
        self.assertEqual(generator.roff("'request\n.backslash\\"),"\\&'request\n\\&.backslash\\e")

    def test_public_route_coverage_and_freshness(self):
        content=generator.manual(ROOT)
        self.assertEqual((ROOT/'man/dots.1').read_text(),content)
        for row in inventory(Reader(ROOT)):
            self.assertIn('.SS "'+generator.roff(row['route'])+'"',content)
            for flag,short,kind,description in row['option']:
                self.assertIn(generator.roff(flag),content)
        (self.root/'bin/dots-hidden').write_text('# dots:summary=Hidden\n# dots:hidden=true\n')
        self.assertNotIn('dots hidden',generator.manual(self.root))

    @unittest.skipUnless(shutil.which('mandoc'),'mandoc unavailable')
    def test_lint_and_render(self):
        target=self.base/'dots.1';target.write_text(generator.manual(ROOT))
        lint=subprocess.run(['mandoc','-Tlint',str(target)],env=self.env,capture_output=True,text=True)
        self.assertEqual(lint.returncode,0,lint.stdout+lint.stderr)
        rendered=subprocess.run(['mandoc','-Tascii',str(target)],env=self.env,capture_output=True,text=True)
        self.assertEqual(rendered.returncode,0,rendered.stderr)
        self.assertTrue('COMMANDS' in re.sub(r'.\x08', '', rendered.stdout), 'rendered manual lacks command section')
        self.assertNotIn('\x1b',rendered.stdout)


class ManagedManual(unittest.TestCase):
    write=fixtures.InstallationTests.write
    receipt=fixtures.InstallationTests.receipt

    def setUp(self):
        fixtures.InstallationTests.setUp(self)
        self.manual=self.repo/'man/dots.1';self.manual.parent.mkdir()
        self.manual.write_text('.TH DOTS 1\n.SH NAME\ndots\n')
        self.prefix=self.base/'-termux prefix ü/usr';self.prefix.mkdir(parents=True)
        self.env.update(PREFIX=str(self.prefix),TERMUX__PREFIX=str(self.prefix),TERMUX_VERSION='fixture')
        self.patch=patch.dict(os.environ,self.env,clear=True);self.patch.start();self.addCleanup(self.patch.stop)

    def plan(self,platform='termux',components=('core',)):
        with patch('install.platform',return_value=platform):
            plan=Installation(self.repo);plan.plan_install(list(components));return plan

    def test_platform_destinations_component_selection_and_missing_source(self):
        for platform in ('termux','linux','wsl','windows'):
            p=self.plan(platform)
            ops=[op for op in p.operations if op.get('link')==str(self.manual)]
            if platform=='windows':self.assertEqual(ops,[]);continue
            expected=(self.prefix if platform=='termux' else self.home/'.local')/'share/man/man1/dots.1'
            self.assertEqual([op['path'] for op in ops],[str(expected)])
        self.assertFalse(any(op.get('link')==str(self.manual) for op in self.plan(components=('files',)).operations))
        self.assertFalse((self.home/'.state').exists())
        self.manual.unlink()
        self.assertTrue(self.plan().blocked)

    def test_install_repeat_remove_restore_and_core_ownership(self):
        target=self.prefix/'share/man/man1/dots.1';target.parent.mkdir(parents=True)
        target.write_text('previous manual\n')
        self.plan().apply('install')
        self.assertEqual(target.resolve(),self.manual)
        self.assertEqual(self.receipt()['entries'][str(target)]['id'],'dots:manual')
        self.assertEqual(self.plan().apply('install')['status'],'unchanged')
        remove=Installation(self.repo);remove.plan_uninstall(['core']);remove.apply('uninstall')
        self.assertEqual(target.read_text(),'previous manual\n')
        self.assertFalse(target.is_symlink())

    @unittest.skipUnless(os.name != 'nt' and shutil.which('man'), 'native POSIX man viewer unavailable')
    def test_viewer_discovers_the_installed_manual_in_an_owned_search_path(self):
        self.plan().apply('install')
        env=dict(self.env,MANPATH=str(self.prefix/'share/man'),MANPAGER='cat',PAGER='cat')
        p=subprocess.run(['man','-w','dots'],env=env,capture_output=True,text=True,timeout=10)
        self.assertEqual(p.returncode,0,p.stdout+p.stderr)
        self.assertIn('dots.1',p.stdout)
        self.assertTrue(str(self.base) in p.stdout)

    def test_unowned_correct_link_foreign_link_and_owned_drift(self):
        target=self.prefix/'share/man/man1/dots.1';target.parent.mkdir(parents=True)
        target.symlink_to(self.manual)
        self.plan().apply('install')
        self.assertNotIn(str(target),self.receipt()['entries'])
        target.unlink();target.symlink_to(self.base/'missing')
        self.assertTrue(self.plan().blocked)
        target.unlink();self.plan().apply('install')
        target.unlink();target.write_text('user changed manual')
        removal=Installation(self.repo);removal.plan_uninstall(['core'])
        self.assertTrue(any(row['id']=='dots:manual' and row['status']=='preserved' for row in removal.items))
        removal.apply('uninstall')
        self.assertIn(str(target),self.receipt()['entries'])
        self.assertEqual(target.read_text(),'user changed manual')

    def test_stale_source_and_failure_roll_back_original(self):
        target=self.prefix/'share/man/man1/dots.1';target.parent.mkdir(parents=True)
        target.write_text('previous')
        stale=self.plan();self.manual.write_text('changed after preview')
        with self.assertRaisesRegex(ValueError,'changed after preview'):stale.apply('install')
        self.assertEqual(target.read_text(),'previous')
        plan=self.plan();save=plan.store.save
        def fail(doc):
            save(doc)
            if doc['status']=='applying' and any(op['path']==str(target) and op['phase']=='done' for op in doc['operations']):
                raise OSError('injected manual failure')
        with patch.object(plan.store,'save',side_effect=fail):
            with self.assertRaisesRegex(OSError,'injected manual failure'):plan.apply('install')
        self.assertEqual(target.read_text(),'previous')
        self.assertFalse(target.is_symlink())
        self.assertFalse((self.home/'.local/bin/dots').exists())

    @unittest.skipIf(os.name == 'nt', 'native Windows has no POSIX manual transaction')
    def test_interrupted_manual_transaction_recovers(self):
        code='''
import os,sys
sys.path.insert(0,sys.argv[1])
from install import Installation
p=Installation(os.environ['DOTS']);p.plan_install(['core']);save=p.store.save
def crash(doc):
    save(doc)
    if doc['status']=='applying' and any(row['path'].endswith('/man1/dots.1') and row['phase']=='done' for row in doc['operations']):os._exit(17)
p.store.save=crash
p.apply('install')
'''
        p=subprocess.run([sys.executable,'-B','-c',code,str(ROOT/'lib/dots/files')],env=self.env,capture_output=True,text=True)
        self.assertEqual(p.returncode,17,p.stderr)
        target=self.prefix/'share/man/man1/dots.1'
        store=Store(self.home/'.state/dots');record=store.records()[0]
        self.assertEqual(record['status'],'applying')
        store.recover(record['id'])
        self.assertFalse(target.exists());self.assertFalse((self.home/'.local/bin/dots').exists())


if __name__=='__main__':unittest.main()
