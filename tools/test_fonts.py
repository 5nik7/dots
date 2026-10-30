#!/usr/bin/env python3
"""Font lifecycle/provider/config/CLI checks, exclusively in owned roots."""
from copy import deepcopy
import io
import json
import os
from pathlib import Path
import shutil
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
    from fontTools.pens.ttGlyphPen import TTGlyphPen
    builder=FontBuilder(1000,isTTF=True)
    builder.setupGlyphOrder(['.notdef','space','A'])
    builder.setupCharacterMap({32:'space',65:'A',0xE000:'A'})
    pen=TTGlyphPen(None);pen.moveTo((100,0));pen.lineTo((500,0));pen.lineTo((300,700));pen.closePath()
    empty=TTGlyphPen(None).glyph()
    builder.setupGlyf({'.notdef':empty,'space':empty,'A':pen.glyph()})
    builder.setupHorizontalMetrics({name:(600,0) for name in ('.notdef','space','A')})
    builder.setupHorizontalHeader(ascent=800,descent=-200)
    builder.setupNameTable(dict(familyName=family,styleName=style,uniqueFontIdentifier=family+style+version,
        fullName=family+' '+style,psName=(family+'-'+style).replace(' ',''),version=version))
    builder.setupOS2(sTypoAscender=800,sTypoDescender=-200,usWinAscent=800,usWinDescent=200)
    builder.setupPost(isFixedPitch=1);builder.setupMaxp();builder.save(path)


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
            ('PATH','PREFIX','TERMUX_VERSION','TERMUX__PREFIX','LD_PRELOAD','SYSTEMROOT','SystemRoot','PYTHONPATH')}
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
        self.source=self.home/'input fonts';self.source.mkdir()
        font(self.source/'-Fixture Regular.ttf')
        (self.source/'OFL.txt').write_text('Fixture license')

    def library(self,platform=None):return Library(platform=platform)

    def execute(self,*arguments,native=False,bash=False,code=0):
        argv=([str(ROOT/'bin/dots'),'fonts'] if bash else
              [sys.executable,'-B',str(ROOT/'lib/dots/cli.py'),'fonts'] if native else
              [sys.executable,'-B',str(ROOT/'lib/dots/fonts_cli.py')])
        result=subprocess.run([*argv,*arguments],capture_output=True,text=True,env=os.environ.copy(),timeout=20)
        self.assertEqual(result.returncode,code,result.stdout+result.stderr)
        return result

    def imported(self,platform=None):
        library=self.library(platform);plan=Plan(library)
        with tempfile.TemporaryDirectory(dir=self.home/'tmp') as tmp:
            identity,version=ops.import_files(plan,self.source,tmp);plan.finish();result=plan.apply('import')
        return identity,version,result

    def test_readonly_cli_modes_and_frontend_parity(self):
        for argv in (('list','--json'),('search','--json'),('current','--json'),('update','--dry-run','--json')):
            first=self.execute(*argv).stdout
            self.assertEqual(first,self.execute(*argv,native=True).stdout)
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

    def test_missing_parser_preview_and_corrupt_metadata_are_bounded(self):
        with patch.dict(sys.modules,{'fontTools.ttLib':None}):
            with self.assertRaisesRegex(ValueError,'fontTools'):metadata(self.source/'-Fixture Regular.ttf')
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
