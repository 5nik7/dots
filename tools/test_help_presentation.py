#!/usr/bin/env python3
"""Semantic help consumers in owned roots; examples are never executed."""
import argparse
import io
import os
import re
import shutil
import unittest
from unittest.mock import patch

import test_profile_config as fixtures
from help_presentation import HelpStyles, HelpPresentation, colorize_help, syntax_spans

ANSI = re.compile(r'\x1b\[[0-9;]*m')


class Syntax(unittest.TestCase):
    def test_synopsis_and_literal_arguments(self):
        text = 'dots [OPTIONS] COMMAND [ARGS...]'
        spans = syntax_spans(text)
        self.assertEqual(''.join(s for s, _ in spans), text)
        for token, role in [('dots','executable'), ('OPTIONS','option'), ('COMMAND','command'), ('ARGS','argument'), ('...','punctuation')]:
            self.assertIn((token, role), spans)
        text = 'dots todo show --project="a space ü" -- --help $(touch NO)'
        spans = syntax_spans(text, route=('todo','show'))
        self.assertEqual(''.join(s for s, _ in spans), text)
        for token, role in [('todo','command'), ('show','subcommand'), ('--project','option'), ('"a space ü"','argument'), ('--help','argument')]:
            self.assertIn((token, role), spans)

    def test_prefix_options_and_ambiguous_value(self):
        text = 'dots --json --profile=list todo list list'
        spans = syntax_spans(text, route=('todo','list'), commands=('todo list',),
                             options={'--json': False, '--profile': True})
        self.assertEqual([role for token,role in spans if token=='list'], ['argument','subcommand','argument'])
        self.assertIn(('todo','command'), spans)

    def test_description_only_explicit_references(self):
        text = 'Use dots help COMMAND for details; dots commands for all commands. The help is useful.'
        spans = syntax_spans(text, kind='description')
        self.assertEqual(''.join(s for s, _ in spans), text)
        self.assertIn(('help','command'), spans)
        self.assertIn(('commands','command'), spans)
        self.assertTrue(any('The help is useful.' in s and role=='description' for s,role in spans))
        self.assertIn(('options','option'), syntax_spans('tool [options] [args...]',prog='tool'))

    def test_command_alternatives_and_nested_parser_rows(self):
        routes=(('todo','list'),('todo','show'))
        spans=syntax_spans('dots todo {list,show}',prog='dots todo',commands=routes)
        self.assertIn(('list','subcommand'),spans)
        self.assertIn(('show','subcommand'),spans)
        self.assertIn(('list','subcommand'),syntax_spans('list',prog='dots todo',commands=routes,kind='command'))
        self.assertIn(('list','subcommand'),syntax_spans('list',prog='dots todo',commands=('list','show'),kind='subcommand'))
        spans=syntax_spans('dots --format {list,show} todo list',commands=routes,options={'--format':True})
        self.assertEqual([r for t,r in spans if t=='show'],['argument'])
        spans=syntax_spans('dots theme sample [FLAVOR] [show|set|init|COLOR [FORMAT]]',
                           prog='dots theme sample',commands=('show','set','init'))
        for token in ('show','set','init'):
            self.assertIn((token,'subcommand'),spans)
        self.assertIn(('FLAVOR','argument'),spans)

    def test_repeated_standalone_and_dots_invocations(self):
        text='wttr browse [LOCATION] [options] | dots wttr browse; wttr get FIELD'
        spans=syntax_spans(text,prog='wttr',commands=('browse','get'))
        self.assertEqual(''.join(t for t,_ in spans),text)
        self.assertEqual([r for t,r in spans if t=='wttr'],['executable','command','executable'])
        self.assertIn(('dots','executable'),spans)
        self.assertEqual([r for t,r in spans if t=='browse'],['command','subcommand'])
        self.assertIn(('get','command'),spans)
        self.assertIn(('FIELD','argument'),spans)


