"""Public parser adapters for shared help styles; ordinary output stays owned."""
import argparse
import os
import sys


def usage_message(message, *, prog='', commands=(), stream=None, color=None):
    """Style an authored usage error without changing other diagnostics."""
    if not message.lower().startswith('usage:'):
        return message
    from help_presentation import colorize_help
    return colorize_help(message, prog=prog, commands=commands,
                         stream=sys.stderr if stream is None else stream, color=color)


def __getattr__(name):
    if name != 'HelpView':
        raise AttributeError(name)
    from help_presentation import HelpPresentation

    class HelpView(HelpPresentation):
        """Keep specialized help layouts on the shared semantic span renderer."""

        def __init__(self, stream=None, *, prog='', commands=(), **kwargs):
            super().__init__(stream, **kwargs)
            self.prog = prog
            self.commands = tuple(commands)

        def heading(self, title):
            if self.prog and title == self.prog:
                return self.help_text(title, kind='syntax', prog=self.prog, commands=self.commands)
            return super().heading(title)

        def detail(self, label, value, code=None, *, value_kind=None):
            if not self.human:
                from files.catalog import Presentation
                return Presentation.detail(self, label, value, code)
            if code:
                # Explicit diagnostic colors keep their original meaning.
                return super().detail(label, value, code)
            text = ', '.join(map(str, value)) if isinstance(value, (list, tuple)) else str(value or '')
            kind = 'option' if label.startswith('-') else 'command' if label in self.commands else 'heading'
            if kind == 'command' and len(self.prog.split()) > 1:
                kind = 'subcommand'
            if value_kind is None:
                value_kind = 'syntax' if label in ('Usage', 'Queries', 'Examples', 'Stock', 'Pages', 'Activate') else 'description'
            return self.help_row(label, text, kind=kind, value_kind=value_kind,
                                 prog=self.prog, commands=self.commands)

        def text(self, text, kind='description', *, indent=0):
            return self.help_text(text, kind=kind, prog=self.prog, commands=self.commands, indent=indent)

    globals()['HelpView'] = HelpView
    return HelpView


class HelpArgumentParser(argparse.ArgumentParser):
    """Keep grammar formatting plain and decorate only the destination stream."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Python 3.14 has native argparse coloring. Dots owns these spans.
        self.color = False
        self._help_color = None

    def parse_known_args(self, args=None, namespace=None):
        words = list(sys.argv[1:] if args is None else args)
        before = words[:words.index('--')] if '--' in words else words
        for index, word in enumerate(before):
            mode = word.partition('=')[2] if word.startswith('--color=') else (
                before[index + 1] if word == '--color' and index + 1 < len(before) else None)
            if mode in ('auto', 'always', 'never'):
                self._help_color = mode
        return super().parse_known_args(words, namespace)

    def _help_colored(self, stream):
        mode = self._help_color or os.environ.get('DOTS_COLOR', 'auto')
        return mode == 'always' or (mode == 'auto' and stream.isatty()
                                    and os.environ.get('TERM', 'dumb') != 'dumb'
                                    and not os.environ.get('NO_COLOR'))

    def print_help(self, file=None):
        from help_presentation import colorize_help
        stream = sys.stdout if file is None else file
        self._print_message(colorize_help(self.format_help(), prog=self.prog, parser=self,
                                          color=self._help_colored(stream), stream=stream), stream)

    def print_usage(self, file=None):
        from help_presentation import colorize_help
        stream = sys.stdout if file is None else file
        self._print_message(colorize_help(self.format_usage(), prog=self.prog, parser=self,
                                          color=self._help_colored(stream), stream=stream), stream)
