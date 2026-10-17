"""Test-owned Vivid adapter with the legacy scalar font-style contract."""
import sys


def install_vivid(directory, version='0.9.0', *, modern=False, native=None):
    path = directory / 'vivid'
    path.write_text('#!' + sys.executable + '\n' + f'''
import json, os, sys
from pathlib import Path
if sys.argv[1:] == ['--version']:
    print('vivid ' + {version!r})
    raise SystemExit(0)
assert sys.argv[1] == 'generate'
try:
    doc = json.loads(Path(sys.argv[2]).read_text())
    def check(node):
        if not isinstance(node, dict):
            return
        for key, value in node.items():
            if key == 'font-style':
                assert isinstance(value, str) or ({modern!r} and isinstance(value, list)), 'Color value should be a string'
            else:
                check(value)
    check(doc)
except (ValueError, AssertionError) as error:
    print(str(error), file=sys.stderr)
    raise SystemExit(1)
if {native!r}:
    os.execv({native!r}, [{native!r}, *sys.argv[1:]])
style = doc['archives']
attrs = style.get('font-style', 'regular')
if isinstance(attrs, str):
    attrs = [attrs]
codes = {{'regular':'0', 'bold':'1', 'faint':'2', 'italic':'3', 'underline':'4', 'blink':'5', 'rapid-blink':'6'}}
print('*.zip=' + ';'.join(codes[attr] for attr in attrs))
''')
    path.chmod(0o700)
    return path
