"""Root usage artwork with the classic or installer gradient; read-only."""
import os
from pathlib import Path
import sys


def lines(root, *, colored=False, artwork=None):
    if artwork is None:
        path = Path(root)/'logo.txt'
        if not path.is_file() or path.stat().st_size > 2*1024*1024:
            return []
        artwork = path.read_text(encoding='utf-8').splitlines()
    if not colored:
        return artwork
    from config_values import Controls
    mode = Controls(root).values.get('apps',{}).get('cli',{}).get('logo_gradient','classic')
    if mode == 'installer':
        from style_config import Styles
        from text_gradient import gradient
        return gradient(artwork, Styles(root).palette, horizontal=True, restore='\x1b[0m')
    steps = max(1,len(artwork)-1)
    return ['\x1b[38;2;0;%d;255m%s\x1b[0m' % (96+159*i//steps,line)
            for i,line in enumerate(artwork)]


def render(ui, root):
    artwork = lines(root, colored=ui.color)
    for line in artwork:ui.emit(line)
    if artwork:ui.emit()


def main():
    from files.catalog import Presentation
    root = Path(os.environ.get('DOTS') or Path(__file__).resolve().parents[2])
    if '--color=always' in sys.argv[1:]:os.environ['DOTS_COLOR']='always'
    ui = Presentation()
    # The shell adapters own their surrounding whitespace.
    artwork = None
    if '--stdin' in sys.argv[1:]:
        data = sys.stdin.read(2*1024*1024+1)
        if len(data)>2*1024*1024:return 1
        artwork = data.splitlines()
    for line in lines(root,colored=ui.color,artwork=artwork):ui.emit(line)
    return 0


if __name__ == '__main__':
    try:sys.exit(main())
    except (OSError,ValueError,KeyError,TypeError):sys.exit(1)
