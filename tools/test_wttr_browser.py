#!/usr/bin/env python3
"""Weather integration in isolated homes, mocked providers and private terminals."""
from contextlib import redirect_stdout, redirect_stderr
import base64
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import test_wttr as fixtures
from wttr import browser
from core import Cache, Unavailable
from interaction import SelectionEnded, SelectionEvent
from menu_tmux import read_request, request_file
from test_menus import NativeMenuFixture

ROOT = fixtures.ROOT


class WeatherBrowser(unittest.TestCase):
    setUp = fixtures.Weather.setUp
    seed = fixtures.Weather.seed
    palette = fixtures.Weather.palette
    run_cli = fixtures.Weather.run_cli
    fake_stock_providers = fixtures.Weather.fake_stock_providers

    def session(self, location=None):
        return browser.Session(self.path, dict(self.cfg), location)

    def command(self, args, *, native=False):
        command = ([sys.executable, '-B', str(ROOT/'lib/dots/cli.py')] if native else [str(ROOT/'bin/dots')])
        return subprocess.run([*command, *args], capture_output=True, text=True, timeout=10)

    def test_both_frontends_preserve_data_modes_and_statuses(self):
        self.seed()
        for args in [('--version',), ('--fields',), ('--json','--cached'), ('get','temperature','--cached'),
                     ('--daylight','--cached'), ('--widget','--cached'), ('--cached','--current'),
                     ('--days','9'), ('get','missing')]:
            expected = self.run_cli(*args, '--color', 'always')
            for native in (False, True):
                actual = self.command(['wttr', *args, '--color', 'always'], native=native)
                self.assertEqual((actual.returncode,actual.stdout,actual.stderr),
                                 (expected.returncode,expected.stdout,expected.stderr), (native,args))

    @unittest.skipUnless(os.name == 'posix', 'executable curl fixture')
    def test_stock_bytes_and_literal_locations_through_dots(self):
        self.fake_stock_providers()
        for command in ([str(ROOT/'bin/dots')], [sys.executable,'-B',str(ROOT/'lib/dots/cli.py')]):
            result=subprocess.run([*command,'wttr','m2T','--location','A/B ü &?#','--color','always'],capture_output=True,timeout=10)
            self.assertEqual((result.returncode,result.stdout,result.stderr),(0,b'\x1b[33mStock\x1b[0m\r\nraw\x00bytes',b''))
            self.assertIn('A%2FB%20%C3%BC%20%26%3F%23?m2T',(self.home/'curl-calls').read_text())
        self.assertFalse(fixtures.core.cache_root().exists())

    def test_help_completion_and_invalid_browse_never_create_cache(self):
        for native in (False, True):
            for args in (['wttr','--help'], ['help','wttr','browse'], ['wttr','browse','--help'],
                         ['wttr','completion','bash']):
                result = self.command(args, native=native)
                self.assertEqual(result.returncode, 0, result.stderr)
        for args in (['--json'], ['--cached'], ['--refresh'], ['--get','temperature'],
                     ['--widget'], ['m2T'], ['moon'], ['--units','bad'], ['--location',''], ['--timeout','0']):
            result = self.run_cli('browse', *args)
            self.assertEqual(result.returncode, 2, (args,result.stderr))
        self.assertFalse(fixtures.core.cache_root().exists())

    def test_dots_contextual_completion_and_generated_sources(self):
        for words, expected in [(['wttr','br'], 'browse'), (['wttr','browse','--un'], '--units'),
                                (['wttr','browse','--units','m'], 'metric'),
                                (['wttr','get','wind_i'], 'wind_icon'), (['wttr','--get','temp'], 'temperature'),
                                (['wttr','completion','p'], 'powershell'), (['wttr',':trans'], ':translation')]:
            result=self.command(['__complete','bash',str(len(words)),'--','dots',*words])
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertIn('candidate\t'+expected+'\t',result.stdout)
            encoded=base64.b64encode(json.dumps(['__complete',*words]).encode()).decode()
            result=subprocess.run([sys.executable,'-B',str(ROOT/'lib/dots/native.py'),'cli',encoded],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertIn(expected,result.stdout)
        result=subprocess.run([sys.executable,'-B',str(ROOT/'tools/generate_wttr_commands.py'),'--check'],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertFalse(fixtures.core.cache_root().exists())

    def test_standalone_browse_completions(self):
        for shell in ('bash','fish','zsh'):
            executable=shutil.which(shell)
            if not executable: continue
            path=self.home/fixtures.completion.FILES[shell]
            path.write_text(fixtures.completion.generate(shell))
            if shell=='bash':
                command=[executable,'-c','source "$1"; COMP_WORDS=(wttr browse --); COMP_CWORD=2; _wttr; printf "%s\\n" "${COMPREPLY[@]}"','test',str(path)]
            elif shell=='fish':
                command=[executable,'--no-config','-c','source "$argv[1]"; complete -C "wttr browse --"',str(path)]
            else:
                command=[executable,'-f','-c','fpath=("${1:h}" $fpath); autoload -Uz compinit; compinit -D; autoload +X _wttr; _arguments() { print -r -- "$@"; }; words=(wttr browse --); _wttr','test',str(path)]
            result=subprocess.run(command,capture_output=True,text=True,timeout=10)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertIn('--query' if shell!='fish' else 'query',result.stdout)
            self.assertNotIn('--json',result.stdout)

    def test_cached_snapshot_is_inert_and_respects_stale_limit(self):
        session=self.session()
        with patch.object(Cache,'refresh',side_effect=AssertionError), patch.object(Cache,'schedule',side_effect=AssertionError), \
                patch.object(fixtures.core,'resolve_location',side_effect=AssertionError):
            self.assertIn('Unavailable',session.snapshot('current'))
            self.assertFalse(fixtures.core.cache_root().exists())
            self.seed(age=1000)
            before=self.cache.path.read_bytes()
            text=session.snapshot('hourly')
            self.assertIn('Stale (~)',text);self.assertIn('12:00',text)
            self.assertEqual(self.cache.path.read_bytes(),before)
            self.seed(age=self.cfg['max_stale']+1)
            text=session.snapshot('current')
            self.assertIn('Unavailable',text);self.assertNotIn('72°F',text)

    def test_preview_transport_and_geometry_keep_data_literal(self):
        row=self.seed();row['location']='日本 café $(touch nope)\x1b[31m' * 3
        fixtures.core.atomic(self.cache.path,row)
        for width,height in ((40,12),(80,24),(120,30)):
            session=self.session(); frame=dict(query='forecast',focus=2)
            def select(*args,**kwargs):
                data=read_request(Path(args[3][2]['DOTS_WTTR_PREVIEW']))
                for text in data['previews']:
                    self.assertNotIn('\x1b[31m',text)
                self.assertEqual(kwargs['focus_index'],2)
                self.assertLessEqual(kwargs['height'],height-2)
                self.assertGreaterEqual(kwargs['preview_lines'],1)
                kwargs['navigation']['query']='current'
                return [0]
            with patch.object(browser.shutil,'get_terminal_size',return_value=os.terminal_size((width,height))), \
                    patch.object(browser.RichSelector,'fzf',side_effect=select), \
                    patch.object(Cache,'refresh',side_effect=AssertionError):
                self.assertEqual(browser.pick(session,frame,None),'current')
            self.assertEqual(frame,dict(query='current',focus=0))
        with request_file(dict(schema=1,previews=['literal $(nope)'])) as path:
            for token in ('-1','99','0;touch nope'):
                with self.assertRaises(ValueError): browser.preview(path,token)
            output=io.StringIO()
            with redirect_stdout(output): browser.preview(path,'0')
            self.assertEqual(output.getvalue(),'literal $(nope)')

    def test_preview_and_help_presentation_preferences_and_widths(self):
        from resources import cells
        self.seed()
        for width in (40,80,120):
            for colors in (dict(background='#111111',foreground='#eeeeee',green='#12ab34'),
                           dict(background='#eeeeee',foreground='#111111',green='#3456ab')):
                self.palette(colors)
                for mode,no_color,enabled in (('auto','',True),('auto','1',False),('always','1',True),('never','',False)):
                    with patch.dict(os.environ,COLUMNS=str(width),DOTS_COLOR=mode,NO_COLOR=no_color,DOTS_ICONS='never'):
                        text=self.session().snapshot('hourly',width=width)
                        self.assertEqual('\x1b[' in text,enabled)
                        plain=re.sub(r'\x1b\[[0-9;]*m','',text)
                        self.assertTrue(all(cells(line)<=width for line in plain.splitlines()),plain)
                        with redirect_stdout(io.StringIO()) as out: browser.help_view()
                        plain=re.sub(r'\x1b\[[0-9;]*m','',out.getvalue())
                        self.assertTrue(all(cells(line)<=width for line in plain.splitlines()),plain)

    def test_reports_refresh_once_and_keep_stale_on_failure(self):
        self.seed(age=1000)
        for force in (False,True):
            out,err=io.StringIO(),io.StringIO()
            with patch.object(Cache,'refresh',side_effect=Unavailable('fixture service failed')) as refresh, \
                    redirect_stdout(out),redirect_stderr(err):
                self.assertEqual(fixtures.cli.main(['--_browse-report','--allow-stale',*(['--refresh'] if force else [])]),0)
            self.assertEqual(refresh.call_count,1)
            self.assertIn('Stale (~)',out.getvalue())
        self.seed(age=self.cfg['max_stale']+1)
        with patch.object(Cache,'refresh',side_effect=Unavailable('fixture failed')), self.assertRaises(Unavailable):
            fixtures.cli.main(['--_browse-report','--allow-stale'])
        self.seed()
        with patch.object(Cache,'refresh',side_effect=AssertionError), redirect_stdout(io.StringIO()):
            self.assertEqual(fixtures.cli.main(['--_browse-report','--allow-stale']),0)

    def test_real_failed_report_exposes_error_age_and_retains_cache(self):
        self.seed(age=1000)
        script=self.home/'report.py'
        script.write_text('import sys\nsys.path.insert(0,'+repr(str(ROOT/'lib/dots/wttr'))+')\n'
                          'import core\nfrom wttr import cli\ndef fail(*a,**k): raise core.Unavailable("fixture offline")\n'
                          'core.resolve_location=fail\nraise SystemExit(cli.main(["--_browse-report","--allow-stale","--refresh"]))\n')
        result=subprocess.run([sys.executable,'-B',str(script)],capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('Stale (~)',result.stdout);self.assertIn('fixture offline',result.stderr)
        self.assertEqual(self.cache.read()['data'],self.data)

    def test_controls_persist_only_in_session_and_reports_use_literal_argv(self):
        session=self.session(); before=self.path.read_bytes(); actions=iter(('location','units','hourly','refresh','back'))
        literal='-city café "quoted" $(touch nope);'
        with patch.object(browser,'pick',side_effect=lambda *a:next(actions)), \
                patch.object(browser,'select',side_effect=('custom','metric')), patch.object(browser,'prompt',return_value=literal), \
                patch.object(browser,'run_action',return_value=1) as run:
            self.assertEqual(browser.browse(session,SimpleNamespace(query=''),None),0)
        self.assertEqual((session.location,session.cfg['units']),(literal,'metric'))
        self.assertEqual(run.call_count,2)
        command=run.call_args_list[0].args[0]
        self.assertIn('--location='+literal,command)
        self.assertIn('--hourly',command)
        self.assertIn('--refresh',run.call_args.args[0])
        self.assertEqual(run.call_args.kwargs['kind'],'output')
        self.assertEqual(self.path.read_bytes(),before)
        self.assertFalse(fixtures.core.cache_root().exists())

    def test_cancelled_input_and_default_location_reset(self):
        for selection,expected in (('custom','Original'),('default',None)):
            session=self.session('Original')
            with patch.object(browser,'pick',side_effect=('location','back')), \
                    patch.object(browser,'select',return_value=selection), \
                    patch.object(browser,'prompt',side_effect=SelectionEvent('back')):
                self.assertEqual(browser.browse(session,SimpleNamespace(query=''),None),0)
            self.assertEqual(session.location,expected)
        with patch.object(browser,'terminal',return_value=True), patch.object(browser,'available',return_value=True), \
                patch.object(browser,'pick',side_effect=SelectionEnded(130)):
            self.assertEqual(browser.main([]),130)
        with patch.object(browser,'pick',return_value='current'), patch.object(browser,'run_action',return_value=130) as run:
            self.assertEqual(browser.browse(self.session(),SimpleNamespace(query=''),None),130)
            run.assert_called_once()

    def test_submenu_help_returns_to_the_same_choice(self):
        with patch.object(browser,'choose',side_effect=(SelectionEvent('help'),browser.Entry('metric','Metric'))) as choose, \
                patch.object(browser,'show_message') as show:
            self.assertEqual(browser.select('Units',[('metric','Metric')],None),'metric')
        self.assertEqual(choose.call_count,2);show.assert_called_once()

    def test_fallback_is_ordinary_report_with_no_tmux_probe(self):
        self.seed()
        with patch.dict(os.environ,TMUX='/not-a-server,1,1'), patch.object(browser,'terminal',return_value=False), \
                patch.object(browser.TmuxContext,'capture',side_effect=AssertionError), \
                patch.object(browser,'available',side_effect=AssertionError), \
                redirect_stdout(io.StringIO()) as out,redirect_stderr(io.StringIO()) as err:
            self.assertEqual(browser.main([]),0)
        self.assertIn('72°F',out.getvalue());self.assertIn('ordinary weather report',err.getvalue())
        with patch.object(browser,'terminal',return_value=True), patch.object(browser,'available',return_value=False), \
                redirect_stdout(io.StringIO()) as out,redirect_stderr(io.StringIO()):
            self.assertEqual(browser.main([]),0)
        self.assertIn('72°F',out.getvalue())

    def test_inherited_context_is_consumed_and_stale_context_refused(self):
        context=unittest.mock.Mock()
        with patch.dict(os.environ,DOTS_MENU_CONTEXT='/private/request'), patch.object(browser,'terminal',return_value=False), \
                patch.object(browser.TmuxContext,'from_environment',return_value=context) as capture, \
                patch.object(browser,'available',return_value=True),patch.object(browser,'browse',return_value=0) as browse:
            self.assertEqual(browser.main([]),0)
            capture.assert_called_once_with();self.assertIs(browse.call_args.args[2],context)
        with patch.dict(os.environ,DOTS_MENU_CONTEXT='/private/request'), \
                patch.object(browser.TmuxContext,'from_environment',side_effect=ValueError('stale context')), \
                patch.object(browser.weather_cli,'main',side_effect=AssertionError):
            with self.assertRaisesRegex(ValueError,'stale context'): browser.main([])


class NativeWeatherBrowser(NativeMenuFixture):
    @unittest.skipUnless(shutil.which('less'), 'native less reader unavailable')
    def test_report_reader_returns_to_query_and_units_apply_without_refetch(self):
        config=self.home/'weather.toml';config.write_text('default_location="Fixture City"\n')
        code='''import os,sys,time
sys.path.insert(0,os.environ['WTTR_MODULES'])
import core
from wttr.browser import main
data={"current_condition":[{"weatherCode":"113","temp_F":"72","temp_C":"22","weatherDesc":[{"value":"Sunny"}]}],
      "weather":[{"date":"2026-10-30","astronomy":[{"sunrise":"6:00 AM","sunset":"6:00 PM"}]}]}
_,cfg=core.config(os.environ['WTTR_CONFIG'])
cache=core.Cache(cfg)
core.atomic(cache.path,dict(schema=2,updated=time.time(),data=data,location='Fixture City'))
raise SystemExit(main(['--config',os.environ['WTTR_CONFIG'],'--client',os.environ['CLIENT']]))
'''
        worker=self.worker(code,WTTR_CONFIG=str(config),WTTR_MODULES=str(ROOT/'lib/dots/wttr'))
        self.receive(self.first[1],b'wttr')
        os.write(self.first[1],b'Current');time.sleep(.2);os.write(self.first[1],b'\r')
        page=self.receive(self.first[1],b'Back q')
        self.assertIn(b'72',page)
        os.write(self.first[1],b'q')
        self.receive(self.first[1],b'wttr')
        os.write(self.first[1],b'\x15units');time.sleep(.2);os.write(self.first[1],b'\r')
        self.receive(self.first[1],b'Metric')
        os.write(self.first[1],b'Metric');time.sleep(.2);os.write(self.first[1],b'\r')
        self.receive(self.first[1],b'wttr')
        os.write(self.first[1],b'\x15Current');time.sleep(.2);os.write(self.first[1],b'\r')
        page=self.receive(self.first[1],b'Back q')
        self.assertIn(b'22',page)
        os.write(self.first[1],b'q')
        self.receive(self.first[1],b'wttr')
        os.write(self.first[1],b'\x03')
        out,err=worker.communicate(timeout=15)
        self.assertEqual((worker.returncode,out),(130,''),err)
        self.assertNotIn(b'Fixture City',self.drain(self.second[1]))
        self.assertEqual(config.read_text(),'default_location="Fixture City"\n')
        self.assertFalse(list(self.base.glob('dots-menu-*')))

    def test_private_two_client_browser_at_40_80_120_and_short_height(self):
        config=self.home/'weather.toml';config.write_text('default_location="Fixture City"\n')
        code='''import os,sys
from wttr.browser import main
raise SystemExit(main(['--config',os.environ['WTTR_CONFIG'],'--client',os.environ['CLIENT']]))
'''
        for width,height in ((40,12),(80,24),(120,30)):
            self.fcntl.ioctl(self.first[1],self.termios.TIOCSWINSZ,self.struct.pack('HHHH',height,width,0,0))
            from menu_tmux import TmuxContext
            context=TmuxContext.capture(client=self.first[2])
            for _ in range(30):
                if context.verify()==(width,height):break
                time.sleep(.05)
            self.assertEqual(context.verify(),(width,height))
            self.drain(self.first[1]);self.drain(self.second[1])
            worker=self.worker(code,WTTR_CONFIG=str(config))
            self.receive(self.first[1],b'wttr')
            self.assertNotIn(b'wttr',self.drain(self.second[1]))
            os.write(self.first[1],b'\x1b')
            out,err=worker.communicate(timeout=15)
            self.assertEqual((worker.returncode,out),(0,''),err)
            self.assertFalse((Path(self.env['XDG_CACHE_HOME'])/'wttr').exists())
        self.assertFalse(list(self.base.glob('dots-menu-*')))


if __name__=='__main__':
    unittest.main()
