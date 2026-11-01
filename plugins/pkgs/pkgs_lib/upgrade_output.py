"""Compact human package transactions; subprocess status remains authoritative."""
from collections import deque
from contextlib import nullcontext
import re
import sys
import time
from urllib.parse import unquote, urlsplit

from . import streams


PROMPT = re.compile(r'(?:(?:password|passphrase)(?: for [^\r\n]*)?\s*:\s*$|\[[yn]/[yn]\]|\[default=[^\]]+\]\s*\?\s*$|'
                    r'(?:continue|proceed|confirm|choice|enter|choose|press).*[:?]\s*$)', re.I)
ROUTINE = re.compile(r'^(?:\(?Reading |Building dependency|Calculating |Get:|Hit:|Ign:|Fetched |'
                     r'Collecting |Downloading |Using cached |Requirement already |'
                     r'Resolved |Prepared |Installed |Nothing to upgrade|\s*\d+%)')
ERROR = re.compile(r'^(?:npm (?:error|ERR!)\s*|E:\s*|dpkg(?:-deb)?:\s*(?:fatal )?error\b[: ]*|(?:error|fatal|failed)\b[: ]*)', re.I)
WARNING = re.compile(r'^(?:npm (?:warn|WARN)\s*|W:\s*|warning\b[: ]*|warn\b[: ]*)', re.I)
STAGES = {'install': 'Installing', 'upgrade': 'Upgrading', 'uninstall': 'Removing'}


def enabled(args, cfg):
    return not args.dry_run and not getattr(args, 'json', False) and streams.styled(cfg, sys.stdout)


def renderer(cfg, stream):
    from .reports import report
    return report(explicit=cfg.get('_explicit_color'), fallback=cfg.get('color', 'auto'), stream=stream)


def heading(cfg, backend=None, *, action='upgrade'):
    title = action.capitalize()+' packages'
    ui = renderer(cfg, sys.stdout)
    if ui:
        ui.heading(title)
        if backend is not None: ui.field('Scope', backend.scope)
    else:
        print(title)
        if backend is not None: print('  Scope: '+backend.scope)
    sys.stdout.flush()


def packages(cfg, label, names):
    """Show selected identities once, without inventory queries or log parsing."""
    value = ', '.join(dict.fromkeys(names))
    if not value: return
    ui = renderer(cfg, sys.stdout)
    if ui: ui.field(label, value, 'identity')
    else: print('  '+label+': '+value)
    sys.stdout.flush()


