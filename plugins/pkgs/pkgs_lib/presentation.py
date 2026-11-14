"""Package-specific consumers of Dots styles; native/data output stays separate."""
from functools import lru_cache
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'lib/dots'))
from files.catalog import Presentation
from plugin_presentation import report as shared_report
import style_config
from style_config import ROLES, ANSI, ATTRS
from .grammar import MANAGERS

# Keep each surface's established fallback, including the separate preview colors.
FALLBACKS = dict(heading='1;96', label='94', identity='94', count='96', value='0',
                 package='accent', manager='magenta', version='0', muted='2', skipped='90', success='92',
                 warning='93', error='91', progress='94', spinner='96',
                 **{'preview.heading':'1;36','preview.label':'36','preview.success':'32',
                    'preview.warning':'33','preview.version':'2'})


@lru_cache(maxsize=16)
def resolved(prefs):
    result = {}
    for role, code in FALLBACKS.items():
        if code in ('accent', 'magenta'): fields = {'fg':code}
        else:
            parts=code.split(';')
            fields={k:True for k,v in ATTRS.items() if str(v) in parts}
            fields.update(fg=next((k for k,v in ANSI.items() if str(v) in parts),'default'))
            semantic=next((ROLES[p] for p in parts if p in ROLES),None)
            if prefs and semantic and not role.startswith('preview.') and role not in ('progress','spinner'):
                fields=prefs.style(semantic,fields,app='cli')
        value = prefs.sgr('pkgs.'+role, fields, app='cli') if prefs else {'accent':'34', 'magenta':'35'}.get(code, code)
        # A resolved style is literal, not another legacy semantic ANSI token.
        result[role] = '0;'+value
    return result


def styles(): return resolved(style_config.current())


# Alternate executable labels can appear in owned diagnostic/progress fixtures.
# This is presentation vocabulary, not extra accepted --manager values.
MANAGER_LABELS = frozenset(MANAGERS) | {'uv', 'pip3', 'apt-get', 'apt-cache',
                                      'pkg', 'dnf5', 'xbps-install', 'xbps-query', 'winget.exe'}


def activity_spans(label, colors):
    """Split the manager position in our own activity labels, never native logs."""
    first, separator, rest = label.partition(' · ')
    if first in MANAGER_LABELS:
        return [(first, colors['manager'])] + ([(separator+rest, colors['progress'])] if separator else [])
    before, separator, last = label.rpartition(' · ')
    if separator and last in MANAGER_LABELS:
        return [(before+separator, colors['progress']), (last, colors['manager'])]
    if label.startswith('Exporting ') and label[10:] in MANAGER_LABELS:
        return [('Exporting ', colors['progress']), (label[10:], colors['manager'])]
    return [(label, colors['progress'])]


def progress(label, colors):
    """Keep sequence updates styled without putting escapes into activity data."""
    from progress import Progress

    class PackageProgress(Progress):
        def update(self, label, completed=0, total=0):
            self.update_spans(activity_spans(str(label), colors), completed, total)

    return PackageProgress(label, marker_style=colors['spinner'], label_style=colors['progress'])


class PackagePresentation(Presentation):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.package_styles=styles()

    def heading(self, title): self.heading_spans([(title,self.package_styles['heading'])])

    def detail_spans(self, label, spans, **kwargs):
        kwargs.setdefault('label_code',self.package_styles['label'])
        return super().detail_spans(label,spans,**kwargs)

    def resource_detail(self, *args, **kwargs):
        kwargs.setdefault('label_code',self.package_styles['label'])
        return super().resource_detail(*args,**kwargs)

    def _spans(self, spans, *args, **kwargs):
        return super()._spans([(text,self.package_styles['value'] if code is None else code)
                              for text,code in spans], *args, **kwargs)


def report(*args, **kwargs):
    # Shared gate stays lazy for raw/data/ordinary redirects.
    from plugin_presentation import color_mode
    import os
    stream=kwargs.get('stream') or sys.stdout
    mode=color_mode(kwargs.get('explicit',args[0] if args else None),kwargs.get('fallback','auto'))
    human=stream.isatty() or os.environ.get('DOTS_MENU_CAPTURE')=='1' or mode=='always' or os.environ.get('DOTS_ICONS')=='always'
    if kwargs.get('data') or not human: return None
    return shared_report(*args,**kwargs,presentation=PackagePresentation,styles=styles())


def message(text, role='value', stream=None):
    from progress import permanent_output
    stream=stream or sys.stdout
    with permanent_output():
        ui=report(stream=stream)
        if ui: print(ui.ui.paint(text,ui.styles[role]),file=stream,flush=True)
        else: print(text,file=stream,flush=True)
