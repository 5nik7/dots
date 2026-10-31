#!/usr/bin/env python3
"""Installer font ownership, exact choices and selective restoration."""
import json
import io
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from contextlib import redirect_stdout

import test_fonts as fixtures
from fonts.model import Library, digest
from install import Installation
from setup_fonts import Fonts, uninstall


class SetupFonts(unittest.TestCase):
    setUp = fixtures.Fonts.setUp
    imported = fixtures.Fonts.imported
    library = fixtures.Fonts.library

    def mapping(self):
        root = self.fixture_root
        source = root/'config/termux'
        source.mkdir(parents=True)
        catalog = root/'.dots';catalog.mkdir()
        platforms = ['termux','linux','wsl','windows']
        (catalog/'sources.json').write_text(json.dumps(dict(schema=1,sources=[dict(id='dots',path='.',roots=['config'],platforms=platforms)])))
        (catalog/'files.json').write_text(json.dumps(dict(schema=1,repository='dots',resources=[dict(id='termux',app='termux',category='config',source='config/termux',target='${HOME}/.termux',strategy='directory-link',platforms=platforms)])))
        (self.home/'.termux').symlink_to(source,target_is_directory=True)
        return source

    def draft(self, identity, version):
        installation = Installation(self.fixture_root)
        installation.plan_install(['files','fonts'])
        face = self.library('termux').families[identity]['versions'][version]['fonts'][0]
        args = SimpleNamespace(font_document=dict(schema=1,applications={}),font_target=None,
            font_choices=[dict(id=identity,version=version,target='termux',face=face['file'],variant=face['variant'])],save_choices=False)
        return installation, Fonts(installation,args)

    def test_managed_parent_run_only_repeat_and_restore(self):
        with patch('install.platform',return_value='termux'):
            source = self.mapping()
            fixtures.font(source/'font.ttf','Original Mono')
            original = (source/'font.ttf').read_bytes()
            identity,version,_ = self.imported('termux')
            preferences = self.fixture_root/'profiles/termux/fonts.json'
            preferences.write_text('{"schema":1,"applications":{}}\n')
            initial = preferences.read_bytes()
            first,fonts = self.draft(identity,version)
            before = sorted(str(p) for p in self.home.rglob('*'))
            fonts.preview()
            self.assertEqual(before,sorted(str(p) for p in self.home.rglob('*')))
            with tempfile.TemporaryDirectory(dir=self.home/'tmp') as temporary:
                fonts.prepare(temporary);fonts.publish(first);first.apply('install')
            self.assertNotEqual((source/'font.ttf').read_bytes(),original)
            self.assertEqual(preferences.read_bytes(),initial)
            repeat,fonts = self.draft(identity,version)
            with tempfile.TemporaryDirectory(dir=self.home/'tmp') as temporary:
                fonts.prepare(temporary);fonts.publish(repeat)
                self.assertEqual(repeat.apply('install')['status'],'unchanged')
            remove = Installation(self.fixture_root)
            remove.plan_uninstall(['fonts']);uninstall(remove);remove.apply('uninstall')
            self.assertEqual((source/'font.ttf').read_bytes(),original)
            self.assertTrue((self.home/'.termux').is_symlink())
            self.assertEqual(preferences.read_bytes(),initial)
            library = self.library('termux')
            self.assertIn(identity,library.families)
            self.assertNotIn('termux',library.document['targets'])

    def test_preparation_failure_and_foreign_parent_are_inert(self):
        with patch('install.platform',return_value='termux'):
            source = self.mapping()
            identity,version,_ = self.imported('termux')
            first,fonts = self.draft(identity,version)
            fonts.args.font_choices[0]['face'] = 'missing.ttf'
            with tempfile.TemporaryDirectory(dir=self.home/'tmp') as temporary, self.assertRaises(ValueError):
                fonts.prepare(temporary)
            self.assertFalse((source/'font.ttf').exists())
            self.assertFalse(first.receipt_path.exists())
            (self.home/'.termux').unlink();(self.home/'.termux').symlink_to(self.source,target_is_directory=True)
            with self.assertRaises(ValueError): self.draft(identity,version)[1].preview()

    def test_windows_copy_registration_and_selective_font_baseline(self):
        root=self.fixture_root
        source=root/'config/code.json';source.parent.mkdir();source.write_text('{"editor.fontFamily":"Original","custom":7}\n')
        original=source.read_bytes();active=self.home/'Roaming/Code/User/settings.json'
        catalog=root/'.dots';catalog.mkdir()
        (catalog/'sources.json').write_text(json.dumps(dict(schema=1,sources=[dict(id='dots',path='.',roots=['config'],platforms=['windows'])])))
        (catalog/'files.json').write_text(json.dumps(dict(schema=1,repository='dots',resources=[dict(id='code',app='vscode',category='config',source='config/code.json',target='${HOME}/Roaming/Code/User/settings.json',strategy='copy',platforms=['windows'])])))
        identity,version,_=self.imported('windows')
        face=self.library('windows').families[identity]['versions'][version]['fonts'][0]
        args=SimpleNamespace(font_document=dict(schema=1,applications={}),font_target=None,
            font_choices=[dict(id=identity,version=version,target='vscode-editor',face=face['file'],variant=face['variant'])],save_choices=False)
        def fixture_registration(spec):
            # Native path grammar has its own font_registry tests. This fixture
            # maps the current-user directory to a test-owned POSIX directory.
            self.assertEqual(set(spec),{'name','before','after'})
            for value in (spec['before'],spec['after']):
                if value is not None:self.assertEqual(Path(value).parent,self.home/'Local/Microsoft/Windows/Fonts')
        with patch('install.platform',return_value='windows'),patch('font_registry.validate',side_effect=fixture_registration):
            installation=Installation(root);installation.plan_install(['files','fonts'])
            fonts=Fonts(installation,args);fonts.preview()
            with tempfile.TemporaryDirectory(dir=self.home/'tmp') as temporary:
                fonts.prepare(temporary);fonts.publish(installation);installation.apply('install')
            self.assertEqual(source.read_bytes(),active.read_bytes())
            self.assertEqual(json.loads(active.read_text())['custom'],7)
            self.assertTrue(self.registry)
            registry=dict(self.registry)
            remove=Installation(root);remove.plan_uninstall(['fonts']);uninstall(remove);remove.apply('uninstall')
            self.assertEqual(source.read_bytes(),original);self.assertEqual(active.read_bytes(),original)
            self.assertEqual(self.registry,registry)
            self.assertIn(str(active),remove.entries)
            remove=Installation(root);remove.plan_uninstall(['files']);remove.apply('uninstall')
            self.assertFalse(active.exists());self.assertEqual(source.read_bytes(),original)

    def test_changed_font_selection_metadata_is_preserved(self):
        from fonts.model import Plan
        with patch('install.platform',return_value='termux'):
            source=self.mapping()
            identity,version,_=self.imported('termux')
            installation,fonts=self.draft(identity,version)
            with tempfile.TemporaryDirectory(dir=self.home/'tmp') as temporary:
                fonts.prepare(temporary);fonts.publish(installation);installation.apply('install')
            before=(source/'font.ttf').read_bytes()
            external=Plan(self.library('termux'))
            external.document['targets']['termux']['family']='Later user selection'
            external.finish();external.apply('fixture-user-selection')
            removal=Installation(self.fixture_root);removal.plan_uninstall(['fonts']);uninstall(removal)
            removal.apply('uninstall')
            self.assertTrue(any(i['status']=='preserved' for i in removal.items))
            self.assertEqual((source/'font.ttf').read_bytes(),before)
            self.assertEqual(self.library('termux').document['targets']['termux']['family'],'Later user selection')

    def test_combined_coordinator_repeat_and_selective_restore(self):
        import sys
        from unittest.mock import Mock
        from install import main
        from test_setup_leaf import SetupLeaf
        sys.path.insert(0,str(fixtures.ROOT/'plugins/pkgs'))
        self.repo=self.fixture_root;self.base=self.home
        fixtures.shutil.copytree(fixtures.ROOT/'default',self.repo/'default')
        SetupLeaf.fixture(self)
        source=self.mapping();fixtures.font(source/'font.ttf','Original Mono')
        original_font=(source/'font.ttf').read_bytes()
        leaf=self.home/'.local/bin/leaf';leaf.parent.mkdir(parents=True);leaf.write_bytes(b'original leaf')
        identity,version,_=self.imported('termux')
        face=self.library('termux').families[identity]['versions'][version]['fonts'][0]
        saved=dict(id=identity,version=version,target='termux',face=face['file'],variant=face['variant'],
                   files={face['file']:face['sha256']})
        preferences=self.home/'font choices.json'
        preferences.write_text(json.dumps(dict(schema=1,applications=dict(termux=saved))))
        packages=self.home/'package choices.json'
        packages.write_text('{"schema":1,"groups":[]}')
        stage=Mock();stage.apply.return_value=dict(schema=1,status='complete',groups=[])
        def prepare_packages():
            if not (self.home/'.local/bin/dots').exists():
                self.assertEqual((source/'font.ttf').read_bytes(),original_font)
                self.assertEqual(leaf.read_bytes(),b'original leaf')
            return dict(schema=1,status='complete',groups=[])
        stage.apply.side_effect=prepare_packages
        def invoke(*words):
            output=io.StringIO()
            with redirect_stdout(output):self.assertEqual(main([*words,'--yes','--json']),0)
            return json.loads(output.getvalue())
        words=['install','--fonts',str(preferences),'--packages',str(packages),'--save-choices']
        for name in ('core','files','fonts','leaf','packages'):words+=['--component',name]
        with patch('install.platform',return_value='termux'),patch('package_setup.Stage',return_value=stage), \
             patch('setup_leaf.execute',side_effect=lambda argv,**kw:SetupLeaf.execute(self,argv,**kw)):
            installed=invoke(*words)
            self.assertEqual(installed['status'],'complete')
            self.assertEqual(leaf.read_bytes(),b'verified fixture binary')
            self.assertNotEqual((source/'font.ttf').read_bytes(),original_font)
            saved_profile=self.fixture_root/'profiles/termux/fonts.json'
            self.assertEqual(json.loads(saved_profile.read_text())['applications']['termux']['files'],saved['files'])
            self.assertEqual(invoke(*words)['status'],'unchanged')
            invoke('uninstall','--component','fonts','--component','leaf')
            self.assertEqual(leaf.read_bytes(),b'original leaf')
            self.assertEqual((source/'font.ttf').read_bytes(),original_font)
            self.assertTrue((self.home/'.local/bin/dots').exists())
            self.assertTrue(self.library('termux').families)
            invoke('uninstall')
            self.assertFalse((self.home/'.local/bin/dots').exists())
            self.assertTrue(saved_profile.exists());self.assertTrue((self.home/'.termux').is_symlink())


if __name__ == '__main__': unittest.main(verbosity=2)
