"""Shared help/header, literal parsing and fast offline presentation checks."""
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import ExitStack, redirect_stderr, redirect_stdout
from unittest.mock import patch

ROOT=Path(__file__).resolve().parent.parent
CORE=ROOT/'lib/blastoff.py'
spec=importlib.util.spec_from_file_location('help_core', CORE)
core=importlib.util.module_from_spec(spec); spec.loader.exec_module(core)
ui=core.ui_module('welcome')
ANSI=re.compile(r'\x1b\[[0-9;]*m')

class TTY(io.StringIO):
    @property
    def encoding(self): return 'utf-8'
    def isatty(self): return True

class Help(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory(prefix='blastoff-help-')
        self.addCleanup(tmp.cleanup)
        self.home=Path(tmp.name)
        self.env=dict(os.environ, HOME=str(self.home), USERPROFILE=str(self.home),
                      STARSHIP_CONFIG=str(self.home/'active.toml'),BLASTOFF_HOME=str(self.home/'store'),
                      PATH='',COLUMNS='80',TERM='xterm-256color')
        self.env.pop('NO_COLOR',None)

    def cli(self,*args,extra=None,code=0):
        result=subprocess.run([sys.executable,'-I',str(CORE),*args],env=dict(self.env,**(extra or {})),capture_output=True,timeout=8)
        self.assertEqual(result.returncode,code,result.stderr)
        return result.stdout.decode(), result.stderr.decode()

    def test_order_independent_color_and_json_help(self):
        for prefix in [[],['theme','apply'],['module','load']]:
            for flag in ['-h','--help']:
                a,_=self.cli('--color','always',*prefix,flag)
                b,_=self.cli(*prefix,flag,'--color','always')
                c,_=self.cli(*prefix,'--color=always',flag)
                self.assertEqual(a,b); self.assertEqual(b,c)
                self.assertIn('\x1b[95m',a)
                self.assertIn('\x1b[1;35m',a)
                for args,extra in [([*prefix,flag,'--color','never'],{}),
                                   ([*prefix,flag,'--color','always'],{'NO_COLOR':''}),
                                   ([*prefix,flag,'--color','always','--json'],{})]:
                    text,_=self.cli(*args,extra=extra)
                    self.assertNotIn('\x1b',text)
        self.assertNotIn('\x1b',self.cli('--color','always','-h','--color','never')[0])
        self.assertEqual(json.loads(self.cli('--json')[0])['name'],'blastoff')

    def test_grouped_complete_root_and_shared_header(self):
        bare,bare_error=self.cli()
        short,short_error=self.cli('-h')
        long,long_error=self.cli('--help')
        self.assertEqual(bare,short)
        self.assertEqual(short,long)
        self.assertEqual((bare_error,short_error,long_error),('','',''))
        self.assertNotIn('{list,current',short)
        for token in ['Browse & choose','Themes & modules','Backup & recovery',
                      '--version','--json','--color','--force','--replace-link',
                      '-l/--list','-t/--theme','bare -t/--theme']:
            self.assertIn(token,short)
        self.assertNotIn('\x1b',short)
        self.assertEqual(list(self.home.iterdir()),[])

    def test_global_flags_without_command_show_equivalent_help(self):
        for flags in (['--color','never'], ['--color=always'], ['-v'], ['--verbose'],
                      ['--dry-run'], ['--force'], ['--replace-link'],
                      ['--color','always','--color','never','--verbose','--dry-run']):
            with self.subTest(flags=flags):
                implicit=self.cli(*flags)
                self.assertEqual(implicit,self.cli(*flags,'--help'))
                self.assertEqual(implicit[1],'')
        plain=self.cli('--color','always',extra={'NO_COLOR':''})
        self.assertEqual(plain,self.cli('-h','--color','always',extra={'NO_COLOR':''}))
        self.assertNotIn('\x1b',plain[0])
        self.assertEqual(list(self.home.iterdir()),[])

    def test_no_command_json_and_explicit_json_help_keep_their_formats(self):
        expected=json.loads(self.cli('--json')[0])
        self.assertEqual(set(expected),{'name','version','description','examples'})
        for flags in ([], ['--color','always'], ['--verbose','--dry-run','--force','--replace-link']):
            out,err=self.cli(*flags,'--json')
            self.assertEqual(json.loads(out),expected)
            self.assertNotIn('\x1b',out)
            self.assertEqual(err,'')
        self.assertEqual(self.cli('--json','--help'),self.cli('--help'))

    def test_implicit_help_does_not_hide_usage_errors(self):
        for flags in (['--color'], ['--color','bogus'], ['--unknown'],
                      ['unknown'], ['--','--help']):
            with self.subTest(flags=flags):
                out,err=self.cli(*flags,code=2)
                self.assertEqual(out,'')
                self.assertTrue(err.startswith('blastoff: '))
        out,err=self.cli('--json','--color','bogus',code=2)
        self.assertEqual(out,'')
        self.assertEqual(json.loads(err)['code'],2)

    def test_direct_core_help_never_initializes_application_or_tools(self):
        expected=self.cli('--help')[0]
        sentinel=self.home/'active.toml'
        sentinel.write_text('invalid TOML sentinel')
        for flags in ([], ['-h'], ['--help'], ['--color','never','--verbose']):
            out,err=io.StringIO(),io.StringIO()
            with ExitStack() as stack:
                stack.enter_context(patch.dict(os.environ,self.env,clear=True))
                stack.enter_context(redirect_stdout(out))
                stack.enter_context(redirect_stderr(err))
                for target in ('App','read','path'):
                    stack.enter_context(patch.object(core,target,side_effect=AssertionError(target)))
                for target in ('subprocess.Popen','os.scandir','os.mkdir','shutil.which'):
                    stack.enter_context(patch(target,side_effect=AssertionError(target)))
                with self.assertRaises(SystemExit) as stopped:
                    core.run(flags)
            self.assertEqual(stopped.exception.code,0)
            self.assertEqual(out.getvalue(),expected)
            self.assertEqual(err.getvalue(),'')
        self.assertEqual(sentinel.read_text(),'invalid TOML sentinel')
        self.assertEqual(list(self.home.iterdir()),[sentinel])

    @unittest.skipUnless(shutil.which('bash'),'Bash required')
    def test_bash_frontend_has_identical_help(self):
        env=dict(self.env,BLASTOFF_PYTHON=sys.executable,
                 BLASTOFF_HOME='relative',STARSHIP_CONFIG='relative')
        for flags in ([], ['-h'], ['--help'], ['--color','never'], ['--dry-run']):
            result=subprocess.run([shutil.which('bash'),str(ROOT/'bin/blastoff'),*flags],
                                  env=env,capture_output=True,timeout=8)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(result.stderr,b'')
            self.assertEqual(result.stdout.decode(),self.cli('--help')[0])
        self.assertEqual(list(self.home.iterdir()),[])

    def test_all_parser_descriptions_and_actions_survive(self):
        def walk(parser):
            with patch.dict(os.environ,{'NO_COLOR':'1','COLUMNS':'80'}):
                text=' '.join(parser.format_help().split())
            if parser.description:
                self.assertIn(' '.join(parser.description.split()),text)
            if parser.epilog:
                self.assertIn(' '.join(parser.epilog.removeprefix('Aliases: ').split()),text)
            for action in parser._actions:
                for option in action.option_strings:
                    self.assertIn(option,text)
                if isinstance(action.choices,dict):
                    for name,child in action.choices.items():
                        self.assertIn(name,text)
                        walk(child)
        walk(core.parser())

    def test_actual_artwork_and_narrow_fallback(self):
        for width in (37, 40, 60, 96):
            with patch.dict(os.environ,{'COLUMNS':str(width),'TERM':'xterm','NO_COLOR':'1'}),redirect_stdout(TTY()):
                header='\n'.join(ui.header(core.VERSION))
                help_text=core.parser().format_help()
                out=TTY()
                with redirect_stdout(out): ui.render(core.VERSION)
            original=(ROOT/'lib/artwork/logo').read_text()
            self.assertEqual(len(original.splitlines()),13)
            self.assertEqual(max(map(len, original.splitlines())),37)
            for line in original.splitlines(): self.assertIn(line,header)
            self.assertTrue(help_text.startswith(header+'\n'))
            self.assertTrue(out.getvalue().startswith(header+'\n'))
        with patch.dict(os.environ,{'COLUMNS':'36'}),redirect_stdout(TTY()):
            text=ui.format_help(core.parser(),core.VERSION,'never')
        self.assertNotIn('⣴',text)
        self.assertTrue(all(len(line)<=36 for line in text.splitlines()))
        with patch.dict(os.environ,{'COLUMNS':'96'}), patch.object(TTY,'encoding',property(lambda _: 'ascii')), redirect_stdout(TTY()):
            self.assertNotIn('⣴','\n'.join(ui.header(core.VERSION,'never')))

    def test_logo_gradient_preserves_artwork_and_resets_each_line(self):
        logo=(ROOT/'lib/artwork/logo').read_text().splitlines()
        with patch.dict(os.environ,self.env,clear=True),redirect_stdout(TTY()):
            rows=ui.header(core.VERSION,'always',width=40)
        self.assertEqual([ANSI.sub('',row) for row in rows[:len(logo)]],logo)
        self.assertTrue(rows[0].startswith('\x1b[38;2;101;30;255m'))
        self.assertIn('\x1b[38;2;255;67;191m',rows[0])
        self.assertTrue(all(row.endswith('\x1b[0m') for row in rows[:len(logo)]))
        with patch.dict(os.environ,dict(self.env,NO_COLOR=''),clear=True),redirect_stdout(TTY()):
            plain=ui.header(core.VERSION,'always',width=40)
        self.assertEqual(plain[:len(logo)],logo)
        self.assertNotIn('\x1b','\n'.join(plain))

    def test_malformed_or_oversized_logo_falls_back(self):
        art=self.home/'artwork'; art.mkdir()
        invalid=[b'\xff', b'\x1b[2J', ('⣴'*97).encode(), ('⣴\n'*17).encode(),
                 ('⣴'*3000).encode(), '\u202e⣴'.encode(), b'$(touch unexpected)']
        with patch.dict(os.environ,dict(self.env,COLUMNS='96'),clear=True),redirect_stdout(TTY()), \
             patch.object(ui,'__file__',str(self.home/'welcome.py')):
            for data in invalid:
                (art/'logo').write_bytes(data)
                text='\n'.join(ui.header(core.VERSION,'never'))
                self.assertTrue(text.isascii())
                self.assertIn('BLASTOFF',text)
                self.assertNotIn('\x1b',text)
            if os.name == 'posix':
                (art/'logo').unlink()
                (art/'logo').symlink_to(ROOT/'lib/artwork/logo')
                self.assertTrue('\n'.join(ui.header(core.VERSION,'never')).isascii())

    def test_missing_or_unsafe_art_is_optional(self):
        with patch.dict(os.environ,{'COLUMNS':'96'}),redirect_stdout(TTY()):
            with patch.object(ui.os,'open',side_effect=OSError('missing')):
                self.assertIn('BLASTOFF','\n'.join(ui.header(core.VERSION,'never')))
            art=self.home/'artwork'; art.mkdir()
            for filename in ('logo',):
                (art/filename).write_bytes(b'\x1b[2Junsafe')
            with patch.object(ui,'__file__',str(self.home/'welcome.py')):
                text='\n'.join(ui.header(core.VERSION,'never'))
                self.assertNotIn('unsafe',text)
                self.assertNotIn('\x1b',text)
                if hasattr(os,'mkfifo'):
                    for file in art.iterdir():
                        file.unlink(); os.mkfifo(file)
                    self.assertIn('BLASTOFF','\n'.join(ui.header(core.VERSION,'never')))

    def test_literals_and_invalid_color_not_swallowed(self):
        _,err=self.cli('--help','--color','bogus',code=2)
        self.assertIn('invalid choice',err)
        self.cli('--help','--color',code=2)
        self.cli('theme','apply','--','--help',code=2)
        self.cli('theme','apply','--help',extra={'BLASTOFF_HOME':'relative','STARSHIP_CONFIG':'relative'})
        self.assertEqual(list(self.home.iterdir()),[])

    @unittest.skipUnless(os.name=='posix','POSIX PTY required')
    def test_real_tty_header_color_and_no_color(self):
        from pty_support import terminal
        env=dict(self.env); env.pop('COLUMNS')
        for width in (36,60):
            outputs=[]
            for args in [[],['-h'],['--help'],['--color','always']]:
                code,out=terminal([sys.executable,'-I',str(CORE),*args],env,columns=width,rows=30)
                self.assertEqual(code,0)
                outputs.append(out)
                if width == 60:
                    self.assertIn('⣴⣦⣄',ANSI.sub('',out.decode()))
                    self.assertIn(b'\x1b[38;2;',out)
            self.assertTrue(all(out==outputs[0] for out in outputs))
        code,out=terminal([sys.executable,'-I',str(CORE),'-h','--color','always'],dict(env,NO_COLOR=''),columns=40,rows=30)
        self.assertEqual(code,0)
        self.assertNotIn(b'\x1b[',out)

    def test_fast_help_has_no_application_imports(self):
        # Import tracing proves the script exits before core/discovery modules.
        for flags in ([], ['-h'], ['--help'], ['--color','never','--verbose','--dry-run']):
            result=subprocess.run([sys.executable,'-I','-X','importtime',str(CORE),*flags],
                                  env=dict(self.env,BLASTOFF_HOME='relative',STARSHIP_CONFIG='relative'),
                                  capture_output=True,timeout=8)
            self.assertEqual(result.returncode,0)
            for module in ['subprocess','tomllib','hashlib','uuid']:
                self.assertFalse(any(line.rstrip().endswith(' '+module) for line in result.stderr.decode().splitlines()),module)
        self.assertEqual(list(self.home.iterdir()),[])
