"""Display-cell column sizing shared by human reports and popup rows."""
import re

from resources import cells


def valid_width(value):
    return (type(value) is int and 0 <= value <= 4096 or isinstance(value,str)
            and re.fullmatch(r'(?:[1-9][0-9]?|100)%', value) is not None)


def width(value, columns, *, indent=0, gap=1):
    requested = columns * int(value[:-1]) // 100 if isinstance(value,str) else value
    return min(max(0, requested), max(0, columns-indent-gap-8))


def pad(text, columns, alignment='left'):
    padding = max(0, columns-cells(text))
    left = padding if alignment=='right' else padding//2 if alignment=='center' else 0
    return ' '*left + text + ' '*(padding-left)
