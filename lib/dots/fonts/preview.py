#!/usr/bin/env python3
"""Private numeric preview reader; never evaluates selected display text."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from menu_tmux import read_request
from resources import clean
from fonts.model import sha


def render_sample(path,color=True):
    if not (shutil.which('magick') and shutil.which('chafa')):return 'Actual font sample unavailable (optional ImageMagick/Chafa missing).\n'
    result=subprocess.run(['magick','-limit','memory','64MiB','-limit','map','64MiB','-size','720x150',
        'xc:none','-font',str(path),'-pointsize','28','-fill','white','-gravity','center',
        '-annotate','0','Aa Bb 0123456789\nThe quick brown fox\n!= -> {} [] ()','png:-'],capture_output=True,timeout=8)
    if result.returncode or len(result.stdout)>4*1024*1024:return 'Actual font rendering unavailable.\n'
    width=max(8,min(65,int(os.environ.get('FZF_PREVIEW_COLUMNS','65'))))
    image=subprocess.run(['chafa','--probe=off','--format=symbols','--size='+str(width)+'x10','--colors=none','-'],
                         input=result.stdout,capture_output=True,timeout=8)
    if image.returncode:return 'Actual font rendering unavailable.\n'
    sample=image.stdout.decode('utf-8',errors='replace')
    if color:
        from fonts.presentation import FontPresentation
        sample='\033['+FontPresentation().style('face','ui.foreground')+'m'+sample+'\033[0m'
    return sample


def main():
    data=read_request(sys.argv[1]);index=int(sys.argv[2])
    if not 0<=index<len(data['previews']):raise ValueError('invalid font preview index')
    item=data['previews'][index]
    if 'report' in item:
        from fonts_cli import render
        os.environ['DOTS_COLOR']='always' if data.get('color') else 'never'
        os.environ['DOTS_ICONS']='always' if data.get('icons') else 'never'
        render(item['report'],human=True,width=int(os.environ.get('FZF_PREVIEW_COLUMNS','80')),action='show',wrap=data.get('wrap',True))
    else:print(item['text'],end='')
    if not data.get('sample',True):return
    from fonts.presentation import FontPresentation
    ui=FontPresentation(terminal=True)
    ui.width=max(1,int(os.environ.get('FZF_PREVIEW_COLUMNS','80')))
    if item.get('font'):
        path=Path(item['font'])
        if path.is_file() and not path.is_symlink() and sha(path)==item['sha256']:
            ui.emit();ui.detail('Sample','Rendered from the selected font')
            print(render_sample(path,data.get('color',False)),end='')
    elif item.get('kind')!='glyph':ui.detail('Sample','Metadata preview; download the font to render its actual sample.')


if __name__=='__main__':
    try:main()
    except (ValueError,KeyError,IndexError,OSError,subprocess.SubprocessError):
        print('Font preview unavailable.',file=sys.stderr);sys.exit(1)
