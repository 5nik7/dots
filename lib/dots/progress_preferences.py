"""Inert progress glyph/style preferences shared by Config and renderers."""
import unicodedata

GLYPHS = dict(filled='━', empty='-', left='[', right=']')
ASCII = dict(filled='#', empty='-', left='[', right=']')
ROLES = ('filled', 'empty', 'surround', 'percentage')


def valid_symbol(name, value):
    if not isinstance(value, str): return False
    if value == '': return name in ('left', 'right')
    return (len(value) == 1 and value.isprintable() and not unicodedata.combining(value)
            and unicodedata.category(value)[0] not in ('C', 'M')
            and not (0x1160 <= ord(value) <= 0x11ff or 0xd7b0 <= ord(value) <= 0xd7ff)
            and unicodedata.east_asian_width(value) not in ('W', 'F'))


def fields(styles, role):
    baseline = (styles.style('ui.heading', {'fg': 'bright_cyan'}, app='cli')
                if role in ('filled', 'percentage') else {'fg': 'muted'})
    return styles.style('progress.'+role, baseline, app='cli')


class Appearance:
    def __init__(self, styles=None):
        self.symbols = dict(GLYPHS)
        self.colors = dict(filled='96', percentage='96', empty='90', surround='90')
        if styles is not None:
            for name in GLYPHS:
                value = styles.icon('progress.bar.'+name, GLYPHS[name], app='cli')
                if valid_symbol(name, value): self.symbols[name] = value
            self.colors = {role: styles.sgr_fields(fields(styles, role)) for role in ROLES}

    def glyphs(self, icons):
        return {name: value if icons or value.isascii() else ASCII[name]
                for name, value in self.symbols.items()}