class Output:
    """Keep bounded diagnostics and a failure tail, without storing full logs."""
    def __init__(self, manager, cfg, progress=None, *, action='upgrade'):
        self.manager, self.cfg, self.progress = manager, cfg, progress
        self.action = action
        self.default_stage = STAGES[action]
        self.errors, self.warnings = [], []
        self.tail = deque(maxlen=3)
        self.extra = 0
        self.pause = None
        self.mirror_sync = False
        self.updated = None
        self.stage, self.package = self.default_stage, ''
        self.transferred, self.total = 0, 0
        self.last_activity = time.monotonic()
        self.partial_seen = ''

    def begin(self, command=None):
        self.stage, self.package = self.default_stage, ''
        self.transferred, self.total = 0, 0
        self.last_activity = time.monotonic()
        self.partial_seen = ''
        if self.manager == 'go' and command and command[:2] == ['go', 'install']:
            target = command[-1].partition('@')[0]
            if re.fullmatch(r'[A-Za-z0-9_.~+/-]+', target):
                self.package = re.sub(r'/v[2-9][0-9]*$', '', target).rsplit('/', 1)[-1]
                self.stage = 'Installing'
        if (self.manager == 'winget' and command and
                re.split(r'[/\\]', command[0])[-1].lower() in ('winget', 'winget.exe') and '--id' in command):
            index = command.index('--id')+1
            if index < len(command) and re.fullmatch(r'[A-Za-z0-9_.+-]+', command[index]):
                self.package = command[index]
        self.tick()

    def pip_stage(self, text):
        """Use native events; never infer bytes or assume a silent build is hung."""
        if self.manager != 'pip': return False
        transferred = re.fullmatch(r'Progress ([0-9]{1,20}) of ([0-9]{1,20})', text)
        if transferred:
            self.stage = 'Downloading'
            self.transferred, self.total = map(int, transferred.groups())
            return True
        package = re.match(r'(?:Collecting|Requirement already satisfied:)\s+([A-Za-z0-9_.-]+)', text)
        if package:
            self.package = package[1]; self.stage = 'Resolving'
        elif text.startswith(('Downloading ', 'Resuming download ')):
            token = text.split()[1 if text.startswith('Downloading ') else 2]
            # Display the filename only, never URL credentials or query strings.
            try: name = urlsplit(token).path.rsplit('/', 1)[-1]
            except ValueError: return False
            if re.fullmatch(r'[A-Za-z0-9_.+-]+', name):
                self.package = re.split(r'-(?=\d)', name, maxsplit=1)[0]
            self.stage = 'Downloading'
        elif text.startswith('Installing build dependencies'): self.stage = 'Build dependencies'
        elif text.startswith(('Getting requirements to build', 'Preparing metadata')): self.stage = 'Preparing'
        elif text.startswith(('Building wheel', 'Running setup.py')):
            self.stage = 'Building'
            match = re.search(r'(?:Building wheel for|Running setup.py.*for)\s+([A-Za-z0-9_.-]+)', text)
            if match: self.package = match[1]
        elif text.startswith(('Installing collected packages', 'Successfully installed')): self.stage = 'Installing'; self.package = ''
        elif 'Retrying' in text: self.stage = 'Retrying'
        elif text.startswith('INFO: pip is '): self.stage = 'Resolving'
        else: return False
        self.transferred, self.total = 0, 0
        return True

    def partial(self, text):
        text = streams.ESCAPES.sub('', text).strip()
        if text and text != self.partial_seen and self.pip_stage(text):
            self.partial_seen = text
            self.last_activity = time.monotonic()
            self.tick()

    def npm_stage(self, text):
        """Summarize native events without displaying URLs or script commands."""
        if self.manager != 'npm': return False
        identity = r'(?:@[A-Za-z0-9_.~-]+/)?[A-Za-z0-9_.~-]+'
        script = re.match(r'npm (?:info|notice) run ('+identity+r')@\S+ (preinstall|install|postinstall|prepare)(?:\s|$)', text)
        if script:
            self.package = script[1]
            self.stage = 'Script '+script[2]
            if re.search(r'\{\s*code:\s*0,', text[script.end():]): self.stage = 'Script finished'
            return True
        if not text.startswith('npm http '): return False
        self.package = ''
        if re.search(r'\battempt \d+ failed\b', text): self.stage = 'Retrying'; return True
        match = re.search(r'https?://\S+', text)
        self.stage = 'Fetching'
        if not match: return True
        try: path = unquote(urlsplit(match[0]).path)
        except ValueError: return True
        if '/security/audits/' in path: self.stage = 'Auditing'; return True
        archive = '/-/' in path or path.endswith(('.tgz', '.tar.gz'))
        self.stage = 'Cached' if text.startswith('npm http cache ') else 'Fetched' if archive else 'Metadata'
        status = re.match(r'npm http fetch \S+ ([0-9]{3})\b', text)
        if status and int(status[1]) >= 400: self.stage = 'Fetch failed'
        parts = path.split('/-/')[0].strip('/').split('/')
        name = '/'.join(parts[-2:]) if len(parts)>1 and parts[-2].startswith('@') else parts[-1]
        if archive and '/-/' not in path:
            name = re.split(r'-(?=\d)', name, maxsplit=1)[0]
            name = re.sub(r'\.(?:tgz|tar\.gz)$', '', name)
        if re.fullmatch(identity, name): self.package = name
        return True

    def native_stage(self, text):
        """Identify packages only from known native transaction events."""
        match = None
        if self.manager == 'apt':
            verb = 'Removing' if self.action == 'uninstall' else '(?:Unpacking|Setting up)'
            match = re.match(verb+r' ([a-z0-9][a-z0-9+.:~-]*)\s+\(', text)
        elif self.manager in ('pacman', 'paru', 'yay'):
            verb = 'removing' if self.action == 'uninstall' else '(?:installing|upgrading)'
            match = re.match(r'\(\s*\d+/\d+\) '+verb+r' ([A-Za-z0-9@_+.-]+)(?:\.\.\.|\s|$)', text)
        elif self.manager == 'pip' and self.action == 'uninstall':
            match = re.match(r'Found existing installation: ([A-Za-z0-9_.-]+)\s', text)
        if not match: return False
        self.package = match[1].removesuffix('...')
        self.stage = 'Removing' if self.action == 'uninstall' else 'Installing'
        return True

    def tick(self, now=None):
        if self.progress is None or self.pause is not None: return
        now = time.monotonic() if now is None else now
        quiet = max(0, int(now-self.last_activity))
        label = self.manager+' · '
        if quiet >= 15 and self.manager in ('pip', 'npm', 'go'): label += f'quiet {quiet//60}:{quiet%60:02d} · '
        if self.stage == 'Downloading' and (self.total or self.transferred):
            def amount(size):
                return f'{size/1048576:.1f}MiB' if size >= 1048576 else f'{size/1024:.0f}KiB'
            if self.total:
                label += f'{min(100, 100*self.transferred//self.total)}% '+amount(self.transferred)+'/'+amount(self.total)
            else: label += 'Downloaded '+amount(self.transferred)
        else: label += self.stage
        if self.package: label += ' · '+self.package
        self.progress.update(label)

    def prompt(self, text, stream, ending=''):
        # Stop transient progress until the command finishes so it cannot obscure input.
        if self.pause is None:
            try:
                from progress import permanent_output
                self.pause = permanent_output()
            except ImportError: self.pause = nullcontext()
            self.pause.__enter__()
        ui = renderer(self.cfg, stream)
        if ui and ending: ui.text(text, 'warning')
        elif ui: ui.prompt(text)
        else: stream.write(text+ending); stream.flush()

    def close(self):
        if self.pause is not None:
            self.pause.__exit__(None, None, None)
            self.pause = None

    def line(self, text, ending, stream):
        text = text.strip()
        if not text: return
        self.last_activity = time.monotonic()
        self.partial_seen = ''
        if ending and self.manager == 'npm' and re.match(r'^npm warn deprecated\b', text, re.I):
            return  # Available in raw output; never inflate diagnostic counts/tails.
        if self.manager == 'apt' and ('File has unexpected size' in text or 'Mirror sync in progress' in text):
            self.mirror_sync = True
        if not ending or PROMPT.search(text):
            self.prompt(text, stream, ending)
            return
        if not self.tail or self.tail[-1] != text: self.tail.append(text)
        event = self.pip_stage(text) or self.npm_stage(text) or self.native_stage(text)
        if event: self.tick()
        error, warning = ERROR.match(text), WARNING.match(text)
        if error or warning:
            value = text[(error or warning).end():].strip() or text
            # npm repeats its code and advice around the useful registry diagnostic.
            if re.fullmatch(r'(?:code )?E?\d+', value) or value.startswith(('Note that you can also install', 'A complete log of this run')):
                return
            rows = self.errors if error else self.warnings
            if value not in rows:
                if len(rows) < 2: rows.append(value)
                else: self.extra += 1
        elif self.progress is not None and not event:
            if self.manager in ('pip', 'npm', 'go', 'winget'):
                self.tick(); return
            self.package = ''
            self.stage = ('Removing' if self.action == 'uninstall' else
                     'Downloading' if re.search(r'^(?:Get:|Downloading|Fetching)', text) else
                     'Installing' if re.search(r'^(?:Unpacking|Setting up|Installing|Successfully)', text) else
                     'Checking' if ROUTINE.match(text) else self.default_stage)
            self.tick()

    def result(self, rc, *, skipped=0, unchanged=False, names=()):
        self.close()
        status = 'failed (exit '+str(rc)+')' if rc else 'unchanged' if unchanged else 'complete'
        suffix = ' · '+str(skipped)+' skipped' if skipped else ''
        ui = renderer(self.cfg, sys.stdout)
        if ui:
            from plugin_presentation import STYLES
            role = 'error' if rc else 'muted' if unchanged else 'success'
            ui.ui.detail_spans(self.manager, [(status, STYLES[role]), (suffix, '90')], label_width=11)
        else: print('  '+self.manager+': '+status+suffix)
        sys.stdout.flush()
        if not rc and not unchanged and self.action in ('install', 'uninstall'):
            packages(self.cfg, 'Installed' if self.action == 'install' else 'Removed', names)
        if not rc and not unchanged and self.action == 'upgrade':
            packages(self.cfg, 'Updated', self.updated if self.updated else
                     ['unavailable' if self.updated is None else 'none'])
        messages = [(s, 'error') for s in (self.errors or (list(self.tail)[-2:] if rc else []))]
        messages += [(s, 'warning') for s in self.warnings]
        if rc and self.mirror_sync:
            retry = 'pkgs upgrade' if self.action == 'upgrade' else 'retry the '+self.action
            messages = [('Repository metadata is inconsistent (mirror sync). Retry pkgs refresh later, then '+retry+'.', 'error')]
        error_ui = renderer(self.cfg, sys.stderr)
        for message, role in messages:
            if error_ui: error_ui.text(self.manager+': '+message, role)
            else: print('  '+self.manager+': '+message, file=sys.stderr)
        if self.extra:
            text = self.manager+': '+str(self.extra)+' more diagnostic lines; --raw shows full output.'
            if error_ui: error_ui.text(text, 'muted')
            else: print('  '+text, file=sys.stderr)