class Consumers(unittest.TestCase):
    def setUp(self):
        fixtures.ProfileConfig.setUp(self)
        shutil.copytree(fixtures.ROOT/'default', self.root/'default')
        self.env['TERM']='xterm-256color'
        environ=patch.dict(os.environ,self.env,clear=True);environ.start();self.addCleanup(environ.stop)
        from config_values import current as controls
        from style_config import current as styles
        for current in (controls,styles):
            current.cache_clear();self.addCleanup(current.cache_clear)

    def test_exact_role_styles_and_tagline_fallback(self):
        palette={'cyan':'#123456','blue':'#234567','magenta':'#345678','yellow':'#456789','green':'#56789a','foreground':'#eeeeee'}
        styles=HelpStyles(self.root,palette=palette)
        self.assertEqual(styles.tagline,'Manage your dotfiles and more...')
        self.assertIn('38;2;238;238;238',styles.code('tagline'))
        for role,color in [('executable','cyan'),('command','blue'),('subcommand','magenta'),('option','yellow'),('argument','green')]:
            expected='38;2;'+';'.join(str(int(palette[color][i:i+2],16)) for i in (1,3,5))
            self.assertIn(expected,styles.code(role))
        self.assertIn('38;2;1;2;3',HelpStyles(self.root,palette=dict(palette,accent='#010203')).code('tagline'))
        (self.path.parent/'colors.toml').write_text('[apps.cli.help.tagline]\nfg="colors.ui.accent.fg"\n')
        self.assertIn('38;2;238;238;238',HelpStyles(self.root,palette=palette).code('tagline'))

    def test_parser_layout_plain_bytes_and_destination_color(self):
        from help_adapters import HelpArgumentParser
        parser=HelpArgumentParser(prog='dots todo',description='Use dots help COMMAND for details.')
        parser.add_argument('--project');sub=parser.add_subparsers(dest='action')
        sub.add_parser('list');sub.add_parser('show')
        plain=parser.format_help()
        self.assertNotIn('\x1b',plain)
        colored=colorize_help(plain,parser=parser,color=True)
        self.assertEqual(ANSI.sub('',colored),plain)
        self.assertEqual(colorize_help(plain,parser=parser,color=False),plain)
        self.assertIn('\x1b[0;34mtodo\x1b[0m',colored)
        self.assertIn('\x1b[0;35mlist\x1b[0m',colored)
        self.assertIn('\x1b[0;35mshow\x1b[0m',colored)
        wrapped='usage: dots todo [-h]\n                 {list,show}\n'
        decorated=colorize_help(wrapped,parser=parser,color=True)
        self.assertEqual(ANSI.sub('',decorated),wrapped)
        self.assertIn('\x1b[0;35mshow\x1b[0m',decorated)
        class Terminal(io.StringIO):
            def isatty(self):return True
        with patch.dict(os.environ,DOTS_COLOR='auto'):
            ordinary=io.StringIO();terminal=Terminal()
            parser.print_usage(ordinary);parser.print_usage(terminal)
            self.assertNotIn('\x1b',ordinary.getvalue())
            self.assertIn('\x1b',terminal.getvalue())
        with patch.dict(os.environ,DOTS_COLOR='auto',NO_COLOR='1'):
            terminal=Terminal();parser.print_help(terminal);self.assertNotIn('\x1b',terminal.getvalue())

    def test_bootstrap_help_without_profile_definitions(self):
        shutil.rmtree(self.root/'profiles')
        from help_adapters import HelpArgumentParser
        for mode in ('never','always'):
            with patch.dict(os.environ,DOTS_PROFILE=self.platform,DOTS_COLOR=mode):
                output=io.StringIO()
                parser=HelpArgumentParser(prog='tool');parser.add_argument('--value')
                parser.print_help(output)
                self.assertIn('tool',output.getvalue())
                self.assertEqual(HelpStyles().tagline,'Manage your dotfiles and more...')

    def test_span_wrapping_and_explicit_style_is_not_status_color(self):
        (self.path.parent/'colors.toml').write_text('[apps.cli.status.success]\nfg="#ff0000"\n[apps.cli.help.argument]\nfg="#010203"\n')
        from resources import cells
        for width in (40,80,120):
            stream=io.StringIO()
            with patch.dict(os.environ,DOTS_COLOR='always',COLUMNS=str(width)):
                view=HelpPresentation(stream,root=self.root,terminal=True)
                view.help_row('show [OPTIONS] NAME','Read a literal Unicode path ü and keep its complete value.',
                              kind='command',prog='todo',label_width=24)
                view.help_text('todo show --project "a space ü"',kind='syntax',prog='todo',route=('show',))
            text=stream.getvalue()
            self.assertIn('\x1b[0;38;2;1;2;3mNAME',text)
            self.assertNotIn('\x1b[0;38;2;255;0;0m',text)
            for line in ANSI.sub('',text).splitlines():self.assertLessEqual(cells(line),width)
            self.assertTrue(all(not line.strip() or line.rstrip().endswith('\x1b[0m') for line in text.splitlines()))


if __name__=='__main__':unittest.main()
