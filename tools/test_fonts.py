#!/usr/bin/env python3
"""Font lifecycle/provider/config/CLI checks, exclusively in owned roots."""
from copy import deepcopy
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'lib/dots'))
sys.path.insert(0,str(ROOT/'lib/dots/files'))
from fonts.model import Library,Plan,metadata,digest
from fonts import operations as ops
from fonts import providers
from fonts.config import edit,json_tree,configure,text_digest
from fonts.commands import parser
from fonts_cli import plan_action
from transactions import Store


def font(path,family='Fixture Mono',style='Regular',version='Version 1.0'):
    from fontTools.fontBuilder import FontBuilder
    is_ttf = path.suffix.lower() != '.otf'
    ps_name = (family + '-' + style).replace(' ', '')
    builder=FontBuilder(1000,isTTF=is_ttf)
    builder.setupGlyphOrder(['.notdef','space','A'])
    builder.setupCharacterMap({32:'space',65:'A',0xE000:'A'})
    if is_ttf:
        from fontTools.pens.ttGlyphPen import TTGlyphPen
        pen=TTGlyphPen(None);pen.moveTo((100,0));pen.lineTo((500,0));pen.lineTo((300,700));pen.closePath()
        empty=TTGlyphPen(None).glyph()
        builder.setupGlyf({'.notdef':empty,'space':empty,'A':pen.glyph()})
    else:
        from fontTools.pens.t2CharStringPen import T2CharStringPen
        pen = T2CharStringPen(600, None)
        pen.moveTo((100, 0))
        pen.lineTo((500, 0))
        pen.lineTo((300, 700))
        pen.closePath()
        empty = T2CharStringPen(600, None).getCharString()
        builder.setupCFF(ps_name, {}, {'.notdef': empty, 'space': empty, 'A': pen.getCharString()}, {})
    builder.setupHorizontalMetrics({name:(600,0) for name in ('.notdef','space','A')})
    builder.setupHorizontalHeader(ascent=800,descent=-200)
    builder.setupNameTable(dict(familyName=family,styleName=style,uniqueFontIdentifier=family+style+version,
        fullName=family+' '+style,psName=ps_name,version=version))
    builder.setupOS2(sTypoAscender=800,sTypoDescender=-200,usWinAscent=800,usWinDescent=200)
    builder.setupPost(isFixedPitch=1);builder.setupMaxp();builder.save(path)


@unittest.skipUnless(os.name == 'nt','requires native Windows registry constants')
class WindowsFontRegistry(unittest.TestCase):
    def test_system_font_registry_selects_native_machine_view(self):
        import winreg
        import font_registry
        for system,hive,view in ((True,winreg.HKEY_LOCAL_MACHINE,winreg.KEY_WOW64_64KEY),
                                 (False,winreg.HKEY_CURRENT_USER,0)):
            with self.subTest(system=system), patch.object(winreg,'OpenKey') as opened, \
                 patch.object(winreg,'QueryValueEx',return_value=('fixture.ttf',winreg.REG_SZ)):
                self.assertEqual(font_registry.read('Fixture',system=system),'fixture.ttf')
                opened.assert_called_once_with(hive,font_registry.KEY,0,winreg.KEY_READ | view)
            with patch.object(winreg,'CreateKeyEx') as opened, patch.object(winreg,'SetValueEx') as assign, \
                 patch.object(winreg,'DeleteValue') as delete, patch.object(winreg,'FlushKey'):
                font_registry.write('Fixture','fixture.ttf',system=system)
                opened.assert_called_once_with(hive,font_registry.KEY,0,winreg.KEY_SET_VALUE | view)
                key = opened.return_value.__enter__.return_value
                assign.assert_called_once_with(key,'Fixture',0,winreg.REG_SZ,'fixture.ttf')
                font_registry.write('Fixture',None,system=system)
                delete.assert_called_once_with(key,'Fixture')


