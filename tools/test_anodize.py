#!/usr/bin/env python3
"""Isolated Anodize authoring and publication acceptance. Requires a prebuilt engine."""
import base64
import struct
import zlib
from contextlib import contextmanager
import json
import os
from pathlib import Path
import shutil
import shlex
import sys
import unittest
from unittest import mock

import test_themes
import test_confirmations
import test_theme_picker
from test_themes import REPO, BASH

sys.path.insert(0, str(REPO / 'lib/dots/files'))
sys.path.insert(0, str(REPO / 'plugins/anodize'))
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
        for p in [REPO / 'bin/anodize', REPO / 'bin/patina', REPO / 'bin/dots-patina', *REPO.glob('bin/dots-anodize*')]:
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
        return json.loads((self.home / 'config/dots/themes' / name / 'anodize.json').read_text())

    def test_patina_four_routes_numbering_and_undo(self):
        import concurrent.futures
        args = [str(self.image), '--theme', 'nord', '--json']
        routes = [('patina',), ('anodize', 'patina'), ('dots', 'patina'), ('dots', 'anodize', 'patina')]
        def invoke(route, *flags):
            command, *rest = route
            return json.loads(self.run_command([BASH, str(self.repo/'bin'/command), *rest, *args, *flags]).stdout)
        preview = invoke(routes[0], '--dry-run', '--yes')
        base = self.home/'config/dots/backgrounds/nord'/self.image.name
        self.assertEqual((preview['style'],preview['harmony'],preview['strength']), ('alloy','auto',100))
        self.assertEqual(preview['target'], str(base))
        self.assertFalse(base.parent.exists())
        for route in routes:
            self.assertEqual(invoke(route), preview)
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as workers:
            saved = list(workers.map(lambda route: invoke(route, '--yes'), routes))
        expected = {base, *(base.with_stem(base.stem+'_'+str(i)) for i in range(1,4))}
        self.assertEqual({Path(r['target']) for r in saved}, expected)
        self.assertEqual(len({p.read_bytes() for p in expected}), 1)
        self.assertTrue(base.read_bytes().startswith(b'\x89PNG'))
        self.assertFalse(self.active.exists())
        profile = self.repo/'profiles/termux'
        (profile/'backgrounds/nord').mkdir(parents=True)
        (profile/'profile.json').write_text(json.dumps(dict(schema=1, id='termux')))
        extra = profile/'backgrounds/nord/profile.png'
        extra.write_bytes(PNG)
        self.env['TERMUX_VERSION'] = 'fixture'
        self.env['DOTS_THEME_SELECTION'] = 'nord'
        listed = {Path(line) for line in self.dots('theme','bg','list').stdout.splitlines()}
        self.assertTrue((expected | {extra}) <= listed, listed)
        item = next(r for r in saved if r['target'].endswith('_1.png'))
        with self.author() as author:
            store = author.store()
            ops, guards, catalogs = store.inverse(item['transaction'])
            store.apply('undo', ops, guards, catalogs=catalogs)
        self.assertEqual(invoke(routes[0])['target'], item['target'])
        Path(item['target']).symlink_to('missing')
        self.assertTrue(invoke(routes[0])['target'].endswith('_4.png'))
        self.cli('patina',str(self.image),'--theme','nord','--output',str(base),'--yes',code=1)
        self.cli('patina',str(self.image),'--theme','nord','--light',code=2)
        uppercase = self.home/'Evening.PNG'
        uppercase.write_bytes(PNG)
        occupied = base.parent/uppercase.name
        occupied.touch()
        preview = self.cli('patina', str(uppercase), '--theme', 'nord', '--dry-run', '--json')
        self.assertEqual(Path(json.loads(preview.stdout)['target']), occupied.with_stem('Evening_1'))

    def test_patina_palette_matches_extract_and_show(self):
        def one_pixel(rgb):
            def chunk(kind, data):
                return (struct.pack('>I',len(data)) + kind + data
                        + struct.pack('>I',zlib.crc32(kind+data)))
            header = struct.pack('>IIBBBBB',1,1,8,2,0,0,0)
            return (PNG[:8] + chunk(b'IHDR',header) + chunk(b'IDAT',zlib.compress(b'\0'+rgb))
                    + chunk(b'IEND',b''))
        self.cli('create','authored','--color','#222222','--set','custom=#ff0102','--yes')
        custom = json.loads(self.cli('show','authored','--json').stdout)['colors']['custom']
        source = self.root/'one ü.png'
        options = ['--mode','ocean','--light']
        extracted = json.loads(self.cli('extract',str(self.image),*options,'--json').stdout)['colors']['blue']
        for palette, flags in ((custom,['--theme','authored']),
                               (extracted,['--palette-image',str(self.image),*options])):
            rgb = bytes.fromhex(palette[1:])
            source.write_bytes(one_pixel(rgb))
            target = self.root/(palette+'.png')
            self.cli('patina',str(source),*flags,'--style','exact','--output',str(target),'--yes')
            output = target.read_bytes()
            start = output.index(b'IDAT') + 4
            # The first and only pixel in a row has zero-valued filter neighbors.
            self.assertEqual(zlib.decompress(output[start:])[1:4], rgb)

    def test_patina_treatments_and_validation(self):
        source = str(self.image)
        target = self.root/'duotone.png'
        self.cli('create','fern','--color','#45584c','--set','fern_tip=#8fad72','--yes')
        for flags, stops in ((['--theme','fern'], ['fern_tip','foreground']),
                             (['--palette-image',source,'--mode','pastel'], ['blue','yellow'])):
            result = json.loads(self.cli('patina',source,*flags,'--style','duotone','--strength','65',
                                         '--stops',','.join(stops),'--output',str(target),'--dry-run','--json').stdout)
            self.assertEqual((result['style'], result['strength'], result['stops']),('duotone',65,stops))
            self.assertFalse(target.exists())
        for flags in (['--style','duotone','--stops','blue'], ['--style','duotone','--stops','blue,green,red'],
                      ['--style','exact','--strength','0'], ['--strength','101'], ['--strength','0.5'],
                      ['--style','gradient','--harmony','source'], ['--stops','blue,yellow']):
            self.cli('patina',source,'--theme','fern','--output',str(target),'--yes',*flags,code=2)
        self.cli('patina',source,'--theme','fern','--output',str(target),'--style','gradient',
                 '--stops','background,unknown','--yes',code=1)
        self.assertFalse(target.exists())

    def test_patina_output_encoders_and_extension_precedence(self):
        import xml.etree.ElementTree as ET
        from cli import parser
        from patina import output_settings
        opts = parser().parse_args(['patina', str(self.image), '--theme', 'nord', '--format', 'webp'])
        with mock.patch.dict(sys.modules, {'PIL': None}):
            with self.assertRaisesRegex(ValueError, 'WEBP encoder'):
                output_settings(opts, self.image)
        try:
            from PIL import Image
            Image.init()
        except ImportError:
            Image = None
        for ext, fmt in [('png','png'), ('JpG','jpeg'), ('jpeg','jpeg'), ('gif','gif'), ('svg','svg'),
                         ('WebP','webp'), ('bmp','bmp'), ('tif','tiff'), ('tiff','tiff'), ('avif','avif')]:
            with self.subTest(ext=ext):
                path = self.root/('encoded.' + ext)
                args = ['patina', str(self.image), '--theme', 'nord', '--format', 'gif', '--output', str(path), '--yes', '--json']
                if fmt in ('webp','avif','bmp','tiff') and (Image is None or fmt.upper() not in Image.SAVE):
                    self.cli(*args, code=1)
                    self.assertFalse(path.exists())
                    continue
                report = json.loads(self.cli(*args).stdout)
                self.assertEqual(report['format'], fmt)
                if fmt == 'svg':
                    href = ET.parse(path).getroot()[0].get('{http://www.w3.org/1999/xlink}href')
                    self.assertTrue(base64.b64decode(href.split(',')[1]).startswith(PNG[:8]))
                elif Image:
                    with Image.open(path) as img:
                        img.load()
                        self.assertEqual((img.format.lower(), img.size), (fmt, (1, 1)))
        for ext, extra in [('webp', ['--quality','0']), ('jpg',['--lossless']), ('png', ['--quality','90']),
                           ('webp', ['--lossless','--quality','30']), ('unknown', [])]:
            path = self.root/('bad.' + ext)
            self.cli('patina',str(self.image),'--theme','nord','--output',str(path),*extra,'--yes',code=1)
            self.assertFalse(path.exists())
        dest = self.root/'type-selected'
        result = json.loads(self.cli('patina',str(self.image),'--theme','nord','--output',str(dest),
                                     '--format','jpg','--quality','82','--json','--yes').stdout)
        self.assertEqual((result['target'], result['quality']), (str(dest)+'.jpg', 82))
        self.assertTrue(Path(result['target']).read_bytes().startswith(b'\xff\xd8'))

    def test_patina_comparisons_and_temporary_theme_mode(self):
        from patina import STYLES
        self.cli('create','fern','--color','#45ad62','--light','--set','fern_tip=#ed8cab','--yes')
        before = self.recipe('fern')
        flags = ['patina',str(self.image),'--theme','fern','--json']
        for number in range(2):
            sheet = json.loads(self.cli(*flags,'--mode','jewel-tones','--compare','--yes').stdout)
            self.assertEqual(sheet['panels'][1:], [f'{i:02d} {s}' for i, s in enumerate(STYLES, 1)])
            self.assertEqual([sheet['panels'][i] for i in (1, 7, 18)],
                             ['01 harmonize', '07 palette-blend', '18 alloy'])
            self.assertTrue(sheet['light'])
            suffix = '_styles.png' if number == 0 else '_styles_1.png'
            self.assertEqual(Path(sheet['target']), self.image.with_name(self.image.stem + suffix))
        sheet = json.loads(self.cli(*flags,'--compare-modes','--style','duotone','--stops','fern_tip,foreground','--dark','--dry-run').stdout)
        self.assertEqual((sheet['panels'][:2],len(sheet['panels']),sheet['light']), (['Original','01 as-authored'],37,False))
        self.assertFalse(Path(sheet['target']).exists())
        self.assertEqual(self.recipe('fern'),before)
        ref = json.loads(self.cli('patina',str(self.image),'--palette-image',str(self.image),'--compare-modes',
                                  '--dry-run','--json').stdout)
        self.assertEqual((len(ref['panels']), ref['style']), (36, 'alloy'))
        self.assertFalse(Path(ref['target']).exists())

    def test_patina_reference_modes_and_drift(self):
        from patina import run
        from cli import parser
        path = self.root/'explicit ü.png'
        args = ['patina',str(self.image),'--palette-image',str(self.image),'--style','shaded']
        self.cli(*args, code=2)
        out = json.loads(self.cli(*args,'--mode','ocean','--light','--output',str(path),'--json','--yes').stdout)
        self.assertEqual((out['mode'],out['light'],out['style'],out['width'],out['height']),('ocean',True,'shaded',1,1))
        self.assertTrue(path.is_file())
        path.unlink()
        with self.author() as author:
            opts = parser().parse_args([*args,'--output',str(path)])
            def change_input(*_):
                self.image.write_bytes(PNG + b'changed')
                return True
            with self.assertRaisesRegex(ValueError,'changed after preview'):
                run(author, opts, change_input, self.fail)
        self.assertFalse(path.exists())

    def test_patina_cancel_thumbnail(self):
        test_confirmations.install_gum(self.root, self.env)
        self.env['GUM_CHOICE'] = 'Cancel'
        for width in (40, 80, 120):
            self.env.update(COLUMNS=str(width), DOTS_COLOR='always')
            command = [BASH, str(self.repo/'bin/patina'), str(self.image), '--theme','nord']
            if width == 40:
                command.extend(['--interactive','--style','exact','--output',str(self.home/'custom.png')])
            result = self.terminal(shlex.join(command), width=width)
            self.assertFalse((self.home/'custom.png').exists())
            self.assertIn('▀'.encode(), result)
            self.assertIn(b'Target', result)
            self.assertFalse((self.home/'config/dots/backgrounds').exists())

    def test_local_plugins_share_publication_and_keep_authoring_inert(self):
        hooks = self.home / 'config/dots/hooks/theme-set.d'
        hooks.mkdir(parents=True)
        hook = hooks / '20-anodize-check.sh'
        hook.write_text('printf "%s %s\\n" "$DOTS_THEME_ID" "$DOTS_THEME_REASON" >> "$HOME/plugin-runs"\n')
        self.dots('theme', 'plugins', 'enable', 'anodize-check')
        self.create()
        self.cli('edit', 'example', '--adjust', 'gamma=1.1', '--yes')
        self.cli('export', 'example', '--format', 'colors')
        self.cli('preview', 'example', '--app', 'kitty')
        self.cli('apply', 'example', '--dry-run', '--json')
        log = self.home / 'plugin-runs'
        self.assertFalse(log.exists())
        result = self.cli('apply', 'example', '--yes', '--json', DOTS_COLOR='always')
        json.loads(result.stdout)
        self.assertEqual(len(log.read_text().splitlines()), 1)
        self.cli('apply', 'example', '--yes')
        self.assertEqual(len(log.read_text().splitlines()), 1)
        self.dots('theme', 'refresh')
        self.assertEqual(len(log.read_text().splitlines()), 2)
        self.assertTrue(log.read_text().splitlines()[-1].endswith(' refresh'))
        hook.write_text('exit 9')
        self.cli('edit', 'example', '--adjust', 'gamma=1.2', '--yes')
        result = self.cli('apply', 'example', '--yes', '--json')
        json.loads(result.stdout)
        self.assertIn('Theme remains published', result.stderr)

    @contextmanager
    def author(self):
        with mock.patch.dict(os.environ, self.env, clear=True):
            yield Author()

    terminal = test_theme_picker.Picker.terminal

    def test_gum_confirmations(self):
        test_confirmations.install_gum(self.root, self.env)
        command = [BASH, str(self.repo / 'bin/anodize'), 'create', 'approval', '--color', '#725ac1']
        self.script = shlex.join(command)
        for choice, code in [('Cancel', 0), ('EXIT:1', 1), ('EXIT:130', 130), ('unknown', 1)]:
            with self.subTest(choice=choice):
                self.env['GUM_CHOICE'] = choice
                out = self.terminal(code=code)
                self.assertNotIn(b'[y/N]', out)
                self.assertNotIn(b'Traceback', out)
                self.assertFalse((self.home / 'config/dots/themes/approval').exists())
                self.assertFalse((self.home / 'state').exists())
        self.env['GUM_CHOICE'] = 'Apply'
        self.terminal()
        self.assertTrue((self.home / 'config/dots/themes/approval/anodize.json').is_file())
        self.assertFalse(self.active.exists())  # Saving never activates a theme.

    def test_confirmation_bypass_and_plain_fallback(self):
        test_confirmations.install_gum(self.root, self.env)
        command = [BASH, str(self.repo / 'bin/anodize'), 'create', 'approval', '--color', '#725ac1']
        self.script = shlex.join(command)
        self.terminal(self.script + ' --dry-run')
        self.terminal(self.script + ' --json')
        self.cli('create', 'approval', '--color', '#725ac1')  # Nonterminal preview.
        self.terminal(env=dict(self.env, TERM='dumb'), steps=((b'[y/N]', b'n\r'),))
        captured = self.home / 'redirected'
        self.terminal(self.script + ' > ' + shlex.quote(str(captured)),
                      steps=((b'', b'n\r'),))
        self.assertIn('[y/N]', captured.read_text())
        self.assertFalse((self.home / 'config/dots/themes/approval').exists())
        self.terminal(self.script + ' --yes')
        self.assertTrue((self.home / 'config/dots/themes/approval/anodize.json').is_file())
        self.assertFalse((self.home / 'gum-calls').exists())

    def test_modes_help_metadata_and_completion(self):
        for width in ('40', '80', '120'):
            for args in ((), ('--help',), ('create', '--help'), ('import', '--help'), ('patina', '--help')):
                for color in ('never', 'always'):
                    help_text = self.cli(*args, COLUMNS=width, DOTS_COLOR=color,
                                         FORCE_COLOR='1', PYTHON_COLORS='1',
                                         ANODIZE_ENGINE=str(self.root/'missing')).stdout
                    self.assertNotIn(r'\x1b', help_text)
                    if color == 'never':
                        self.assertNotIn('\x1b', help_text)
                        self.assertTrue(all(len(line) <= int(width) for line in help_text.splitlines()))
                    else:
                        self.assertIn('\x1b[0;1;36mUsage\x1b[0m', help_text)
                    self.assertIn('Usage', help_text)
                    self.assertIn('Options', help_text)
        self.assertIn('Choose exactly one source', self.cli('create', '--help').stdout)
        modes=json.loads(self.cli('modes','--json').stdout)['modes']
        self.assertEqual(len(modes),35)
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
        self.assertFalse((self.home/'config/dots/themes/example').exists())
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
        self.assertFalse((self.home/'config/dots/themes/example').exists())

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
        p=self.home/'config/dots/themes/image'
        self.assertEqual(self.recipe('image')['wallpaper'],'backgrounds/wallpaper.png')
        self.assertEqual((p/'backgrounds/wallpaper.png').read_bytes(),PNG)
        self.cli('edit','image','--reextract','--yes')
        self.cli('create','reference','--image',self.image,'--reference-wallpaper','--yes')
        self.assertEqual(self.recipe('reference')['wallpaper'],str(self.image))
        self.cli('edit','reference','--adjust','saturation=1','--yes')
        self.assertEqual(self.recipe('reference')['wallpaper'],str(self.image))
        self.assertFalse((self.home/'config/dots/themes/reference/backgrounds').exists())

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

    def test_logo_preserves_raw_and_structured_interfaces(self):
        self.create()
        for args in [('show','example','--json'), ('export','example','--format','colors'),
                     ('export','example'), ('preview','example','--app','kitty')]:
            expected = self.cli(*args).stdout
            for renderer in ('text','auto','kitty','chafa'):
                actual = self.cli(*args,'--logo='+renderer, DOTS_COLOR='always', DOTS_ICONS='always').stdout
                self.assertEqual(actual, expected)

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
        colors=self.home/'config/dots/themes/example/colors.toml';colors.write_text(colors.read_text()+'# manual change\n')
        self.cli('edit','example','--adjust','gamma=2','--yes',code=1)
        self.assertTrue(colors.read_text().endswith('# manual change\n'))
        self.cli('create','../escape','--color','#ffffff','--yes',code=1)
        self.cli('create','invalid','--color','#ffffff','--adjust','gamma=nan','--yes',code=1)
        self.cli('create','invalid','--color','#ffffff','--set','red=bad','--yes',code=1)
        (self.home/'config/dots/themes/link').symlink_to(self.home/'config/dots/themes/example')
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
        # Wallpaper preflight checks both the adapter and its runtime timeout.
        (self.tools/'timeout').symlink_to(shutil.which('timeout'))
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
        self.assertIn('No authored themes',self.cli('list',DOTS=str(self.root/'empty'),XDG_CONFIG_HOME=str(self.root/'empty-config')).stdout)

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
        before=digest(self.home/'config/dots/themes/example')
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
        self.run_command([sys.executable,'-B','-c',script,str(REPO/'plugins/anodize'),str(REPO/'lib/dots/files')],code=77)
        with self.author() as author:
            pending=[d for d in author.store().records() if d['status']=='applying']
            self.assertEqual(len(pending),1)
            author.store().recover(pending[0]['id'])
        self.assertEqual(digest(self.home/'config/dots/themes/example'),before)

if __name__=='__main__':
    unittest.main()
