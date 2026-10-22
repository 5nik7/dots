#!/usr/bin/env python3
"""Isolated weather contracts: no Android API, public HTTP or live installations."""
from contextlib import redirect_stdout
from datetime import datetime
import base64
import copy
import io
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
FZF_TAB = Path(os.environ.get('DOTS_TEST_FZF_TAB') or Path.home()/'.local/share/zinit/plugins/Aloxaf---fzf-tab')
sys.path.insert(0, str(ROOT / 'lib/dots/wttr'))
import core
sys.path.insert(0, str(ROOT / 'lib/dots/wttr'))
import cli
import completion
import stock
import styling


def sample():
    return {'current_condition': [{'weatherCode': '113', 'temp_F': '72', 'temp_C': '22',
            'FeelsLikeF': '74', 'FeelsLikeC': '23', 'humidity': '60', 'windspeedMiles': '5',
            'windspeedKmph': '8', 'precipInches': '0.0', 'precipMM': '0', 'winddir16Point': 'NW',
            'weatherDesc': [{'value': 'Sunny'}]}], 'nearest_area': [{'areaName': [{'value': 'Test Town'}]}],
            'weather': [{'date': datetime.now().date().isoformat(),
            'astronomy': [{'sunrise': '06:30 AM', 'sunset': '06:30 PM'}],
            'mintempF': '50', 'maxtempF': '75', 'mintempC': '10', 'maxtempC': '24',
            'hourly': [{'time': '1200', 'weatherCode': '113', 'tempF': '72', 'tempC': '22', 'weatherDesc': [{'value': 'Sunny'}]}]}]}


