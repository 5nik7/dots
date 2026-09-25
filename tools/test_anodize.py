#!/usr/bin/env python3
"""Isolated Anodize authoring and publication acceptance. Requires a prebuilt engine."""
import base64
from contextlib import contextmanager
import json
import os
from pathlib import Path
import shutil
import sys
import unittest
from unittest import mock

import test_themes
from test_themes import REPO, BASH

sys.path.insert(0, str(REPO / 'lib/dots/files'))
sys.path.insert(0, str(REPO / 'lib/dots/anodize'))
from authoring import Author
from transactions import Store, digest

# One opaque pixel. No image libraries or network required.
PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGP4z8AAAAMBAQDJ/pLvAAAAAElFTkSuQmCC')

class Anodize(unittest.TestCase):
    setUpFixture = test_themes.Themes.setUp
    run_command = test_themes.Themes.run_command
    dots = test_themes.Themes.dots

    def setUp(self):
        self.setUpFixture()
        engine = os.environ.get('ANODIZE_ENGINE')
        if not engine or not Path(engine).is_file():
            self.fail('Use python3 -B tools/verify_anodize.py check; ANODIZE_ENGINE must be a prebuilt test binary')
        self.env['ANODIZE_ENGINE'] = engine
        for p in [REPO / 'bin/anodize', *REPO.glob('bin/dots-anodize*')]:
            shutil.copy2(p, self.repo / 'bin' / p.name)
        self.env['PYTHONDONTWRITEBYTECODE'] = '1'
        self.image = self.root / '-wall ü.png'
        self.image.write_bytes(PNG)
        self.active = self.home / 'state/dots/current/theme'

    def cli(self, *args, code=0, **env):
        return self.run_command([BASH, str(self.repo / 'bin/anodize'), *map(str,args)],code,dict(self.env,**env))

    def create(self, name='example', *args):
        return json.loads(self.cli('create', name, '--color', '#725ac1', '--yes', '--json', *args).stdout)

    def recipe(self, name='example'):
        return json.loads((self.repo / 'themes' / name / 'anodize.json').read_text())

    @contextmanager
    def author(self):
        with mock.patch.dict(os.environ, self.env, clear=True):
            yield Author()

    def test_modes_help_metadata_and_completion(self):
        for width in ('40', '80', '120'):
            for args in ((), ('--help',), ('create', '--help'), ('import', '--help')):
                for color in ('never', 'always'):
                    help_text = self.cli(*args, COLUMNS=width, DOTS_COLOR=color,
                                         FORCE_COLOR='1', PYTHON_COLORS='1',
                                         ANODIZE_ENGINE=str(self.root/'missing')).stdout
                    self.assertNotIn(r'\x1b', help_text)
                    if color == 'never':
                        self.assertNotIn('\x1b', help_text)
                        self.assertTrue(all(len(line) <= int(width) for line in help_text.splitlines()))
                    else:
                        self.assertIn('\x1b[1;96m', help_text)
                    self.assertIn('Usage', help_text)
                    self.assertIn('Options', help_text)
        self.assertIn('Choose exactly one source', self.cli('create', '--help').stdout)
        modes=json.loads(self.cli('modes','--json').stdout)['modes']
        self.assertEqual(len(modes),23)
        self.assertEqual(modes,json.loads(self.dots('anodize','modes','--json').stdout)['modes'])
        self.dots('commands','--check')
        for action in ('create','import','edit','export','apply','preview'):
            self.assertIn('anodize',self.cli(action,'--help').stdout)
            self.assertIn(action,self.dots('help','anodize',action).stdout)
        for shell in ('bash','zsh','fish'):
            self.assertIn('--image',self.dots('__complete',shell,'3','--','dots','anodize','create','--i').stdout)
        self.cli('bogus',code=2)
        self.assertFalse(self.state.exists())

    def test_create_preview_save_noop_and_undo(self):
        args=('create','example','--color','#725ac1','--json')
        preview=json.loads(self.cli(*args,'--dry-run','--yes').stdout)
        self.assertEqual(preview['status'],'preview')
        self.assertFalse((self.repo/'themes/example').exists())
        self.assertFalse(self.state.exists())
        saved=self.create()
        self.assertEqual(saved['status'],'complete')
        self.assertFalse(self.active.exists())
        recipe=self.recipe()
        self.assertEqual(recipe['baseline']['blue'],json.loads(self.cli('show','example','--json').stdout)['colors']['blue'])
        count=len(list((self.home/'state/dots/files/transactions').iterdir()))
        self.assertEqual(json.loads(self.cli('edit','example','--yes','--json').stdout)['status'],'unchanged')
        self.assertEqual(len(list((self.home/'state/dots/files/transactions').iterdir())),count)
        with self.author() as author:
            store=author.store();ops,guards,catalogs=store.inverse(saved['transaction'])
            store.apply('undo',ops,guards,retain=True,catalogs=catalogs)
        self.assertFalse((self.repo/'themes/example').exists())

    def test_adjustment_reset_and_retained_edit(self):
        self.create()
        before=json.loads(self.cli('show','example','--json').stdout)['colors']
        baseline=self.recipe()['baseline']
        edited=json.loads(self.cli('edit','example','--adjust','brightness=12','--set','accent=#123456','--yes','--json').stdout)
        self.assertEqual(self.recipe()['baseline'],baseline)
        shown=json.loads(self.cli('show','example','--json').stdout)
        self.assertEqual(shown['colors']['accent'],'#123456')
        self.assertNotEqual(before['background'],shown['colors']['background'])
        self.assertEqual(json.loads(self.cli('edit','example','--adjust','brightness=12','--set','accent=#123456','--yes','--json').stdout)['status'],'unchanged')
        self.cli('edit','example','--reset-adjustments','--yes')
        self.assertEqual(json.loads(self.cli('show','example','--json').stdout)['colors']['background'],before['background'])
        with self.author() as author:
            record=author.store().load(edited['transaction'])
            self.assertTrue(record['retain_backup'])

    def test_variants_from_bundled_and_imported(self):
        self.cli('create','derived','--from','catppuccin-mocha','--yes')
        self.assertEqual(self.recipe('derived')['baseline']['background'],'#1e1e2e')
        before=self.recipe('derived')['baseline']
        self.cli('edit','derived','--light','--yes')
        self.assertTrue(self.recipe('derived')['options']['light'])
        self.assertNotEqual(self.recipe('derived')['baseline']['background'],before['background'])
        self.cli('edit','derived','--reextract','--yes',code=1)
        self.cli('create','light-derived','--from','catppuccin-mocha','--light','--yes')
        self.assertNotEqual(self.recipe('light-derived')['baseline']['background'],'#1e1e2e')
        self.cli('edit','catppuccin-mocha','--yes',code=1)

    def test_image_copy_reference_and_reextract(self):
        self.cli('extract',self.image,'--json')
        self.assertFalse(self.state.exists())
        self.cli('create','image','--image',self.image,'--yes')
        p=self.repo/'themes/image'
        self.assertEqual(self.recipe('image')['wallpaper'],'backgrounds/wallpaper.png')
        self.assertEqual((p/'backgrounds/wallpaper.png').read_bytes(),PNG)
        self.cli('edit','image','--reextract','--yes')
        self.cli('create','reference','--image',self.image,'--reference-wallpaper','--yes')
        self.assertEqual(self.recipe('reference')['wallpaper'],str(self.image))
        self.cli('edit','reference','--adjust','saturation=1','--yes')
        self.assertEqual(self.recipe('reference')['wallpaper'],str(self.image))
        self.assertFalse((self.repo/'themes/reference/backgrounds').exists())

    def test_import_export_roundtrips_and_aether_adjustments(self):
        self.create()
        for fmt in ('anodize','aether','colors'):
            output=self.root/(fmt+'.data')
            raw=self.cli('export','example','--format',fmt).stdout
            output.write_text(raw)
            if fmt=='aether':
                data=json.loads(raw);data['adjustments']={'brightness':30};data['settings']={'includeNeovim':True};output.write_text(json.dumps(data))
            result=self.cli('import',output,'--format',fmt,'--name',fmt,'--yes','--json')
            self.assertEqual(self.recipe(fmt)['adjustments'],{})
            self.assertEqual(json.loads(self.cli('show',fmt,'--json').stdout)['colors'],json.loads(self.cli('show','example','--json').stdout)['colors'])
            if fmt=='aether':
                self.assertIn('already adjusted',result.stdout)
                self.assertEqual(self.recipe(fmt)['provenance']['aether_adjustments']['brightness'],30)

    def test_base16_and_export_collision(self):
        source=self.root/'base16.yaml'
        source.write_text('scheme: Test\n'+''.join(f'base{i:02X}: "{i*0x111111:06x}"\n' for i in range(16)))
        self.cli('import',source,'--format','base16','--name','base','--yes')
        self.assertEqual(self.recipe('base')['baseline']['background'],'#000000')
        self.assertEqual(self.recipe('base')['baseline']['selection'], '#222222')
        source.write_text(source.read_text().replace('base01:', 'missing:'))
        self.cli('import',source,'--format','base16','--name','incomplete','--yes',code=1)
        out=self.root/'export ü.json'
        self.cli('export','base','--output',out,'--dry-run')
        self.assertFalse(out.exists())
        self.cli('export','base','--output',out,'--yes')
        self.cli('export','base','--output',out,'--yes',code=1)
        self.cli('export','base','--format','colors','--json',code=2)

    def test_collisions_drift_symlinks_and_invalid_input(self):
        self.create()
        self.cli('create','example','--color','#ffffff','--yes',code=1)
        colors=self.repo/'themes/example/colors.toml';colors.write_text(colors.read_text()+'# manual change\n')
        self.cli('edit','example','--adjust','gamma=2','--yes',code=1)
        self.assertTrue(colors.read_text().endswith('# manual change\n'))
        self.cli('create','../escape','--color','#ffffff','--yes',code=1)
        self.cli('create','invalid','--color','#ffffff','--adjust','gamma=nan','--yes',code=1)
        self.cli('create','invalid','--color','#ffffff','--set','red=bad','--yes',code=1)
        (self.repo/'themes/link').symlink_to(self.repo/'themes/example')
        self.cli('create','link','--color','#ffffff','--yes',code=1)
        user=self.home/'config/dots/themes/duplicate';user.mkdir(parents=True)
        self.cli('create','duplicate','--color','#ffffff','--yes',code=1)
        broken=self.root/'broken';broken.symlink_to(self.root/'absent')
        self.cli('extract',broken,code=1)
        if hasattr(os,'mkfifo'):
            fifo=self.root/'fifo';os.mkfifo(fifo);self.cli('extract',fifo,code=1)

    def test_publication_normalized_colors_preflight_and_noop(self):
        self.create()
        kitty=self.home/'config/kitty';kitty.mkdir(parents=True)
        preview=json.loads(self.cli('apply','example','--dry-run','--json').stdout)
        self.assertIn(str(kitty/'dots-theme.conf'),preview['connectors'])
        self.assertFalse(self.active.exists())
        self.cli('apply','example','--yes','--json',DOTS_COLOR='always')
        first=self.active.readlink()
        palette=json.loads((self.active/'palette.json').read_text())
        self.assertEqual(palette['roles']['accent'],palette['colors']['accent'])
        self.assertEqual(palette['colors']['color0'],palette['roles']['background'])
        self.cli('apply','example','--yes')
        self.assertEqual(first,self.active.readlink())
        template=self.home/'config/dots/themed/kitty.conf.tpl';template.parent.mkdir(parents=True);template.write_text('{{ invalid }}\n')
        self.cli('apply','example','--dry-run',code=1)
        self.assertEqual(first,self.active.readlink())

    def test_background_preflight_and_failure(self):
        self.cli('create','image','--image',self.image,'--yes')
        self.cli('apply','image','--background','--yes',code=1)
        self.assertFalse(self.active.exists())
        adapter=self.repo/'bin/feh'
        adapter.write_text('#!'+BASH+'\nexit 0\n');adapter.chmod(0o755)
        self.cli('apply','image','--background','--dry-run',DISPLAY=':fixture')
        self.assertFalse(self.active.exists())
        self.cli('apply','image','--background','--yes',DISPLAY=':fixture')
        self.assertTrue(self.active.exists())
        adapter.write_text('#!'+BASH+'\nexit 1\n')
        error=self.cli('apply','image','--background','--yes',DISPLAY=':fixture',code=1)
        self.assertIn('remains published',error.stderr)

    def test_raw_previews_and_missing_engine_help(self):
        self.create()
        text=self.cli('preview','example','--app','kitty',DOTS_COLOR='always').stdout
        self.assertIn('background',text);self.assertNotIn('\x1b',text)
        self.cli('preview','example','--app','kitty','--json',code=2)
        self.cli('--help',ANODIZE_ENGINE=str(self.root/'missing'))
        self.assertIn('verify_anodize.py build',self.cli('modes',code=1,ANODIZE_ENGINE=str(self.root/'missing')).stderr)

    def test_presentation_modes_and_json(self):
        self.create()
        for width in ('40','80','120'):
            plain=self.cli('show','example',COLUMNS=width,DOTS_COLOR='never').stdout
            self.assertNotIn('\x1b',plain)
            colored=self.cli('--color=always','show','example',COLUMNS=width,NO_COLOR='1',TERM='dumb').stdout
            self.assertIn('\x1b[48;2;',colored)
            self.assertNotIn('\x1b',self.cli('show','example',DOTS_COLOR='auto',TERM='dumb').stdout)
            data=self.cli('--color=always','show','example','--json',COLUMNS=width).stdout
            self.assertEqual(json.loads(data)['schema'],1);self.assertNotIn('\x1b',data)
        self.assertIn('No authored themes',self.cli('list',DOTS=str(self.root/'empty')).stdout)

    def test_save_failure_rollback_and_guard(self):
        self.create()
        with self.author() as author:
            doc=author.load('example',owned=True);doc['overrides']['accent']='#123456'
            plan=author.prepare(doc,edit=True);path=Path(plan['target']);before=digest(path)
            original=Store.save
            def fail(store,record):
                original(store,record)
                if record['status']=='applying' and record['operations'][0]['phase']=='done':
                    raise OSError('injected failure')
            with mock.patch.object(Store,'save',fail):
                with self.assertRaises(OSError):author.save(plan)
            self.assertEqual(digest(path),before)
            (path/'notes.txt').write_text('new user work')
            with self.assertRaises(ValueError):author.save(plan)
            self.assertEqual((path/'notes.txt').read_text(),'new user work')

    def test_abrupt_save_recovery(self):
        self.create()
        before=digest(self.repo/'themes/example')
        script='''import os,sys
sys.path[:0]=sys.argv[1:3]
from authoring import Author
import transactions
original=transactions.os.rename
def crash(a,b):
 original(a,b)
 os._exit(77)
a=Author();d=a.load('example',owned=True);d['overrides']['accent']='#abcdef';p=a.prepare(d,edit=True)
transactions.os.rename=crash
a.save(p)
'''
        self.run_command([sys.executable,'-B','-c',script,str(REPO/'lib/dots/anodize'),str(REPO/'lib/dots/files')],code=77)
        with self.author() as author:
            pending=[d for d in author.store().records() if d['status']=='applying']
            self.assertEqual(len(pending),1)
            author.store().recover(pending[0]['id'])
        self.assertEqual(digest(self.repo/'themes/example'),before)

if __name__=='__main__':
    unittest.main()