class FontMetadata(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='dots-font-metadata-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def test_reference_metadata_for_truetype_and_cff(self):
        from fontTools.fontBuilder import FontBuilder
        from fontTools.ttLib import TTFont

        for suffix in ('.ttf', '.otf'):
            with self.subTest(suffix=suffix):
                path = self.root / ('-Misleading file ü' + suffix)
                font(path, 'Legacy family', 'Legacy style')
                with TTFont(path) as face:
                    names = face['name']
                    names.setName('Typographic family', 16, 3, 1, 0x409)
                    names.setName('Typographic style', 17, 3, 1, 0x409)
                    names.setName('Étoile Nerd Font Mono', 21, 3, 1, 0x409)
                    names.setName('家族', 21, 3, 1, 0x411)
                    names.setName('Demi-gras', 22, 1, 0, 0)
                    face['post'].isFixedPitch = int(suffix == '.ttf')
                    if suffix == '.ttf':
                        builder = FontBuilder(font=face)
                        builder.setupFvar([('slnt', -15.5, -2.25, 0, 'Slant'),
                                           ('wght', 100, 400, 900, 'Weight')], [])
                        builder.setupGvar({glyph: [] for glyph in face.getGlyphOrder()})
                    output = io.BytesIO()
                    face.save(output)
                path.write_bytes(output.getvalue())
                with TTFont(path) as reference:
                    names = reference['name']
                    axes = [dict(tag=axis.axisTag, minimum=axis.minValue, default=axis.defaultValue,
                                 maximum=axis.maxValue) for axis in reference['fvar'].axes] if 'fvar' in reference else []
                    expected = dict(file=path.name, family=names.getBestFamilyName(), style=names.getBestSubFamilyName(),
                                    full_name=names.getDebugName(4), variant='mono',
                                    monospace=bool(reference['post'].isFixedPitch), variable=bool(axes),
                                    axes=axes, sha256=hashlib.sha256(path.read_bytes()).hexdigest())
                with patch.dict(sys.modules, {'fontTools.ttLib': None}):
                    self.assertEqual(metadata(path), expected)

    def test_mac_roman_and_missing_optional_fields(self):
        from fontTools.ttLib import TTFont

        original = self.root / 'original.ttf'
        path = self.root / 'renamed.ttf'
        font(original)
        with TTFont(original) as face:
            del face['post']
            face['name'].names = []
            face['name'].setName('Café', 1, 1, 0, 0)
            face.save(path)
        item = metadata(path)
        self.assertEqual((item['family'], item['style'], item['full_name']), ('Café', 'Regular', 'Café Regular'))
        self.assertEqual((item['monospace'], item['variable'], item['axes']), (False, False, []))

    def test_legacy_mac_family_names_with_vendor_characters(self):
        from fontTools.ttLib import TTFont
        from fontTools.ttLib.tables.DefaultTable import DefaultTable

        original = self.root / 'original.ttf'
        font(original)
        # Each contains a Mac-specific byte outside the base East Asian codec.
        for encoding, raw, expected in ((1, b'\x8f\x91\xfe', '書™'), (2, b'Face\xfd', 'Face©'),
                                        (3, b'Face\x81', 'Face₩'), (25, b'Face\x80', 'Faceü')):
            with self.subTest(encoding=encoding):
                path = self.root / f'mac-{encoding}.ttf'
                table = DefaultTable('name')
                table.data = struct.pack('>3H6H', 0, 1, 18, 1, encoding, 0, 1, len(raw), 0) + raw
                with TTFont(original) as face:
                    face['name'] = table
                    face.save(path)
                self.assertEqual(metadata(path)['family'], expected)

    def test_version_one_name_table_with_localized_family(self):
        from fontTools.ttLib import TTFont
        from fontTools.ttLib.tables.DefaultTable import DefaultTable

        original, localized = self.root / 'original.ttf', self.root / 'localized.ttf'
        font(original)
        family = '書体'.encode('utf-16-be')
        language = 'ja'.encode('utf-16-be')
        # One Unicode family record and one BCP-47 language tag share string storage.
        table = DefaultTable('name')
        table.data = (struct.pack('>3H', 1, 1, 24) +
                      struct.pack('>6H', 0, 4, 0x8000, 16, len(family), 0) +
                      struct.pack('>3H', 1, len(language), len(family)) + family + language)
        with TTFont(original) as face:
            face['name'] = table
            face.save(localized)
        self.assertEqual(metadata(localized)['family'], '書体')

    def test_malformed_payloads_and_containers_are_rejected(self):
        from fontTools.fontBuilder import FontBuilder
        from fontTools.ttLib import TTFont

        original = self.root / 'source.ttf'
        path = self.root / 'invalid.ttf'
        font(original)
        with TTFont(original) as face:
            FontBuilder(font=face).setupFvar([('wght', 100, 400, 900, 'Weight')], [])
            face.save(path)
        raw = path.read_bytes()
        with TTFont(path) as face:
            name = face.reader.tables['name'].offset
            fvar = face.reader.tables['fvar'].offset
            directory_end = 12 + 16 * len(face.reader.tables)
        post_entry = next(offset for offset in range(12, directory_end, 16) if raw[offset:offset + 4] == b'post')

        # Each edit changes a single boundary of an otherwise parseable payload.
        for reason, offset, replacement in (
            ('collection', 0, b'ttcf'), ('web font', 0, b'wOFF'), ('web font 2', 0, b'wOF2'),
            ('table past EOF', 12 + 8, struct.pack('>I', len(raw) + 4)),
            ('name storage past table', name + 4, b'\xff\xff'),
            ('name record past storage', name + 6 + 10, b'\xff\xff'),
            ('truncated post table', post_entry + 12, struct.pack('>I', 15)),
            ('axis record too short', fvar + 10, b'\0\x01'),
            ('inverted axis limits', fvar + 16 + 4, struct.pack('>i', 950 << 16)),
        ):
            with self.subTest(reason=reason):
                path.write_bytes(raw[:offset] + replacement + raw[offset + len(replacement):])
                with self.assertRaises(ValueError):
                    metadata(path)
        with path.open('wb') as stream:
            stream.truncate(64 * 1024 * 1024 + 1)
        with self.assertRaisesRegex(ValueError, '64 MiB'):
            metadata(path)
        with TTFont(original) as face:
            face['name'].names = []
            face['name'].setName('Invalid\nfamily', 1, 3, 1, 0x409)
            face.save(path)
        with self.assertRaises(ValueError):
            metadata(path)

    def test_regular_font_path_required(self):
        path = self.root / 'source.ttf'
        font(path)
        renamed = self.root / 'source.bin'
        shutil.copyfile(path, renamed)
        with self.assertRaises(ValueError):
            metadata(renamed)
        if os.name != 'nt':
            alias = self.root / 'alias.ttf'
            alias.symlink_to(path)
            with self.assertRaises(ValueError):
                metadata(alias)


class Fonts(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='dots-fonts-test-');self.addCleanup(self.temp.cleanup)
        self.home=Path(self.temp.name)/'-home ü';self.home.mkdir()
        self.fixture_root=self.home/'fixture checkout'
        for name in ('linux','wsl','termux','windows'):
            directory=self.fixture_root/'profiles'/name;directory.mkdir(parents=True)
            (directory/'profile.json').write_text(json.dumps(dict(schema=1,id=name)))
        for name in ('lib','bin'):
            shutil.copytree(ROOT/name,self.fixture_root/name,ignore=shutil.ignore_patterns('__pycache__'))
        self.environment={key:value for key,value in os.environ.items() if key in
            ('PATH','PATHEXT','OS','COMSPEC','PREFIX','TERMUX_VERSION','TERMUX__PREFIX','LD_PRELOAD','SYSTEMROOT','SystemRoot','PYTHONPATH','DOTS_TEST_POWERSHELL')}
        self.environment.update(HOME=str(self.home),DOTS=str(self.fixture_root),TERM='dumb',DOTS_COLOR='never',DOTS_ICONS='never',
            USERPROFILE=str(self.home),APPDATA=str(self.home/'Roaming'),LOCALAPPDATA=str(self.home/'Local'),
            TMPDIR=str(self.home/'tmp'),TMP=str(self.home/'tmp'),TEMP=str(self.home/'tmp'))
        (self.home/'tmp').mkdir()
        for name in ('CONFIG','STATE','DATA','CACHE'):self.environment['XDG_'+name+'_HOME']=str(self.home/name.lower())
        self.addCleanup(patch.stopall)
        patch.dict(os.environ,self.environment,clear=True).start()
        # Native test runs must never read or change the developer's registry.
        self.registry={}
        patch('font_registry.read',side_effect=lambda name:self.registry.get(name)).start()
        def registration_write(name,value):
            if value is None:self.registry.pop(name,None)
            else:self.registry[name]=value
        patch('font_registry.write',side_effect=registration_write).start()
        if os.name=='nt':
            # POSIX platform fixtures still create NTFS symlinks. Capture their
            # actual mode and native substitution path for drift assertions.
            def native_link_digest(source):
                with tempfile.TemporaryDirectory(dir=self.home/'tmp') as temp:
                    link=Path(temp)/'preview-link'
                    link.symlink_to(source)
                    return digest(link)
            patch('fonts.operations.link_digest',side_effect=native_link_digest).start()
        self.source=self.home/'input fonts';self.source.mkdir()
        font(self.source/'-Fixture Regular.ttf')
        (self.source/'OFL.txt').write_text('Fixture license')

    def library(self,platform=None):return Library(platform=platform)

    def execute(self,*arguments,native=False,bash=False,powershell=False,code=0):
        engine = os.environ.get('DOTS_TEST_POWERSHELL') or shutil.which('pwsh') or shutil.which('powershell')
        root=Path(os.environ['DOTS'])
        argv=([engine,'-NoLogo','-NoProfile','-NonInteractive','-File',str(root/'bin/dots.ps1'),'fonts'] if powershell else
              [str(root/'bin/dots'),'fonts'] if bash else
              [sys.executable,'-B',str(root/'lib/dots/cli.py'),'fonts'] if native else
              [sys.executable,'-B',str(root/'lib/dots/fonts_cli.py')])
        result=subprocess.run([*argv,*arguments],capture_output=True,text=True,env=os.environ.copy(),timeout=20)
        self.assertEqual(result.returncode,code,result.stdout+result.stderr)
        return result

    def imported(self,platform=None):
        library=self.library(platform);plan=Plan(library)
        with tempfile.TemporaryDirectory(dir=self.home/'tmp') as tmp:
            identity,version=ops.import_files(plan,self.source,tmp);plan.finish();result=plan.apply('import')
        return identity,version,result

    def machine_fixture(self):
        from fonts_cli import mutate
        windows = self.home/'Native Windows'
        (windows/'Fonts').mkdir(parents=True)
        patch('font_registry.windows_root', return_value=windows).start()
        patch('font_registry.elevated', return_value=False).start()
        def state_directory(path, *, create=False):
            if create: path.mkdir(exist_ok=True)
        patch('fonts.machine_state.check_directory', side_effect=state_directory).start()
        machine = {}
        patch('font_registry.machine_values', side_effect=lambda: list(machine.items())).start()
        patch('font_registry.read', side_effect=lambda name,system=False: (machine if system else self.registry).get(name)).start()
        def write(name,value,system=False):
            hive = machine if system else self.registry
            if value is None:
                hive.pop(name,None)
            else:
                hive[name] = value
        patch('font_registry.write', side_effect=write).start()
        patch('fonts.operations.refresh', return_value=[]).start()
        def command(action,*words,preview=False):
            args = parser().parse_args([action,*words,'--system','--dry-run' if preview else '--yes'])
            with patch('font_registry.elevated',return_value=not preview):
                return mutate(Library(platform='windows',system=True),args)
        return windows, machine, command

    def test_system_font_lifecycle_and_scope(self):
        windows, machine, command = self.machine_fixture()
        font(self.source/'Fixture Bold.otf',style='Bold')
        identity,version,_ = self.imported('windows')
        personal = self.library('windows')
        user_plan = Plan(personal)
        # The simulated personal Fonts directory uses this test host's paths.
        with patch('font_registry.PureWindowsPath',Path):
            ops.install(user_plan,identity)
            user_plan.finish().apply('install')
        user_values = dict(self.registry)
        personal = self.library('windows')
        preview = command('install',identity,'--from','personal','--version',version,preview=True)
        self.assertEqual((preview['scope'],preview['font_directory'],preview['elevated']),('system',str(windows/'Fonts'),False))
        self.assertEqual({row['user_registration'] for row in preview['items'] if 'face' in row},set(user_values.values()))
        self.assertFalse((windows/'DotsFontState').exists())
        self.assertFalse(machine)
        with tempfile.TemporaryDirectory(dir=self.home/'tmp') as staging:
            args = parser().parse_args(['install',identity,'--system','--dry-run'])
            plan = plan_action(Library(platform='windows',system=True),args,staging)
            with self.assertRaisesRegex(ValueError,'machine transaction store'):
                Store(personal.state).apply('fonts-install',plan.operations,plan.guards)
        result = command('install',identity)
        self.assertEqual(result['status'],'complete')
        self.assertEqual(set(machine),set(user_values))
        for filename in machine.values():
            self.assertEqual(Path(filename).name,filename)
            self.assertTrue((windows/'Fonts'/filename).is_file())
        self.assertEqual(command('install',identity)['status'],'unchanged')
        machine_values = dict(machine)
        removed = command('uninstall',identity)
        self.assertEqual(machine,{})
        self.assertEqual(list((windows/'Fonts').iterdir()),[])
        command('undo',removed['transaction'])
        self.assertEqual(machine,machine_values)
        self.assertEqual(personal.guard,self.library('windows').guard)
        self.assertEqual(self.registry,user_values)
        name = next(iter(machine))
        machine['Unmanaged alias'] = machine[name]
        with self.assertRaisesRegex(ValueError,'another machine'):
            command('uninstall',identity)
        machine.pop('Unmanaged alias')
        machine[name] = 'foreign.ttf'
        with self.assertRaisesRegex(ValueError,'registration'):
            command('undo',result['transaction'],preview=True)
        self.assertEqual(machine[name],'foreign.ttf')
        machine[name] = machine_values[name]
        (windows/'Fonts'/machine[name]).write_bytes(b'edited')
        with self.assertRaisesRegex(ValueError,'changed'):
            command('uninstall',identity)

    def test_system_font_batch_conflict_and_rollback(self):
        windows, machine, command = self.machine_fixture()
        first,_,_ = self.imported('windows')
        (self.source/'-Fixture Regular.ttf').unlink()
        font(self.source/'Other.ttf',family='Other')
        second,_,_ = self.imported('windows')
        machine['Other Regular (TrueType)'] = 'existing.ttf'
        with self.assertRaisesRegex(ValueError,'owned outside'):
            command('install',first,second)
        self.assertFalse((windows/'DotsFontState').exists())
        machine.clear()
        import font_registry
        write = font_registry.write.side_effect
        def fail(name,value,system=False):
            if value and name.startswith('Other '):
                raise OSError('injected registration failure')
            write(name,value,system)
        with patch('font_registry.write',side_effect=fail), self.assertRaisesRegex(OSError,'injected'):
            command('install',first,second)
        self.assertEqual(machine,{})
        self.assertEqual(list((windows/'Fonts').iterdir()),[])
        library = Library(platform='windows',system=True)
        self.assertEqual(library.families,{})
        self.assertEqual(Store(library.state).records()[-1]['status'],'rolled-back')

    def test_system_font_command_boundaries(self):
        from fonts_cli import run
        if os.name == 'nt':
            with patch('font_registry.elevated',return_value=False):
                with self.assertRaisesRegex(ValueError,'Administrator PowerShell: dots fonts install'):
                    run(['install',"Font's Name",'--yes','--system'])
            with self.assertRaisesRegex(ValueError,'different destinations'):
                run(['install','SomeFont','--directory','DOTFONTS','--system','--dry-run'])
            for engine in ('powershell','pwsh'):
                if shutil.which(engine):
                    with patch.dict(os.environ,DOTS_TEST_POWERSHELL=engine):
                        self.assertIn('--system', self.execute('install','--help',powershell=True).stdout)
                        result = self.execute('install','SomeFont','--directory','DOTFONTS','--system','--dry-run',powershell=True,code=1)
                        self.assertIn('different destinations',result.stderr)
        else:
            with self.assertRaisesRegex(ValueError,'requires native Windows'):
                run(['install','SomeFont','--system','--dry-run'])
            self.assertIn('requires native Windows',self.execute('install','SomeFont','--system','--dry-run',bash=True,code=1).stderr)

    @unittest.skipUnless(os.name == 'nt','requires native Windows ACLs')
    def test_system_font_state_directory_acl(self):
        from codex_attention_native import Windows
        from fonts import machine_state
        native = Windows()
        sid = native.sid_text(native.sid)
        # Exercise the real ACL API under the test user's token. Production
        # assigns ownership to Administrators in the protected Windows folder.
        descriptor = machine_state.DESCRIPTOR.replace('O:BA', 'O:'+sid) + '(A;OICI;FA;;;'+sid+')'
        path = self.home/'state access'
        with patch.object(machine_state,'DESCRIPTOR',descriptor):
            machine_state.check_directory(path)
            self.assertFalse(path.exists())
            machine_state.check_directory(path,create=True)
            machine_state.check_directory(path,create=True)
            machine_state.check_directory(path)
            with self.assertRaisesRegex(ValueError,'administrator-owned'):
                machine_state.check_directory(self.source)

    def test_nf_shim_forwards_exact_icons_contract(self):
        cache=self.library().catalog_path;cache.parent.mkdir(parents=True)
        rows=[dict(name='fixture', glyph='\ue000', codepoint='U+E000', collection='fixture')]
        cache.write_text(json.dumps(dict(schema=1, families={}, glyph_version='v', glyphs={'v':rows})))
        if os.name=='nt':
            engine=os.environ.get('DOTS_TEST_POWERSHELL') or shutil.which('pwsh') or shutil.which('powershell')
            prefix=[engine,'-NoProfile','-File']
            suffix='.ps1'
        else:
            prefix=[];suffix=''
        def call(name,*words):
            return subprocess.run([*prefix,str(self.fixture_root/'bin'/(name+suffix)),*words],
                                  capture_output=True,timeout=15)
        for args in (('--help',),('--json','--color','always'),('fixture','--format','glyph'),
                     ('--print',),('missing','--format','glyph'),('--bad-option',)):
            expected=call('dots','fonts','icons',*args);actual=call('nf',*args)
            self.assertEqual((actual.returncode,actual.stdout,actual.stderr),
                             (expected.returncode,expected.stdout,expected.stderr),args)
        self.assertEqual(call('nf','fixture','--format','glyph').stdout,'\ue000'.encode())

    def test_readonly_cli_modes_and_frontend_parity(self):
        for argv in (('list','--json'),('search','--json'),('current','--json'),('update','--dry-run','--json')):
            first=self.execute(*argv).stdout
            self.assertEqual(first,self.execute(*argv,native=True).stdout)
            if os.name == 'nt':
                with patch.dict(os.environ, PATH=str(Path(sys.executable).parent)+os.pathsep+os.environ['PATH']):
                    self.assertEqual(first,self.execute(*argv,powershell=True).stdout)
            else:
                self.assertEqual(first,self.execute(*argv,bash=True).stdout)
            self.assertNotIn('\x1b',first);json.loads(first)
        self.execute('--help');self.execute('install','--help')
        self.assertFalse((self.home/'state').exists());self.assertFalse((self.home/'data').exists());self.assertFalse((self.home/'cache').exists())

    def test_import_idempotence_provenance_export_and_undo(self):
        identity,version,result=self.imported()
        library=self.library();record=library.families[identity]['versions'][version]
        self.assertEqual(record['provenance']['upstream_version'],'unknown')
        self.assertEqual(record['fonts'][0]['family'],'Fixture Mono')
        self.assertEqual(self.imported()[2]['status'],'unchanged')
        output=self.home/'export space'
        self.execute('export',identity,'--output',str(output),'--yes','--json')
        self.assertEqual((output/'-Fixture Regular.ttf').read_bytes(),(self.source/'-Fixture Regular.ttf').read_bytes())
        self.assertEqual((output/'OFL.txt').read_text(),'Fixture license')
        store=Store(library.state);operations,guards,catalogs=store.inverse(result['transaction'])
        store.apply('undo',operations,guards,retain=True,catalogs=catalogs)
        self.assertFalse(library.path.exists());self.assertTrue(self.source.exists())

    def test_install_pin_uninstall_remove_and_drift(self):
        identity,version,_=self.imported()
        library=self.library();plan=Plan(library);ops.install(plan,identity);plan.finish();result=plan.apply('install')
        library=self.library();installed=library.families[identity]['installed'];target=Path(installed['files'][0]['path'])
        self.assertEqual(digest(target),installed['files'][0]['after'])
        again=Plan(library);ops.install(again,identity);again.finish();self.assertEqual(again.operations,[])
        self.execute('pin',identity,'--yes','--json')
        self.assertEqual(self.library().families[identity]['pin'],version)
        self.execute('remove',identity,'--version',version,'--yes','--json',code=1)
        target.unlink();target.write_text('unowned replacement')
        with self.assertRaisesRegex(ValueError,'changed'):ops.uninstall(Plan(self.library()),identity)
        target.unlink()
        source=library.folder(identity,version)/'-Fixture Regular.ttf'
        if library.platform=='windows':shutil.copy2(source,target)
        else:target.symlink_to(source)
        self.execute('unpin',identity,'--yes','--json')
        plan=Plan(self.library());ops.uninstall(plan,identity);plan.finish();plan.apply('uninstall')
        self.assertFalse(target.exists())
        plan=Plan(self.library());ops.remove(plan,identity,version);plan.finish();plan.apply('remove')
        self.assertNotIn(identity,self.library().families)

    def test_termux_set_backups_no_reload_and_undo(self):
        identity,version,_=self.imported('termux')
        path=self.home/'.termux/font.ttf';path.parent.mkdir();path.write_bytes(b'previous font')
        library=self.library('termux');plan=Plan(library);record=library.families[identity]['versions'][version]
        configure(plan,identity,version,record['fonts'][0],'termux');plan.finish();result=plan.apply('set')
        self.assertEqual(path.read_bytes(),(self.source/'-Fixture Regular.ttf').read_bytes())
        library=self.library('termux');again=Plan(library)
        configure(again,identity,version,record['fonts'][0],'termux');again.finish();self.assertEqual(again.operations,[])
        with patch('fonts.operations.subprocess.run') as run:
            self.assertIn('skipped',ops.refresh(plan,no_reload=True)[0]);run.assert_not_called()
        store=Store(library.state);operations,guards,catalogs=store.inverse(result['transaction'])
        store.apply('undo',operations,guards,retain=True,catalogs=catalogs)
        self.assertEqual(path.read_bytes(),b'previous font')

    def test_requires_confirmation_and_stale_plan(self):
        self.execute('import',str(self.source),'--json',code=1)
        self.assertFalse((self.home/'state').exists())
        library=self.library();plan=Plan(library)
        with tempfile.TemporaryDirectory(dir=self.home/'tmp') as tmp:
            ops.import_files(plan,self.source,tmp);plan.finish()
            (self.source/'-Fixture Regular.ttf').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'changed'):plan.apply('import')
        self.assertFalse(library.path.exists())

    def test_payload_directory_drift_blocks_removal(self):
        identity,version,_=self.imported();library=self.library()
        (library.folder(identity,version)/'unrelated').write_text('keep')
        with self.assertRaisesRegex(ValueError,'directory changed'):ops.remove(Plan(library),identity,version)

    def test_upgrade_retained_version_and_active_face_protection(self):
        identity,version,_=self.imported();library=self.library();plan=Plan(library)
        ops.install(plan,identity);plan.finish();plan.apply('install')
        library=self.library();plan=Plan(library)
        with tempfile.TemporaryDirectory(dir=self.home/'tmp') as tmp:
            payload=Path(tmp)/'next';shutil.copytree(self.source,payload)
            font(payload/'-Fixture Regular.ttf',version='Version 2.0')
            record=deepcopy(library.families[identity]['versions'][version]);record['fonts']=[metadata(payload/'-Fixture Regular.ttf')]
            ops.stage(plan,identity,'v2',payload,record,'Fixture Mono');ops.install(plan,identity,'v2');plan.finish();plan.apply('upgrade')
        self.assertEqual(self.library().families[identity]['installed']['version'],'v2')
        self.assertTrue(library.folder(identity,version).is_dir())
        plan=Plan(self.library());ops.install(plan,identity,version);plan.finish();plan.apply('rollback')
        self.assertEqual(self.library().families[identity]['installed']['version'],version)

    def test_upgrade_and_rollback_active_termux_without_desktop_install(self):
        identity='nerd:Fixture';first='v1.0.0';second='v2.0.0'
        with tempfile.TemporaryDirectory(dir=self.home/'tmp') as tmp:
            payload=Path(tmp)/'first';shutil.copytree(self.source,payload)
            face=metadata(payload/'-Fixture Regular.ttf')
            record=dict(fonts=[face],licenses=['OFL.txt'],fingerprint='first',provenance=dict(revision=first))
            plan=Plan(self.library('termux'));ops.stage(plan,identity,first,payload,record,'Fixture')
            configure(plan,identity,first,face,'termux');plan.finish();plan.apply('set')
            payload=Path(tmp)/'second';shutil.copytree(self.source,payload)
            font(payload/'-Fixture Regular.ttf',version='Version 2.0')
            record=dict(record,fonts=[metadata(payload/'-Fixture Regular.ttf')],fingerprint='second')
            library=self.library('termux');plan=Plan(library);ops.stage(plan,identity,second,payload,record,'Fixture')
            catalog=dict(schema=1,glyphs={},families={identity:dict(name='Fixture',provider='nerd',latest=second,
                versions={second:dict(provider='nerd',version=second,fingerprint='second')})})
            plan.put(library.catalog_path,data=catalog);plan.finish();plan.apply('download')
            with patch('fonts.providers.download',side_effect=AssertionError('already downloaded')):
                plan=plan_action(self.library('termux'),parser().parse_args(['upgrade']),tmp)
            plan.apply('upgrade')
            library=self.library('termux')
            self.assertEqual(library.document['targets']['termux']['version'],second)
            self.assertIsNone(library.families[identity]['installed'])
            plan=plan_action(library,parser().parse_args(['rollback',identity,'--version',first]),tmp);plan.apply('rollback')
            self.assertEqual(self.library('termux').document['targets']['termux']['version'],first)
            self.assertEqual((self.home/'.termux/font.ttf').read_bytes(),(self.source/'-Fixture Regular.ttf').read_bytes())

    def test_configuration_preserves_comments_fallbacks_and_other_fields(self):
        text='// heading\n{"editor.fontFamily": "Old, \'Fallback\', monospace", "editor.fontSize": 14, "x": 1, "x": 2,}\n'
        result=edit(text,'vscode-editor','New Mono')
        self.assertIn('// heading',result);self.assertIn('New Mono, \'Fallback\', monospace',result)
        self.assertIn('"editor.fontSize": 14',result);self.assertIn('"x": 1, "x": 2',result)
        result=edit(result,'vscode-terminal','Terminal Mono');json_tree(result)
        with self.assertRaisesRegex(ValueError,'ambiguous'):edit('{"editor.fontFamily":"a","editor.fontFamily":"b"}','vscode-editor','New')
        kitty='# keep\nfont_family family="Old" features="+liga"\nfont_size 14\nbold_font auto\n'
        self.assertEqual(edit(kitty,'kitty','New'),kitty.replace('"Old"','"New"'))
        lua='config.font = wezterm.font_with_fallback({\n { family = "Old", weight = "Medium" }, "Emoji",\n})\nconfig.font_size = 9\n'
        self.assertEqual(edit(lua,'wezterm','New'),lua.replace('"Old"','"New"'))
        with self.assertRaisesRegex(ValueError,'computed'):edit('config.font = compute_font()','wezterm','New')
        with self.assertRaisesRegex(ValueError,'computed'):edit('config.font = wezterm.font("Old" .. suffix)','wezterm','New')
        comment='--[[\nconfig.font = wezterm.font("Comment")\n]]\n'
        self.assertEqual(edit(comment+lua,'wezterm','New'),comment+lua.replace('"Old"','"New"'))
        wt='{"profiles":{"defaults":{"font":{"face":"Old, Fallback","size":9}},"list":[{"guid":"abc","font":{"face":"Other"}}]}}'
        self.assertIn('"Other"',edit(wt,'windows-terminal','New'))
        self.assertIn('"Old, Fallback"',edit(wt,'windows-terminal','New','abc'))

    def test_two_vscode_targets_share_one_guarded_write(self):
        identity,version,_=self.imported();library=self.library();plan=Plan(library)
        ops.install(plan,identity);plan.finish();plan.apply('install')
        path=self.home/'settings.json';path.write_text('{"editor.fontFamily":"Old","terminal.integrated.fontFamily":"Old", "size":9}\n')
        library=self.library();plan=Plan(library);face=library.families[identity]['versions'][version]['fonts'][0]
        for target in ('vscode-editor','vscode-terminal'):configure(plan,identity,version,face,target,explicit=str(path))
        plan.finish();plan.apply('set')
        library=self.library();self.assertEqual(len({v['after'] for v in library.document['targets'].values()}),1)
        self.assertEqual(next(iter(library.document['targets'].values()))['after'],digest(path))
        again=Plan(library)
        for target in ('vscode-editor','vscode-terminal'):configure(again,identity,version,face,target,explicit=str(path))
        again.finish();self.assertEqual(again.operations,[])

    def test_archive_validation_and_provider_urls(self):
        archive=self.home/'font.zip';dest=self.home/'extracted';dest.mkdir()
        with zipfile.ZipFile(archive,'w') as z:z.writestr('../escape.ttf','bad')
        with self.assertRaisesRegex(ValueError,'unsafe'):providers.extract(archive,dest)
        self.assertEqual(list(dest.iterdir()),[])
        for url in ('http://github.com/x','https://evil.test/font','https://user:secret@github.com/font'):
            with self.assertRaises(ValueError):providers.url(url)
        self.assertEqual(providers.url('https://github.com/a/b'),'https://github.com/a/b')

    def test_download_progress_uses_response_bytes_and_optional_total(self):
        from unittest.mock import Mock
        payload = b'x' * (300 * 1024)
        for length in (str(len(payload)), '', 'invalid', '0', '9'*50, '12'):
            with self.subTest(length=length):
                response = io.BytesIO(payload)
                response.url = 'https://github.com/fixture/font'
                response.headers = {'Content-Length': length}
                opener = Mock(); opener.open.return_value = response
                with patch.object(providers, 'build_opener', return_value=opener), \
                     patch.object(providers, 'report') as meter:
                    self.assertEqual(providers.fetch(response.url), payload)
                counts = [call.args[1:] for call in meter.call_args_list]
                self.assertEqual([done for done, _ in counts], [0, 256*1024, len(payload)])
                self.assertEqual(counts[-1][1], len(payload) if length == str(len(payload)) else 0)

    def test_official_catalog_fixtures_and_versioned_glyphs(self):
        responses={
            providers.API+'ryanoasis/nerd-fonts/releases/latest':dict(tag_name='v3.4.0',assets=[dict(name='Fixture.zip',browser_download_url='https://github.com/ryanoasis/nerd-fonts/releases/download/v3.4.0/Fixture.zip')]),
            'https://raw.githubusercontent.com/ryanoasis/nerd-fonts/v3.4.0/glyphnames.json':{'METADATA':{},'test-icon':dict(code='e000',char='\ue000')},
        }
        with patch('fonts.providers.get',side_effect=lambda u:responses[u]):
            catalog=providers.refresh(dict(schema=1,families={},glyphs={}),'nerd')
        self.assertEqual(catalog['glyphs']['v3.4.0'][0]['codepoint'],'U+E000')
        library=self.library();plan=Plan(library);plan.put(library.catalog_path,data=catalog);plan.apply('update')
        self.assertEqual(self.execute('icons','test-icon','--format','glyph').stdout,'\ue000')
        self.assertEqual(self.execute('icons','test-icon','--format','codepoint').stdout,'U+E000')
        with patch('fonts.providers.get',side_effect=ValueError('rate limited')):
            with self.assertRaisesRegex(ValueError,'rate'):providers.refresh(catalog,'nerd')
        self.assertEqual(self.library().catalog,catalog)

    def test_completion_no_writes_and_literal_values(self):
        identity,version,_=self.imported()
        command=[sys.executable,'-B',str(ROOT/'lib/dots/fonts/completion.py')]
        before=digest(self.library().path)
        result=subprocess.run([*command,'install',''],capture_output=True,text=True,env=os.environ.copy())
        self.assertIn(identity,result.stdout)
        result=subprocess.run([*command,'set',identity,'--face',''],capture_output=True,text=True,env=os.environ.copy())
        self.assertIn('-Fixture Regular.ttf',result.stdout)
        if os.name=='nt':
            candidates=subprocess.check_output([sys.executable,'-B',str(self.fixture_root/'lib/dots/cli.py'),
                                                '__complete','fonts','icons','--format',''])
            self.assertIn(b'candidate\tglyph\t',candidates)
        for shell in (() if os.name=='nt' else ('bash','zsh','fish')):
            args=[str(self.fixture_root/'bin/dots'),'__complete',shell]
            nf=subprocess.check_output([*args,'2','--','nf','--format',''])
            icons=subprocess.check_output([*args,'4','--','dots','fonts','icons','--format',''])
            self.assertEqual(nf,icons)
            self.assertIn(b'candidate\tglyph\t',nf)
        self.assertEqual(digest(self.library().path),before)

    def test_google_selective_download_and_two_nerd_archives(self):
        commit='a'*40;group='b'*40;family='c'*40
        replies={providers.API+'google/fonts/commits/main':dict(sha=commit),
            providers.API+'google/fonts/git/trees/'+commit:dict(tree=[dict(path='ofl',type='tree',sha=group)]),
            providers.API+'google/fonts/git/trees/'+group:dict(tree=[dict(path='fixture',type='tree',sha=family)]),
            providers.API+'google/fonts/git/trees/'+family:dict(tree=[dict(path='Fixture.ttf',type='blob'),dict(path='OFL.txt',type='blob'),dict(path='DESCRIPTION.en_us.html',type='blob')])}
        addresses=[]
        def fetch(address,output=None,**kwargs):
            addresses.append(address)
            source=self.source/('-Fixture Regular.ttf' if address.endswith('.ttf') else 'OFL.txt')
            shutil.copyfile(source,output)
        with patch('fonts.providers.get',side_effect=lambda u:replies[u]),patch('fonts.providers.fetch',side_effect=fetch):
            catalog=providers.refresh(dict(schema=1,families={},glyphs={}),'google')
            spec=catalog['families']['google:ofl/fixture']['versions'][commit]
            record=providers.download('google:ofl/fixture',spec,self.home/'google download')
        self.assertEqual(record['fingerprint'],family);self.assertEqual(record['provenance']['revision'],commit)
        self.assertEqual(len(addresses),2);self.assertTrue(all('/'+commit+'/' in a for a in addresses))
        archive=self.home/'official.zip'
        with zipfile.ZipFile(archive,'w') as z:
            for path in self.source.iterdir():z.write(path,'Licence.txt' if path.name=='OFL.txt' else path.name)
        def archive_fetch(address,output=None,**kwargs):shutil.copyfile(archive,output)
        spec=dict(provider='nerd',version='v1.0.0',url='https://github.com/ryanoasis/nerd-fonts/releases/download/v1.0.0/Fixture.zip')
        with patch('fonts.providers.fetch',side_effect=archive_fetch):
            for number in (1,2):
                record=providers.download('nerd:Fixture',spec,self.home/('nerd-'+str(number)),keep_archive=True)
                self.assertEqual(len(record['fonts']),1)
                self.assertEqual(record['licenses'],['Licence.txt'])
            with self.assertRaisesRegex(ValueError,'digest mismatch'):
                providers.download('nerd:Fixture',dict(spec,fingerprint='sha256:'+'0'*64),self.home/'bad-digest')
        self.assertFalse(self.library().path.exists())

    @unittest.skipIf(os.name=='nt','POSIX symlink ownership fixture; native Windows links require separate acceptance')
    def test_managed_source_link_copy_receipt_and_drift(self):
        identity,version,_=self.imported();library=self.library()
        face=library.families[identity]['versions'][version]['fonts'][0]
        repository=self.home/'repo';repository.mkdir();source=repository/'kitty.conf';active=self.home/'kitty.conf'
        source.write_bytes(b'# keep\r\nfont_family Old\r\nfont_size 14\r\n');active.symlink_to(source)
        manifest=repository/'catalog.json';manifest.write_text('{}')
        from unittest.mock import Mock
        catalog=Mock();catalog.records.return_value=[dict(id='fixture',app='kitty',applicable=True,enabled=True,
            target=str(active),source=str(source),status='linked')];catalog.input_paths.return_value=[manifest]
        with patch.dict(os.environ,DOTS=str(repository)),patch('files.catalog.Catalog',return_value=catalog):
            plan=Plan(library);configure(plan,identity,version,face,'kitty');plan.finish();plan.apply('set')
            self.assertTrue(active.is_symlink());self.assertEqual(source.read_bytes(),b'# keep\r\nfont_family Fixture Mono\r\nfont_size 14\r\n')
            active.unlink();shutil.copyfile(source,active)
            with self.assertRaisesRegex(ValueError,'unowned'):configure(Plan(self.library()),identity,version,face,'kitty')
            receipt=library.state/'installation.json'
            record=dict(schema=1,root=str(repository),platform=library.platform,entries={str(active):dict(id='fixture',after=digest(active))})
            receipt.write_text(json.dumps(record))
            new_face=dict(face,family='Other Fixture')
            plan=Plan(self.library());configure(plan,identity,version,new_face,'kitty');plan.finish();plan.apply('set')
            self.assertEqual(source.read_bytes(),active.read_bytes())
            self.assertEqual(json.loads(receipt.read_text())['entries'][str(active)]['after'],digest(active))
            active.write_text('unrelated changes')
            with self.assertRaisesRegex(ValueError,'changed'):configure(Plan(self.library()),identity,version,face,'kitty')

    @unittest.skipIf(os.name=='nt','Termux symlink lifecycle fixture')
    def test_active_face_pin_collision_and_stale_payload_guards(self):
        identity,version,_=self.imported();library=self.library('termux');plan=Plan(library)
        face=library.families[identity]['versions'][version]['fonts'][0]
        configure(plan,identity,version,face,'termux');ops.install(plan,identity);plan.finish();plan.apply('set')
        library=self.library('termux');plan=Plan(library)
        with tempfile.TemporaryDirectory(dir=self.home/'tmp') as tmp:
            payload=Path(tmp)/'incompatible';shutil.copytree(self.source,payload)
            font(payload/'-Fixture Regular.ttf',family='Renamed')
            record=deepcopy(library.families[identity]['versions'][version]);record['fonts']=[metadata(payload/'-Fixture Regular.ttf')]
            ops.stage(plan,identity,'v2',payload,record,'Renamed')
            with self.assertRaisesRegex(ValueError,'active face'):ops.install(plan,identity,'v2')
            plan.document['families'][identity]['pin']=version
            with self.assertRaisesRegex(ValueError,'pinned'):ops.install(plan,identity,'v2')
        library=self.library();plan=Plan(library)
        plan.file(identity,version,face)
        (library.folder(identity,version)/'extra').write_text('preserve concurrent file')
        plan.put(self.home/'result',text='should not apply')
        with self.assertRaisesRegex(ValueError,'changed'):plan.apply('export')
        self.assertFalse((self.home/'result').exists())

    def test_invalid_import_preview_and_corrupt_metadata_are_bounded(self):
        (self.source/'Broken.ttf').write_bytes(b'truncated')
        plan = Plan(self.library())
        with tempfile.TemporaryDirectory(dir=self.home/'tmp') as staging, self.assertRaises(ValueError):
            ops.import_files(plan, self.source, staging)
        self.assertFalse(plan.operations)
        self.assertFalse(plan.library.path.exists())
        from fonts.preview import render_sample
        with patch('fonts.preview.shutil.which',return_value=None),patch('fonts.preview.subprocess.run') as child:
            self.assertIn('unavailable',render_sample(self.source/'-Fixture Regular.ttf'));child.assert_not_called()
        if shutil.which('magick') and shutil.which('chafa'):
            result=render_sample(self.source/'-Fixture Regular.ttf',False)
            self.assertNotIn('unavailable',result);self.assertNotIn('\x1b',result)
        library=self.library();library.path.parent.mkdir(parents=True)
        library.path.write_text(json.dumps(dict(schema=1,families={'local:invalid':dict(versions={'v1':None})},targets={})))
        result=self.execute('list','--json',code=1)
        self.assertNotIn('Traceback',result.stderr);self.assertIn('invalid font version',result.stderr)

    def test_icon_insertion_pins_context_and_never_sends_enter(self):
        from fonts.browser import insert
        from unittest.mock import Mock
        context=Mock();context.pane='%8';context.command.side_effect=lambda *a:['tmux','-S','private',*a]
        with patch('fonts.browser.subprocess.run',return_value=Mock(returncode=0)) as run:
            insert('\ue000',context)
            self.assertEqual(run.call_args.args[0],['tmux','-S','private','send-keys','-t','%8','-l','--','\ue000'])
        context.verify.assert_called_once()
        context.verify.side_effect=ValueError('stale')
        with patch('fonts.browser.subprocess.run') as run:
            with self.assertRaisesRegex(ValueError,'stale'):insert('\ue000',context)
            run.assert_not_called()

    def test_narrow_human_views_and_forced_decoration_data(self):
        from fonts_cli import render
        identity,version,_=self.imported();library=self.library()
        for width in (40,80,120):
            output=io.StringIO()
            with patch('shutil.get_terminal_size',return_value=os.terminal_size((width,24))):
                render(dict(items=library.rows()),output)
            self.assertTrue(all(len(line)<=width for line in output.getvalue().splitlines()),output.getvalue())
        for argv in (('list','--json'),('path',identity,'--json')):
            result=self.execute(*argv,'--color','always','--icons','always')
            self.assertNotIn('\x1b',result.stdout);json.loads(result.stdout)

    def test_legacy_flags_preserve_sources_and_dry_run_is_offline(self):
        if self.library().platform!='termux':self.skipTest('Termux compatibility wrappers')
        with patch.dict(os.environ,TERMUX_NF_FONT_DIR=str(self.source)):
            self.assertEqual(self.execute('__legacy','chnf','-l').stdout,'-Fixture Regular.ttf\n')
            result=self.execute('__legacy','chnf','--font=-Fixture Regular.ttf','--no-reload','--dry-run')
            self.assertIn('preview',result.stdout)
            self.execute('__legacy','getnf','-i','Fixture','-f','-k','--dry-run')
            self.execute('__legacy','getnf','--help');self.execute('__legacy','chnf','--help')
        self.assertFalse(self.library().path.exists());self.assertTrue((self.source/'-Fixture Regular.ttf').exists())

    def test_registry_transaction_failure_rollback_and_undo(self):
        import font_registry
        with patch.dict(os.environ,LOCALAPPDATA=r'C:\Users\fixture\AppData\Local'):
            registry={};name='Fixture Mono Regular (TrueType)'
            value=r'C:\Users\fixture\AppData\Local\Microsoft\Windows\Fonts\fixture.ttf'
            receipt=self.home/'receipt.json';store=Store(self.home/'state/dots')
            spec=dict(name=name,before=None,after=value)
            def write(n,v):
                if v is None:registry.pop(n,None)
                else:registry[n]=v
            with patch.object(font_registry,'read',side_effect=lambda n:registry.get(n)),patch.object(font_registry,'write',side_effect=write):
                result=store.apply('fonts-install',[dict(path=str(receipt),data=dict(schema=1),font_registry=spec)],{str(receipt):None},retain=True)
                self.assertEqual(registry[name],value)
                inverse,guards,catalogs=store.inverse(result['id']);store.apply('undo',inverse,guards,retain=True,catalogs=catalogs)
                self.assertEqual(registry,{});self.assertFalse(receipt.exists())
                def fail(n,v):
                    write(n,v)
                    if v is not None:raise OSError('registration failed after write')
                with patch.object(font_registry,'write',side_effect=fail):
                    with self.assertRaises(OSError):store.apply('fonts-install',[dict(path=str(receipt),data=dict(schema=1),font_registry=spec)],{str(receipt):None},retain=True)
                self.assertEqual(registry,{});self.assertFalse(receipt.exists())


if __name__=='__main__':unittest.main(verbosity=2)