class Weather(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory(prefix='wttr-test-')
        self.addCleanup(t.cleanup)
        self.root = Path(t.name)
        self.home = self.root / 'home space ü'
        self.home.mkdir()
        env = {k: os.environ[k] for k in ('PATH','PREFIX','LD_PRELOAD','LD_LIBRARY_PATH','SystemRoot','COMSPEC') if k in os.environ}
        env.update(HOME=str(self.home), USERPROFILE=str(self.home), APPDATA=str(self.home / 'roaming'),
                   LOCALAPPDATA=str(self.home / 'local'), XDG_CONFIG_HOME=str(self.home / 'config'),
                   XDG_CACHE_HOME=str(self.home / 'cache'), XDG_STATE_HOME=str(self.home / 'state'),
                   XDG_DATA_HOME=str(self.home / 'data'), TERM='xterm-256color', DOTS_PROGRESS='never')
        self.environment = patch.dict(os.environ, env, clear=True)
        self.environment.start(); self.addCleanup(self.environment.stop)
        self.path = self.home / 'config/wttr/config.toml'
        self.path.parent.mkdir(parents=True)
        shutil.copy2(ROOT / 'config/wttr/config.toml', self.path)
        _, self.cfg = core.config()
        self.cache = core.Cache(self.cfg)
        self.data = sample()

    def palette(self, colors=None):
        path = Path(os.environ['XDG_STATE_HOME']) / 'dots/current/theme/palette.json'
        path.parent.mkdir(parents=True, exist_ok=True)
        colors = colors if colors is not None else dict(cyan='#06B6D4', blue='#3B82F6',
            green='#22C55E', yellow='#EAB308', orange='#F97316', red='#EF4444',
            muted='#9CA3AF', magenta='#A78BFA')
        path.write_text(json.dumps(dict(colors=colors)))
        return path

    def seed(self, age=0):
        row = dict(schema=2, updated=time.time()-age, location='Test Town', source='fixture', data=self.data)
        core.atomic(self.cache.path, row)
        return row

    def run_cli(self, *args):
        return subprocess.run([sys.executable, '-B', str(ROOT / 'lib/dots/wttr/cli.py'), *args],
                              capture_output=True, text=True, timeout=5)

    def test_defaults_icons_and_config_errors(self):
        self.assertEqual(self.cfg['units'], 'us')
        self.assertEqual(self.cfg['default_location'], '')
        self.assertEqual(len(self.cfg['icons']), 49)
        self.assertTrue(all(0xe000 <= ord(v) <= 0xf8ff for v in self.cfg['icons'].values()))
        self.path.write_text('units = "bad"')
        with self.assertRaises(ValueError): core.config()
        self.path.write_text('[broken')
        with self.assertRaises(ValueError): core.config()

    def test_temperature_scale_boundaries_conversion_and_config_validation(self):
        cases=[(-10,0),(32,0),(32.01,1),(59.99,1),(60,2),(74.99,2),(75,3),(84.99,3),(85,4),(94.99,4),(95,5),(120,5)]
        for value,index in cases:
            self.assertEqual(styling.temperature_color(value,self.cfg),styling.COLORS[index])
            metric=copy.deepcopy(self.cfg);metric['units']='metric'
            self.assertEqual(styling.temperature_color((value-32)*5/9,metric),styling.COLORS[index])
        for value in ('?',None,'NaN','inf'):
            self.assertEqual(styling.temperature_color(value,self.cfg),'default')
        cfg=copy.deepcopy(self.cfg);cfg['temperature_scale']['colors'][2]='#010203'
        self.assertEqual(styling.temperature_color(72,cfg),'#010203')
        self.assertEqual(styling.sgr('#010203'),'38;2;1;2;3')
        cfg['temperature_scale']=dict(unit='C',thresholds=[0,10,20,30,40],colors=styling.COLORS)
        self.assertEqual(styling.temperature_color(68,cfg),styling.COLORS[3])
        invalid=[{'show_location_attribution':'false'}, {'widget_color':'yes'}, {'widget_color_format':'html'},
                 {'temperature_scale':{'unit':'K'}}, {'temperature_scale':{'thresholds':[0,1,1,2,3]}},
                 {'temperature_scale':{'thresholds':[0,1,2,3,float('inf')]}},
                 {'temperature_scale':{'thresholds':[False,1,2,3,4]}},
                 {'temperature_scale':{'thresholds':[0,1,2,3,10**400]}},
                 {'temperature_scale':{'colors':['not-a-color']*6}}, {'icon_colors':{'113':'#fff'}},
                 {'night_icon_colors':{'113':'\x1b[31m'}}]
        for change in invalid:
            cfg=copy.deepcopy(self.cfg);cfg.update(change)
            with self.subTest(change=change),self.assertRaises(ValueError):styling.validate_config(cfg)
        self.path.write_text('default_location="Test City"\n')
        self.assertTrue(core.config()[1]['show_location_attribution'])

    def test_theme_colors_literal_overrides_and_snapshot_per_render(self):
        path = self.palette(dict(blue='#123456', muted='#abcdef', magenta='#fedcba',
                                 color0='#010101', color7='#eeeeee', color15='#ffffff'))
        with patch.object(core, 'read_regular', wraps=core.read_regular) as read:
            colors = styling.Colors()
            self.assertEqual(colors.resolve('blue'), '#123456')
            self.assertEqual(colors.resolve('indigo'), '#123456')
            self.assertEqual(colors.resolve('gray'), '#abcdef')
            self.assertEqual(colors.resolve('grey'), '#abcdef')
            self.assertEqual(colors.resolve('purple'), '#fedcba')
            self.assertEqual(colors.resolve('black'), '#010101')
            self.assertEqual(colors.resolve('white'), '#eeeeee')
            self.assertEqual(colors.resolve('bright_white'), '#ffffff')
            self.assertEqual(read.call_count, 1)
        self.palette(dict(blue='#654321'))
        self.assertEqual(colors.resolve('blue'), '#123456')
        self.assertEqual(styling.Colors().resolve('blue'), '#654321')
        with patch.object(core, 'read_regular', side_effect=AssertionError('unnecessary palette read')):
            literal = styling.Colors()
            for value, expected in [('#123abc', '#123abc'), (0, 0), (255, 255), ('033', 33), ('default', 'default')]:
                self.assertEqual(literal.resolve(value), expected)
            self.assertEqual(styling.Colors(enabled=False).sgr('blue'), None)
        self.assertEqual(styling.Colors().sgr('33'), '38;5;33')
        # The publication directory may be a link; the payload must remain regular.
        if os.name == 'posix':
            target = self.root / 'palette-target.json'
            path.rename(target); path.symlink_to(target)
            self.assertEqual(styling.Colors().resolve('blue'), 4)

    def test_palette_fallbacks_and_invalid_config_colors(self):
        self.assertEqual(styling.Colors().resolve('foreground'), 'default')
        self.assertEqual(styling.Colors().resolve('orange'), 208)
        self.assertEqual(styling.Colors().resolve('bright_blue'), 12)
        path = self.palette()
        for raw in ('{broken', '[]', '{"colors":[]}', '{"colors":{"blue":"#[fg=red]"}}',
                    '[' * 2000, ' ' * (styling.PALETTE_LIMIT + 1)):
            path.write_text(raw)
            self.assertEqual(styling.Colors().resolve('blue'), 4)
        for value in (-1, 256, '256', True, False, 33.0, '1.0', '#fff', '#12345g',
                      'Blue', 'unknown', '\x1b[31m', 'red]#[bg=blue', None):
            for group in ('temperature_scale', 'icon_colors', 'night_icon_colors'):
                cfg = copy.deepcopy(self.cfg)
                if group == 'temperature_scale': cfg[group]['colors'][0] = value
                else: cfg[group]['113'] = value
                with self.subTest(value=value, group=group), self.assertRaises(ValueError):
                    styling.validate_config(cfg)
        self.path.write_text('[temperature_scale]\ncolors=["cyan",33,"green","#123456","208","red"]\n'
                             '[icon_colors]\n"113"=255\n[night_icon_colors]\n"113"="blue"\n')
        _, cfg = core.config()
        self.assertEqual(cfg['temperature_scale']['colors'][1], 33)
        self.assertEqual(cfg['icon_colors']['113'], 255)
        self.path.write_text('[icon_colors]\n"113"=256\n')
        result = self.run_cli('--current', '--cached')
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, '')

    def test_theme_and_index_colors_in_widgets_and_plain_bypass(self):
        self.palette(dict(green='#abcdef', yellow='#123456', blue='#654321'))
        values = core.fields(self.seed(), self.cfg)
        values['daylight'] = 'day'
        cfg = copy.deepcopy(self.cfg)
        cfg['widget_color'] = 'always'
        cfg['icon_colors']['113'] = '33'
        ui = cli.Presentation(io.StringIO())
        template = '{icon} {temperature}{unit}'
        text = styling.widget(template, values, cfg, ui)
        self.assertIn('\x1b[38;5;33m', text)
        self.assertIn('\x1b[38;2;171;205;239m72', text)
        cfg['widget_color_format'] = 'tmux'
        text = styling.widget(template, values, cfg, ui)
        self.assertIn('#[fg=colour33]', text)
        self.assertIn('#[fg=#abcdef]72', text)
        self.assertTrue(text.endswith('#[default]#[pop-default]'))
        cfg['widget_color_format'] = 'plain'
        with patch.object(core, 'read_regular', side_effect=AssertionError('plain palette read')):
            self.assertEqual(styling.widget(template, values, cfg, ui), values['icon'] + ' 72°F')
        with patch.object(styling, 'Colors', side_effect=AssertionError('machine palette read')):
            for args in (['--json'], ['get', 'temperature'], ['--daylight']):
                with redirect_stdout(io.StringIO()) as out:
                    self.assertEqual(cli.main(args + ['--cached', '--color', 'always']), 0)
                self.assertNotIn('\x1b', out.getvalue())

    def test_aligned_weather_spacing_and_wrapping(self):
        from resources import cells
        row = self.seed()
        row['data']['current_condition'][0].update(temp_F='53', weatherDesc=[{'value':' Clear  '}])
        row['data']['weather'][0]['hourly'][0].update(weatherCode='122', weatherDesc=[{'value':' Overcast '}])
        cfg = copy.deepcopy(self.cfg)
        cfg['icons']['113'] = cfg['night_icons']['113'] = '\ue32b'
        cfg['icons']['122'] = '\ue312'
        args = cli.parser().parse_args([])
        def view(width, color='never', icons='always'):
            with patch.dict(os.environ, COLUMNS=str(width), DOTS_COLOR=color, DOTS_ICONS=icons), redirect_stdout(io.StringIO()) as out:
                cli.render(row, cfg, args, 0)
            return re.sub(r'\x1b\[[0-9;]*m', '', out.getvalue())
        for width in (40,80,120):
            plain = view(width)
            self.assertIn('    Now        \ue32b Clear 53°F\n', plain)
            self.assertIn('    Midday     \ue312 Overcast\n', plain)
            self.assertEqual(view(width, color='always'), plain)
            self.assertIn('    Now        Clear 53°F\n', view(width, icons='never'))
            self.assertIn('    Midday     Overcast\n', view(width, icons='never'))
            args.hourly = True
            self.assertIn('72°F \ue312 Overcast', view(width))
            args.hourly = False
        cfg['icons']['113'] = cfg['night_icons']['113'] = ''
        cfg['icons']['122'] = ''
        self.assertIn('    Now        Clear 53°F\n', view(80))
        self.assertIn('    Midday     Overcast\n', view(80))
        row['data']['current_condition'][0]['weatherDesc'] = [{'value':'雲 long weather ' * 12}]
        for width in (40,80,120):
            text = view(width)
            self.assertTrue(all(cells(line) <= width for line in text.splitlines()), text)
            self.assertIn('53°F', text)
        with patch.object(core, 'read_regular', side_effect=AssertionError('plain palette read')):
            view(80)

    def test_forecast_icons_colors_and_attribution_setting(self):
        self.palette()
        from datetime import timedelta
        row=self.seed();row['attribution']='Location credit'
        self.assertFalse(self.cfg['show_location_attribution'])
        day=row['data']['weather'][0]
        day['date']=(datetime.now().date()+timedelta(days=1)).isoformat()
        day['hourly']=[dict(time='0',weatherCode='113',tempF='32',tempC='0',weatherDesc=[{'value':'Clear'}]),
                       dict(time='1200',weatherCode='296',tempF='85',tempC='29.44',weatherDesc=[{'value':'Rain'}])]
        self.assertTrue(styling.forecast_night(row['data'],day,0))
        self.assertFalse(styling.forecast_night(row['data'],day,1200))
        args=cli.parser().parse_args(['--hourly'])
        with patch.dict(os.environ,DOTS_COLOR='always',DOTS_ICONS='always'),redirect_stdout(io.StringIO()) as out:
            cli.render(row,self.cfg,args,0)
        text=out.getvalue()
        self.assertNotIn('Location credit',text)
        self.assertIn('\x1b[38;2;6;182;212m32°F',text)
        self.assertIn('\x1b[38;2;249;115;22m85°F',text)
        self.assertIn(self.cfg['night_icons']['113'],text)
        self.assertIn(self.cfg['icons']['296'],text)
        args.hourly=False
        with patch.dict(os.environ,DOTS_COLOR='always',DOTS_ICONS='always'),redirect_stdout(io.StringIO()) as out:
            cli.render(row,dict(self.cfg,show_location_attribution=True),args,0)
        text=out.getvalue()
        self.assertIn('Location credit',text)
        self.assertIn('\x1b[38;2;59;130;246m50',text)
        self.assertIn('\x1b[38;2;234;179;8m75°F',text)
        self.assertIn(self.cfg['icons']['296'],text)
        cfg=copy.deepcopy(self.cfg);cfg['icon_colors']['296']='#010203'
        self.assertEqual(styling.condition('296',cfg)[1],'#010203')
        self.assertEqual(styling.condition('999',cfg)[1],'default')
        with patch.dict(os.environ,DOTS_COLOR='never',DOTS_ICONS='never'),redirect_stdout(io.StringIO()) as out:
            cli.render(row,self.cfg,args,0)
        self.assertNotIn('\x1b',out.getvalue())
        self.assertNotIn(self.cfg['icons']['296'],out.getvalue())

    def test_widget_color_policy_formats_and_data_boundaries(self):
        self.palette()
        row=self.seed();values=core.fields(row,self.cfg)
        template='{temperature}{unit} {feels_like}{unit} {icon}'
        class TTY(io.StringIO):
            def isatty(self):return True
        ui=cli.Presentation(TTY())
        output=styling.widget(template,values,self.cfg,ui)
        self.assertIn('\x1b[38;2;34;197;94m72',output)
        ui=cli.Presentation(io.StringIO())
        self.assertNotIn('\x1b',styling.widget(template,values,self.cfg,ui))
        with patch.dict(os.environ,NO_COLOR='1'):
            self.assertNotIn('\x1b',styling.widget(template,values,self.cfg,cli.Presentation(TTY())))
            with patch.dict(os.environ,DOTS_COLOR='always'):
                self.assertIn('\x1b',styling.widget(template,values,self.cfg,ui))
                self.assertNotIn('\x1b',styling.widget(template,values,dict(self.cfg,widget_color_format='plain'),ui))
        cfg=dict(self.cfg,widget_color='always')
        with patch.dict(os.environ,DOTS_COLOR='never'):
            self.assertNotIn('\x1b',styling.widget(template,values,cfg,ui))
        markup=styling.widget('{temperature}{unit}',values,dict(self.cfg,widget_color_format='tmux'),ui)
        self.assertTrue(markup.startswith('#[push-default]'))
        self.assertTrue(markup.endswith('#[default]#[pop-default]'))
        self.assertNotIn('\x1b',markup)
        values['location']='#[fg=red]'
        with patch.dict(os.environ,DOTS_COLOR='never'):
            self.assertEqual(styling.widget('{location}',values,dict(self.cfg,widget_color_format='tmux'),ui),'##[fg=red]')
        for args in [('get','temperature'),('--json',),('--daylight',)]:
            result=self.run_cli(*args,'--cached','--color','always')
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertNotIn('\x1b',result.stdout)
            self.assertNotIn('#[',result.stdout)
        self.assertIn('\x1b[38;2;',self.run_cli('--widget','--cached','--color','always').stdout)
        self.assertNotIn('\x1b',self.run_cli('--widget','--cached').stdout)

    def test_native_config_destination_and_catalog(self):
        from app_paths import config_directory
        with patch.dict(os.environ, XDG_CONFIG_HOME=''):
            self.assertEqual(config_directory('wttr'),Path(os.environ['APPDATA'])/'wttr')
        self.assertEqual(config_directory('wttr'),Path(os.environ['XDG_CONFIG_HOME'])/'wttr')
        resource=next(r for r in json.loads((ROOT/'.dots/files.json').read_text())['resources'] if r['id']=='wttr')
        self.assertEqual(resource['targets']['windows'],'${APP_CONFIG:wttr}')
        self.assertFalse(core.cache_root().exists())

    @unittest.skipUnless(os.name == 'posix' and shutil.which('tmux'), 'native tmux unavailable')
    def test_native_tmux_widget_escaping_and_style_restoration(self):
        import shlex
        from test_tmux_status import TmuxStatus
        fixture=TmuxStatus('test_layout_and_template_ownership');fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        inner,base=fixture.server('widget');outer,_=fixture.server('widget-view',termux=False)
        inner('set-option','-g','status-position','top')
        inner('set-option','-g','status-interval','1')
        outer('set-option','-g','status','off')
        outer('set-option','-g','default-terminal','tmux-256color')
        attach=shlex.join(['env','-u','TMUX','-u','TMUX_PANE',*base,'attach-session','-t','fixture'])
        outer('new-session','-d','-s','view','-x','80','-y','24',attach)
        target=fixture.home/'widget-output'
        self.palette()
        cfg=dict(self.cfg,widget_color_format='tmux')
        values=core.fields(self.seed(),cfg)
        for width in (40,80,120):
            outer('resize-window','-t','view','-x',str(width),'-y','24')
            for literal in ('#[bg=red]','#{pid}','#(touch BAD)'):
                values['location']=literal
                target.write_text(styling.widget('{location} {temperature}{unit}',values,cfg,cli.Presentation(io.StringIO())))
                inner('set-option','-g','status-format[0]','#[fg=#abcdef,bg=#112233]before #('+shlex.join(['cat',str(target)])+') after')
                inner('refresh-client','-S')
                lines=fixture.await_screen(outer,'view',lambda rows: bool(rows) and literal+' 72°F after' in rows[0])
                self.assertEqual(fixture.colors_at(lines[0],'72')['fg'],(34,197,94))
                self.assertEqual(fixture.colors_at(lines[0],'after')['fg'],(171,205,239))
                self.assertEqual(fixture.colors_at(lines[0],'after')['bg'],(17,34,51))
        self.assertFalse((fixture.home/'BAD').exists())

    def test_strict_cached_missing_is_read_only(self):
        cache_root = core.cache_root()
        for args, expected in [(('--daylight','--cached'),'unknown\n'), (('--widget','--cached'),'?\n')]:
            result = self.run_cli(*args)
            self.assertEqual((result.returncode,result.stdout,result.stderr), (0,expected,''))
        self.assertFalse(cache_root.exists())
        with patch.object(core, 'geo_helper', side_effect=AssertionError('no providers')):
            with redirect_stdout(io.StringIO()): self.assertEqual(cli.main(['--cached','--daylight']), 0)

    def test_cache_fresh_stale_expired_and_future(self):
        for age, usable, stale_ok in [(0,True,True),(901,False,True),(21601,False,False),(-60,False,False)]:
            row=self.seed(age)
            self.assertEqual(self.cache.usable(row), usable)
            self.assertEqual(self.cache.usable(row, True), stale_ok)
        self.cache.path.write_text('{broken')
        self.assertEqual(self.cache.read(), {})
        self.cache.path.write_text('{"schema":1,"updated":NaN}')
        self.assertEqual(self.cache.read(), {})
        self.cache.path.write_text('[' * 2000)
        self.assertEqual(self.cache.read(), {})

    def test_daylight_boundaries_and_bad_astronomy(self):
        date=datetime.now()
        for hour, minute, expected in [(6,29,'night'),(6,30,'day'),(18,29,'day'),(18,30,'night'),(23,59,'night')]:
            self.assertEqual(core.astronomy(self.data,date.replace(hour=hour,minute=minute))[2], expected)
        for solar in [None,{},[],[{}],[{'sunrise':'No sunrise','sunset':'06:30 PM'}],
                      [{'sunrise':'08:00 PM','sunset':'06:00 AM'}]]:
            data=copy.deepcopy(self.data);data['weather'][0]['astronomy']=solar
            self.assertEqual(core.astronomy(data)[2],'unknown')
        self.data['weather'][0]['date']='2000-01-01'
        self.assertEqual(core.astronomy(self.data)[2],'unknown')

    def test_machine_modes_and_templates_are_literal(self):
        self.seed()
        result=self.run_cli('--json','--cached','--color','always','--icons','always')
        self.assertEqual(json.loads(result.stdout), self.data)
        self.assertEqual(result.stderr,'')
        self.assertNotIn('\x1b', result.stdout)
        self.assertEqual(self.run_cli('get','temperature','--cached','--color','always').stdout,'72\n')
        self.assertEqual(self.run_cli('--get','temperature','--units','metric','--cached').stdout,'22\n')
        self.assertEqual(self.run_cli('--icons','never','get','icon','--cached').stdout,'\n')
        self.assertEqual(self.run_cli('--format','{temperature}{unit} {{literal}}','--cached').stdout,'72°F {literal}\n')
        for template in ['{temperature.__class__}','{icon!r}','{icon:>8}','{not_a_field}','\x1b[31m{icon}']:
            self.assertNotEqual(self.run_cli('--format',template,'--cached').returncode,0)
        self.assertEqual(self.run_cli('--format','$(touch BAD) {temperature}','--cached').stdout,'$(touch BAD) 72\n')
        self.assertFalse((ROOT/'BAD').exists())
        self.seed(1000)
        self.assertEqual(self.run_cli('--widget','--cached').stdout[-2:],'~\n')
        self.assertEqual(self.run_cli('--daylight','--cached').stdout,'unknown\n')
        self.assertEqual(self.run_cli('--get','stale','--cached','--allow-stale').stdout,'true\n')
        self.assertNotEqual(self.run_cli('--get','temperature','--cached').returncode,0)

    def test_geo_city_precedence_and_no_ip(self):
        geo = json.dumps(dict(version=1, city='Test City', attribution='© OpenStreetMap contributors')).encode()
        with patch.object(core,'geo_helper',return_value='termux-geo'), patch.object(core,'bounded_command',return_value=geo) as run:
            self.assertEqual(core.resolve_location(None,self.cfg,True,20), ('Test City','cached city','© OpenStreetMap contributors'))
            self.assertEqual(run.call_args.args[0],['termux-geo','--json','--max-age','86400','--cached'])
            core.resolve_location(None,self.cfg,False,20)
            self.assertNotIn('--cached',run.call_args.args[0])
            self.assertNotIn('--max-age',run.call_args.args[0])
            self.assertNotIn('--refresh',run.call_args.args[0])
        for value in (b'', b'NaN', b'bad', b'1,2', b'[]', b'['*2000,
                      b'{"version":1,"city":null}', b'{"version":1,"city":42}',
                      b'{"version":1,"city":""}', b'{"version":2,"city":"Wrong version"}',
                      b'{"version":1,"city":"Town","attribution":[]}', b'{}'):
            with patch.object(core,'geo_helper',return_value='missing'),patch.object(core,'bounded_command',return_value=value):
                with self.assertRaises(core.Unavailable): core.resolve_location(None,self.cfg,True,1)
        for failure in (FileNotFoundError(), core.Unavailable('timeout')):
            with patch.object(core,'geo_helper',return_value='missing'),patch.object(core,'bounded_command',side_effect=failure):
                with self.assertRaises(core.Unavailable): core.resolve_location(None,self.cfg,True,1)
        with patch.object(core,'geo_helper',return_value=None):
            with self.assertRaises(core.Unavailable): core.resolve_location(None,self.cfg,False,1)
        with patch.object(core,'geo_helper',side_effect=AssertionError('configured input must not locate')):
            cfg=dict(self.cfg,default_location='Oslo')
            self.assertEqual(core.resolve_location('Paris',cfg,False,1),('Paris','manual',''))
            self.assertEqual(core.resolve_location(None,cfg,True,1),('Oslo','default',''))

    def test_city_label_cache_version_and_explicit_recovery(self):
        import hashlib
        old_identity=['auto',False,self.cfg['default_location'],self.cfg['language']]
        old_path=core.cache_root()/(hashlib.sha256(json.dumps(old_identity).encode()).hexdigest()+'.json')
        old=dict(schema=1,updated=time.time(),location='1,2',data=self.data)
        core.atomic(old_path,old)
        self.assertEqual(self.cache.read(),{})
        self.assertEqual(self.run_cli('--cached','--daylight').stdout,'unknown\n')
        attribution='© OpenStreetMap contributors'
        with patch.object(core,'resolve_location',return_value=('Actual City','city',attribution)),patch.object(core,'fetch',return_value=self.data) as fetch:
            self.cache.refresh(force=True)
            self.assertEqual(fetch.call_args.args[0],'Actual City')
        self.assertEqual(self.run_cli('get','location','--cached').stdout,'Actual City\n')
        view=self.run_cli('--current','--cached')
        self.assertIn('Weather — Actual City',view.stdout)
        self.assertNotIn(attribution,view.stdout)
        self.path.write_text(self.path.read_text().replace('show_location_attribution = false','show_location_attribution = true'))
        self.assertIn(attribution,self.run_cli('--current','--cached').stdout)
        self.assertNotIn('Test Town',view.stdout)
        self.assertEqual(json.loads(self.run_cli('--json','--cached').stdout),self.data)
        self.assertEqual(json.loads(old_path.read_text()),old)

    def test_bounded_helpers_timeout_stderr_oversize_and_missing(self):
        self.assertEqual(core.bounded_command([sys.executable,'-c','import sys; print("1,2"); print("PRIVATE",file=sys.stderr)'],1,32),b'1,2\n')
        for command in [[sys.executable,'-c','import time; time.sleep(10)'],
                        [sys.executable,'-c','print("x"*100000)']]:
            start=time.monotonic()
            with self.assertRaises(core.Unavailable):core.bounded_command(command,.2,32)
            self.assertLess(time.monotonic()-start,1)
        with self.assertRaises(OSError):core.bounded_command([str(self.home/'missing')],1)

    def fake_stock_providers(self):
        directory=self.home/'fake bin';directory.mkdir()
        curl=directory/'curl'
        curl.write_text('#!'+sys.executable+'\n'+'''import json, os, pathlib, sys, time
home=pathlib.Path(os.environ['HOME'])
with (home/'curl-calls').open('a') as f: f.write(json.dumps(sys.argv[1:])+'\\n')
print('PRIVATE curl stderr',file=sys.stderr)
mode=os.environ.get('WTTR_TEST_MODE','ok')
if mode=='timeout': time.sleep(10)
if mode=='fail': sys.exit(22)
if mode=='large': sys.stdout.buffer.write(b'x'*(4*1024*1024+1)); sys.exit()
sys.stdout.buffer.write(b'\\x1b[33mStock\\x1b[0m\\r\\nraw\\x00bytes')
''')
        curl.chmod(0o700)
        geo=directory/'termux-geo'
        geo.write_text('#!'+sys.executable+'\n'+'''import json, os, pathlib, sys
home=pathlib.Path(os.environ['HOME'])
with (home/'geo-calls').open('a') as f: f.write(json.dumps(sys.argv[1:])+'\\n')
print('PRIVATE geo stderr',file=sys.stderr)
print(json.dumps(dict(version=1,city='Auto City',attribution='OpenStreetMap contributors')))
''')
        geo.chmod(0o700)
        os.environ.update(PATH=str(directory)+os.pathsep+os.environ['PATH'],TERMUX_VERSION='fixture')
        return directory

    @unittest.skipUnless(os.name == 'posix', 'native executable fake curl')
    def test_stock_urls_raw_bytes_auto_city_and_no_weather_cache(self):
        self.fake_stock_providers()
        cases=[(['m','2','T'],'Auto%20City?m2T'),(['m2T'],'Auto%20City?m2T'),
               (['u0','--location','London'],'London?u0'),
               (['format=3'],'Auto%20City?format=3'),
               (['m','format=%l: %t'],'Auto%20City?m&format=%25l%3A+%25t'),
               (['--location','A/B ü &?#','format=*'],'A%2FB%20%C3%BC%20%26%3F%23?format=%2A'),
               (['Paris','m','--language','fr','2'],'Paris?m2&lang=fr'),
               (['moon'],'moon'),(['moon@2016-10-25'],'moon@2016-10-25'),
               ([':help'],':help'),([':bash.function'],':bash.function'),([':translation'],':translation')]
        cases.extend(([flag,'--location','London'],'London?'+flag) for flag in cli.STOCK_FLAGS)
        for args, suffix in cases:
            with self.subTest(args=args):
                result=subprocess.run([sys.executable,'-B',str(ROOT/'lib/dots/wttr/cli.py'),*args,'--color','always'],capture_output=True,timeout=5)
                self.assertEqual((result.returncode,result.stdout,result.stderr),(0,b'\x1b[33mStock\x1b[0m\r\nraw\x00bytes',b''))
                argv=json.loads((self.home/'curl-calls').read_text().splitlines()[-1])
                self.assertEqual(argv[-1],'https://wttr.in/'+suffix)
                self.assertEqual(argv[0],'-q')
                self.assertIn('--globoff',argv)
                self.assertIn('--max-time',argv)
        calls=[json.loads(line) for line in (self.home/'geo-calls').read_text().splitlines()]
        self.assertEqual(len(calls),4)
        self.assertTrue(all(call[:1]==['--json'] and '--refresh' not in call for call in calls))
        self.assertFalse(core.cache_root().exists())

    @unittest.skipUnless(os.name == 'posix', 'native executable fake curl')
    def test_stock_config_override_missing_curl_and_failures(self):
        directory=self.fake_stock_providers()
        self.path.write_text('default_location = "Config City"\n')
        result=self.run_cli('m2')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads((self.home/'curl-calls').read_text().splitlines()[-1])[-1],'https://wttr.in/Config%20City?m2')
        self.assertFalse((self.home/'geo-calls').exists())
        for mode in ('fail','timeout','large'):
            with patch.dict(os.environ,WTTR_TEST_MODE=mode):
                started=time.monotonic()
                result=self.run_cli('m2','--timeout','1')
                self.assertEqual(result.returncode,1)
                self.assertEqual(result.stdout,'')
                self.assertNotIn('PRIVATE',result.stderr)
                self.assertLess(time.monotonic()-started,3)
        (directory/'curl').unlink()
        with patch.dict(os.environ,PATH=str(directory)):
            result=self.run_cli('moon')
        self.assertEqual(result.returncode,1)
        self.assertIn('require curl',result.stderr)

    def test_stock_conflicts_and_special_routes_never_locate(self):
        invalid=[['m2','--cached'],['format=3','--widget'],['u','--days','2'],
                 ['T','--format','{icon}'],['m','--get','temperature'],['m','--json'],
                 ['m','--refresh'],['m','--fields'],['m','--units','us'],
                 ['format=1','format=2'],['format='],['moon@2023-02-29'],
                 ['moon@today'],['moon','Paris'],['moon','--location','Paris'],
                 [':unknown'],[':help','format=3']]
        with patch.object(core,'geo_helper',side_effect=AssertionError('must not locate')),patch.object(stock,'bounded_command',side_effect=AssertionError('must not fetch')):
            for args in invalid:
                with self.subTest(args=args), self.assertRaises(ValueError): cli.main(args)
        for route in ['moon','moon@2024-02-29',':help',':bash.function',':translation']:
            request,rest=stock.classify([route]);self.assertFalse(rest)
            with patch.object(stock,'resolve_location',side_effect=AssertionError('must not locate')),patch.object(stock.shutil,'which',return_value='curl'),patch.object(stock,'bounded_command',return_value=b'raw'):
                self.assertEqual(stock.fetch(request,None,self.cfg),(b'raw',''))
        # Reserved words remain available as explicit literal locations.
        self.assertEqual(stock.classify([]),(None,[]))
        with patch.object(core,'geo_helper',side_effect=AssertionError('must not locate')):
            self.assertEqual(core.resolve_location('m2',self.cfg,False,1),('m2','manual',''))

    @unittest.skipUnless(os.name == 'posix', 'native executable fake curl')
    def test_stock_native_bridge_and_literal_input(self):
        self.fake_stock_providers()
        arguments=['--location','-Town $(touch BAD) ü','format=%l: %t']
        args=base64.b64encode(json.dumps(arguments).encode()).decode()
        result=subprocess.run([sys.executable,'-B',str(ROOT/'lib/dots/native.py'),'wttr',args],cwd=self.home,capture_output=True,timeout=5)
        self.assertEqual((result.returncode,result.stdout,result.stderr),(0,b'\x1b[33mStock\x1b[0m\r\nraw\x00bytes',b''))
        self.assertFalse((self.home/'BAD').exists())

    def test_refresh_failure_cooldown_and_explicit_recovery(self):
        old=self.seed(1000)
        with patch.object(core,'resolve_location',return_value=('Test Town','fixture','')),patch.object(core,'fetch',side_effect=core.Unavailable('timeout')) as fetch:
            with self.assertRaises(core.Unavailable):self.cache.refresh()
            self.assertEqual(self.cache.read()['data'],old['data'])
            self.cache.refresh()
            self.assertEqual(fetch.call_count,1)
        with patch.object(core,'resolve_location',return_value=('Test Town','fixture','')),patch.object(core,'fetch',return_value=self.data):
            row=self.cache.refresh(force=True)
        self.assertTrue(self.cache.usable(row))
        self.assertEqual(row['retry_at'],0)
        self.assertNotIn('error',row)
        self.assertEqual(self.cache.path.stat().st_mode & 0o777,0o600)

    def test_failed_explicit_refresh_reports_failure_and_bad_format_never_polls(self):
        self.seed()
        with patch.object(core, 'resolve_location',return_value=('Test Town','fixture','')), patch.object(core,'fetch',side_effect=core.Unavailable('fixture failure')):
            with self.assertRaises(core.Unavailable):cli.main(['--refresh','--current'])
        with patch.object(core.subprocess,'Popen',side_effect=AssertionError('must not spawn')):
            with self.assertRaises(ValueError):cli.main(['--format','{bad.field}'])

    def test_schedule_coalesces_and_manual_cache_is_separate(self):
        with patch.object(core.subprocess,'Popen') as spawn:
            for _ in range(5): self.cache.schedule(self.path)
            self.assertEqual(spawn.call_count,1)
            payload=json.loads(spawn.call_args.args[0][-1]);self.assertIsNone(payload['location'])
        self.assertNotEqual(self.cache.path,core.Cache(self.cfg,'London').path)
        with patch.object(core,'resolve_location',return_value=('Test Town','fixture','')),patch.object(core,'fetch',return_value=self.data):
            self.cache.refresh(background=True)
        with patch.object(core.subprocess,'Popen') as spawn:
            self.cache.schedule(self.path)
            spawn.assert_not_called()
        with self.cache.locked():
            with self.assertRaises(OSError):self.cache.refresh(force=True)

    def test_http_json_errors_limits_retry_after_and_url(self):
        response=io.BytesIO(json.dumps(self.data).encode())
        with patch.object(core.urllib.request,'urlopen',return_value=response) as get:
            self.assertEqual(core.http_fetch('A/B ü','en',2)['data'],self.data)
            self.assertIn('A%2FB%20%C3%BC?format=j1&lang=en',get.call_args.args[0].full_url)
        for body in [b'broken',b'[]',b'{}',b'['*2000,b'NaN',b'x'*(core.LIMIT+1)]:
            with patch.object(core.urllib.request,'urlopen',return_value=io.BytesIO(body)):
                self.assertIn('error',core.http_fetch('London','en',1))
        error=core.urllib.error.HTTPError('url',429,'limited',{'Retry-After':'3600'},None)
        with patch.object(core.urllib.request,'urlopen',side_effect=error):
            self.assertEqual(core.http_fetch('London','en',1)['retry'],3600)

    @unittest.skipUnless(os.name != 'nt' and shutil.which('bash'), 'Bash entry point')
    def test_bash_entry_via_unicode_symlink_and_literal_location(self):
        link=self.home/'-weather ü';link.symlink_to(ROOT/'bin/wttr')
        result=subprocess.run([str(link),'--version'],capture_output=True,text=True,timeout=3)
        self.assertEqual((result.returncode,result.stdout,result.stderr),(0,core.VERSION+'\n',''))
        # A cached manual lookup must preserve literal punctuation and never execute it.
        cache=core.Cache(self.cfg,'-Town $(touch BAD) ü')
        row=self.seed();core.atomic(cache.path,row)
        result=subprocess.run([str(link),'--location=-Town $(touch BAD) ü','--cached','--get','temperature'],cwd=self.home,capture_output=True,text=True,timeout=3)
        self.assertEqual((result.returncode,result.stdout),(0,'72\n'))
        self.assertFalse((self.home/'BAD').exists())

    def test_help_metadata_native_bridge_and_invalid_options(self):
        for width in (40,80,120):
            with patch.dict(os.environ,COLUMNS=str(width)):
                result=self.run_cli('--help','--color','always')
            self.assertEqual(result.returncode,0)
            self.assertIn('\x1b[',result.stdout)
            for flag,_,_ in cli.OPTIONS:self.assertIn(flag,result.stdout)
        args=base64.b64encode(json.dumps(['--version']).encode()).decode()
        result=subprocess.run([sys.executable,'-B',str(ROOT/'lib/dots/native.py'),'wttr',args],capture_output=True,text=True)
        self.assertEqual((result.returncode,result.stdout),(0,core.VERSION+'\n'))
        for args in [('--days','4'),('--timeout','0'),('--cached','--refresh'),('--units','bad'),('--get','bad')]:
            self.assertNotEqual(self.run_cli(*args).returncode,0)
        self.assertFalse(core.cache_root().exists())

    def test_completion_install_backup_undo_and_idempotence(self):
        directory=self.home/'completion space ü'
        directory.mkdir();target=directory/'wttr.bash';target.write_text('old content\n')
        from file_platform import state_root
        from transactions import Store
        record,_=completion.install(['bash'],directory)
        self.assertIn('_wttr',target.read_text())
        again,_=completion.install(['bash'],directory)
        self.assertEqual(again['status'],'unchanged')
        store=Store(state_root())
        ops, guards, catalogs = store.inverse(record['id'])
        store.apply('undo', ops, guards, catalogs=catalogs)
        self.assertEqual(target.read_text(),'old content\n')
        target.unlink();target.symlink_to(directory/'missing')
        with self.assertRaises(ValueError):completion.install(['bash'],directory)

    def test_native_shell_completions(self):
        for shell in ('bash','zsh','fish'):
            exe=shutil.which(shell)
            if not exe:continue
            path=self.home/completion.FILES[shell];path.write_text(completion.generate(shell))
            if shell=='bash':
                cmd=['-c','source "$1"; COMP_WORDS=(wttr --units m); COMP_CWORD=2; _wttr; printf "%s\\n" "${COMPREPLY[@]}"','test',str(path)]
            elif shell=='zsh':
                cmd=['-f','-c','fpath=("${1:h}" $fpath); autoload -Uz compinit; compinit -D; autoload +X _wttr; _arguments() { print -r -- "$@"; }; words=(wttr --units m); _wttr','test',str(path)]
            else:
                cmd=['--no-config','-c','source "$argv[1]"; complete -C "wttr --units m"',str(path)]
            result=subprocess.run([exe,*cmd],capture_output=True,text=True,timeout=10)
            self.assertEqual(result.returncode,0,(shell,result.stderr))
            self.assertIn('metric',result.stdout)
            if shell in ('bash','fish'):
                for prefix, expected in [('wttr :trans',':translation'),('wttr m2 for','format=')]:
                    if shell=='bash':
                        words=prefix.split()
                        if words[-1].startswith(':'):
                            words[-1:]=[':',words[-1][1:]]
                            expected=expected[1:]
                        code='source "$1"; shift; COMP_WORDS=("$@"); COMP_CWORD=$((${#COMP_WORDS[@]}-1)); _wttr; printf "%s\\n" "${COMPREPLY[@]}"'
                        command=[exe,'-c',code,'test',str(path),*words]
                    else:
                        command=[exe,'--no-config','-c','source "$argv[1]"; complete -C "$argv[2]"',str(path),prefix]
                    result=subprocess.run(command,capture_output=True,text=True,timeout=10)
                    self.assertEqual(result.returncode,0,result.stderr)
                    self.assertIn(expected,result.stdout)
        for shell in cli.SHELLS:
            text=completion.generate(shell)
            for flag,_,_ in cli.OPTIONS:self.assertIn(flag[2:],text)
            for word in stock.STOCK_ROUTES:self.assertIn(word,text)
            self.assertIn('format=',text)
            self.assertNotIn('\x1b',text)

    @unittest.skipUnless(os.name == 'posix', 'native Unix PTYs')
    def test_native_pty_help_views_and_progress(self):
        self.palette()
        import fcntl, pty, select, struct, termios, re
        def terminal(argv, width):
            master, slave = pty.openpty()
            fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 30, width, 0, 0))
            env=dict(os.environ, DOTS_PROGRESS='auto', DOTS_COLOR='auto', DOTS_ICONS='never')
            child=subprocess.Popen(argv, stdin=slave, stdout=slave, stderr=slave, env=env, start_new_session=True)
            os.close(slave)
            result=b'';deadline=time.monotonic()+8
            try:
                while time.monotonic()<deadline:
                    if select.select([master],[],[],.1)[0]:
                        try: block=os.read(master,65536)
                        except OSError: break
                        if not block: break
                        result+=block
                    elif child.poll() is not None: break
                self.assertIsNotNone(child.poll() if child.poll() is not None else child.wait(timeout=1))
                self.assertEqual(child.returncode,0,result)
            finally:
                if child.poll() is None: child.kill()
                child.wait();os.close(master)
            return result.decode()
        for width in (40,80,120):
            output=terminal([sys.executable,'-B',str(ROOT/'lib/dots/wttr/cli.py'),'--help'],width)
            self.assertIn('\x1b[',output)
            plain=re.sub(r'\x1b\[[0-9;]*m','',output)
            self.assertTrue(all(len(line)<=width for line in plain.splitlines()), plain)
            self.assertNotIn('Fetching weather',output)
            self.seed()
            view=terminal([sys.executable,'-B',str(ROOT/'lib/dots/wttr/cli.py'),'--cached','--hourly'],width)
            self.assertIn('Test Town',view)
            self.assertIn('12:00',view)
            for extra in ([], ['--hourly']):
                view=terminal([sys.executable,'-B',str(ROOT/'lib/dots/wttr/cli.py'),
                               '--cached','--icons','always',*extra],width)
                plain=re.sub(r'\x1b\[[0-9;]*m','',view)
                self.assertRegex(plain, r'    Now        [\ue000-\uf8ff] Sunny 72°F\r?\n')
                if extra:
                    self.assertIn('72°F '+self.cfg['icons']['113']+' Sunny',plain)
                else:
                    self.assertIn('    Midday     '+self.cfg['icons']['113']+' Sunny',plain)
                self.assertTrue(all(cli.Presentation.clean(line) == line for line in plain.splitlines()))
                from resources import cells
                self.assertTrue(all(cells(line)<=width for line in plain.splitlines()),plain)
            widget=terminal([sys.executable,'-B',str(ROOT/'lib/dots/wttr/cli.py'),'--widget','--cached','--icons','always'],width)
            self.assertIn('\x1b[38;2;',widget)
        script="import sys,time; sys.path.insert(0,"+repr(str(ROOT/'lib/dots/wttr'))+"); import cli,core; "
        script+="core.resolve_location=lambda *a: ('Test Town','fixture',''); core.fetch=lambda *a: (time.sleep(.8),"+repr(self.data)+")[1]; "
        human=terminal([sys.executable,'-B','-c',script+"sys.exit(cli.main(['--refresh','--current']))"],80)
        self.assertIn('Fetching weather',human)
        self.assertIn('Weather — Test Town',human)
        data=terminal([sys.executable,'-B','-c',script+"sys.exit(cli.main(['--refresh','--json','--color','always']))"],80)
        self.assertNotIn('Fetching weather',data)
        self.assertNotIn('\x1b',data)
        self.assertEqual(json.loads(data),self.data)

    def test_real_background_worker_and_cached_geo_only(self):
        fixture=self.home/'fixture repo'
        shutil.copytree(ROOT/'lib/dots',fixture/'lib/dots',ignore=shutil.ignore_patterns('__pycache__'))
        (fixture/'config/wttr').mkdir(parents=True)
        shutil.copy2(self.path,fixture/'config/wttr/config.toml')
        provider=fixture/'androidots/bin/termux-geo';provider.parent.mkdir(parents=True)
        provider.write_text('#!'+sys.executable+'\nimport sys\nassert sys.argv[1:]==["--json","--max-age","86400","--cached"]\nprint(\'{"version":1,"city":"Test Town"}\')\n')
        provider.chmod(0o700)
        calls=self.home/'fetch-calls'
        copied=fixture/'lib/dots/wttr/core.py'
        with copied.open('a') as stream:
            stream.write('\ndef fetch(location, language, timeout):\n    assert location == "Test Town"\n    with Path('+repr(str(calls))+').open("a") as stream: stream.write("call\\n")\n    time.sleep(.3)\n    return '+repr(self.data)+'\n')
        command=[sys.executable,'-B',str(fixture/'lib/dots/wttr/cli.py'),'--daylight']
        env=dict(os.environ,TERMUX_VERSION='fixture',PATH=str(provider.parent)+os.pathsep+os.environ['PATH'])
        results=[subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env) for _ in range(4)]
        for p in results:
            out,err=p.communicate(timeout=5);self.assertEqual(p.returncode,0,err)
            self.assertIn(out,(b'unknown\n',b'day\n',b'night\n'));self.assertEqual(err,b'')
        deadline=time.monotonic()+5
        while not self.cache.usable(self.cache.read()):
            self.assertLess(time.monotonic(),deadline,'worker never published')
            time.sleep(.05)
        self.assertEqual(calls.read_text(),'call\n')
        self.assertEqual(self.cache.read()['source'],'cached city')
        before=self.cache.path.read_bytes()
        result=subprocess.run(command+['--cached'],env=env,capture_output=True,timeout=3)
        self.assertIn(result.stdout,(b'day\n',b'night\n'))
        self.assertEqual(before,self.cache.path.read_bytes())

    @unittest.skipUnless(os.name == 'posix' and shutil.which('zsh'), 'native Zsh PTY unavailable')
    def test_zsh_actual_tab_completion(self):
        import pty, select, signal
        directory=self.home/'completions';directory.mkdir()
        (directory/'_wttr').write_text(completion.generate('zsh'))
        rc=self.home/'.zshrc'
        rc.write_text("fpath=(\"$HOME/completions\" $fpath)\nautoload -Uz compinit; compinit -D\nPS1='READY> '\n_capture() { print -r -- \"$BUFFER\" > \"$HOME/buffer\"; exit; }\nzle -N _capture\nbindkey '^X' _capture\n")
        for text,expected in [('wttr --units m','wttr --units metric'),('wttr get sunr','wttr get sunrise'),('wttr :trans','wttr :translation'),('wttr m2 for','wttr m2 format=')]:
            target=self.home/'buffer';target.unlink(missing_ok=True)
            pid,fd=pty.fork()
            if not pid:
                env=dict(os.environ,ZDOTDIR=str(self.home))
                os.execve(shutil.which('zsh'),['zsh','-i'],env)
            data=b'';sent=False;deadline=time.monotonic()+8
            try:
                while time.monotonic()<deadline:
                    if select.select([fd],[],[],.05)[0]:
                        try:block=os.read(fd,65536)
                        except OSError:break
                        data+=block
                    if not sent and b'READY>' in data:
                        os.write(fd,text.encode()+b'\t');time.sleep(.3);os.write(fd,b'\x18');sent=True
                    if target.exists():break
                self.assertTrue(target.exists(),data)
                self.assertEqual(target.read_text().strip(),expected)
            finally:
                try:os.killpg(pid,signal.SIGKILL)
                except ProcessLookupError:pass
                os.waitpid(pid,0);os.close(fd)

    def test_cache_special_files_and_lease_recovery(self):
        root=core.cache_root();root.mkdir(parents=True)
        self.cache.path.symlink_to(self.home/'missing')
        self.assertEqual(self.cache.read(),{})
        with self.assertRaises(ValueError):core.atomic(self.cache.path,{'schema':2})
        self.cache.path.unlink()
        if hasattr(os,'mkfifo'):
            os.mkfifo(self.cache.path)
            started=time.monotonic();self.assertEqual(self.cache.read(),{})
            self.assertLess(time.monotonic()-started,.2)
            self.cache.path.unlink()
        core.atomic(self.cache.path,dict(schema=2,lease=time.time()-1))
        with patch.object(core.subprocess,'Popen') as spawn:
            self.cache.schedule(self.path)
            self.assertEqual(spawn.call_count,1)

    @unittest.skipUnless(os.name == 'posix' and shutil.which('bash'), 'native Bash PTY unavailable')
    def test_bash_actual_stock_tab_completion(self):
        import pty, select, signal
        (self.home/'wttr.bash').write_text(completion.generate('bash'))
        rc=self.home/'bashrc'
        rc.write_text('source "$HOME/wttr.bash"\nPS1="READY> "\n_capture() { printf "%s" "$READLINE_LINE" > "$HOME/buffer"; exit; }\nbind -x \'"\\C-x":_capture\'\n')
        for text,expected in [('wttr :trans','wttr :translation'),('wttr m2 for','wttr m2 format='),('wttr --units m','wttr --units metric')]:
            target=self.home/'buffer';target.unlink(missing_ok=True)
            pid,fd=pty.fork()
            if not pid:
                os.execve(shutil.which('bash'),['bash','--noprofile','--rcfile',str(rc),'-i'],dict(os.environ))
            data=b'';sent=False;deadline=time.monotonic()+8
            try:
                while time.monotonic()<deadline:
                    if select.select([fd],[],[],.05)[0]:
                        try:block=os.read(fd,65536)
                        except OSError:break
                        data+=block
                    if not sent and b'READY>' in data:
                        os.write(fd,text.encode()+b'\t');time.sleep(.3);os.write(fd,b'\x18');sent=True
                    if target.exists():break
                self.assertTrue(target.exists(),data)
                self.assertEqual(target.read_text().strip(),expected,data)
            finally:
                try:os.killpg(pid,signal.SIGKILL)
                except ProcessLookupError:pass
                os.waitpid(pid,0);os.close(fd)

    @unittest.skipUnless(os.name == 'posix' and shutil.which('zsh') and shutil.which('fzf') and (FZF_TAB/'fzf-tab.plugin.zsh').is_file(), 'native Zsh/FZF-tab unavailable')
    def test_native_fzf_tab_descriptions_and_insertion(self):
        import fcntl, struct, termios, shlex, re, select
        from bash_dots_pty import Terminal
        plugin=self.home/'fzf-tab'
        shutil.copytree(FZF_TAB,plugin,ignore=shutil.ignore_patterns('.git'))
        directory=self.home/'completions';directory.mkdir()
        (directory/'_wttr').write_text(completion.generate('zsh'))
        cases=[(width,'wttr m','Metric','Metric (SI) units','wttr m') for width in (40,80,120)]
        cases += [(80,'wttr :','upstream','Show upstream usage','wttr :help'),
                  (80,'wttr m2 ','Upstream format','Upstream format preset','wttr m2 format='),
                  (80,'wttr ',"'Quiet:",'Quiet: hide the Weather report','wttr q')]
        for width,typed,query,description,expected in cases:
            target=self.home/'buffer';target.unlink(missing_ok=True)
            terminal=Terminal(shutil.which('zsh'),dict(os.environ),self.home)
            try:
                fcntl.ioctl(terminal.master,termios.TIOCSWINSZ,struct.pack('HHHH',24,width,0,0))
                setup='fpath=("$HOME/completions" $fpath); autoload -Uz compinit; compinit -D; source '+shlex.quote(str(plugin/'fzf-tab.plugin.zsh'))
                setup+='; zstyle ":completion:*:descriptions" format "[%d]"; PROMPT="READY> "; wttr() { print BAD > "$HOME/provider-called"; }; _capture() { print -r -- "$BUFFER" > "$HOME/buffer"; }; zle -N _capture; bindkey "^X" _capture; print INITIALIZED\r'
                terminal.send(setup);terminal.wait(b'INITIALIZED\r\n')
                terminal.send(typed+'\t');terminal.wait(b'\x1b[?1000h')
                start=len(terminal.output)
                terminal.send('\x15'+query)
                deadline=time.monotonic()+8
                while True:
                    visible=re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]','',terminal.output[start:].decode(errors='replace'))
                    if description in visible and re.search(r'\b1/\d+',visible):break
                    self.assertLess(time.monotonic(),deadline,terminal.output[-2500:])
                    if select.select([terminal.master],[],[],.05)[0]:
                        terminal.output.extend(os.read(terminal.master,65536))
                terminal.send('\r');time.sleep(.25);terminal.send('\x18')
                deadline=time.monotonic()+5
                while not target.exists():
                    self.assertLess(time.monotonic(),deadline,terminal.output[-1500:])
                    time.sleep(.05)
                self.assertEqual(target.read_text().strip(),expected,terminal.output[-1500:])
                self.assertFalse((self.home/'provider-called').exists())
            finally:terminal.close()

    @unittest.skipUnless(shutil.which('pwsh') or shutil.which('powershell'), 'PowerShell 5.1/7 runtime unavailable')
    def test_native_powershell_entry_and_completion(self):
        engine=shutil.which('pwsh') or shutil.which('powershell')
        self.seed()
        source=self.home/'wttr.ps1';source.write_text(completion.generate('powershell'))
        quote=lambda x: "'"+str(x).replace("'","''")+"'"
        code='. '+quote(source)+"; (TabExpansion2 'wttr --units m' 14).CompletionMatches.CompletionText; & "+quote(ROOT/'bin/wttr.ps1')+' --get temperature --cached'
        result=subprocess.run([engine,'-NoProfile','-NonInteractive','-Command',code],capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('metric',result.stdout);self.assertIn('72',result.stdout)
        code='. '+quote(source)+"; (TabExpansion2 'wttr :trans' 11).CompletionMatches.CompletionText; (TabExpansion2 'wttr m2 for' 11).CompletionMatches.CompletionText"
        result=subprocess.run([engine,'-NoProfile','-NonInteractive','-Command',code],capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn(':translation',result.stdout);self.assertIn('format=',result.stdout)


if __name__=='__main__':unittest.main()
