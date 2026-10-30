"""Evidence from known configs, receipts and inherited values. No subprocesses/writes."""
import configparser
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import tomllib

from file_platform import check_object
from transactions import parents_safe

FAILURES = {'different', 'stale'}

from profile_config import config_path


def result(status='unknown', basis='unsupported', reason='No bounded check is available for this consumer.', paths=(), automation=None):
    summary = {'matches': {'environment': 'environment matches', 'installed-content': 'installed content matches'}.get(basis, 'matches current'),
               'configured': 'configured', 'different': 'different from current', 'stale': 'stale generation',
               'unknown': 'unknown', 'not-configured': 'not configured'}[status]
    return dict(status=status, basis=basis, summary=summary, reason=reason,
                paths=[str(p) for p in paths], automation=automation)


class Verifier:
    def __init__(self, inspection, read):
        self.inspection, self.read = inspection, read
        self.cache, self.results = {}, {}
        self.env = dict(os.environ)
        self.generation, self.config = inspection.generation, inspection.config

    def bytes(self, path):
        path = Path(path)
        key = str(path)
        if key not in self.cache:
            try:
                if not path.is_absolute(): raise ValueError('relative config path')
                if path.is_relative_to(self.inspection.state):
                    parents_safe(path)
                    if path.is_symlink(): raise ValueError('state evidence is a symlink')
                for parent in (path, *path.parents): check_object(parent)
                real = path.resolve(strict=True)
                parents_safe(real)
                before = real.stat()
                data = self.read(real, 256 * 1024)
                after = real.stat()
                signature = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns)
                if signature(before) != signature(after) or path.resolve(strict=True) != real:
                    raise ValueError('configuration changed during inspection')
                self.cache[key] = data
            except (OSError, ValueError, RuntimeError) as error:
                self.cache[key] = error
        value = self.cache[key]
        if isinstance(value, Exception): raise value
        return value

    def text(self, path):
        return self.bytes(path).decode('utf-8-sig')

    def optional(self, path):
        try: return self.bytes(path)
        except FileNotFoundError: return None

    def previous(self, path):
        """Only publication ancestry proves an older generation; names are random."""
        current = self.generation
        for _ in range(32):
            try: token = self.text(current / 'previous').strip()
            except (OSError, ValueError, RuntimeError): return False
            if not re.fullmatch(r'g\.[A-Za-z0-9]+', token): return False
            current = self.generation.parent / token
            if path.is_relative_to(current): return True
        return False

    def environment_value(self, key, expected):
        observed = self.env.get(key)
        if observed is None: return result(basis='environment', reason=key + ' is not exported to this command.')
        return result('matches' if observed == expected else 'different', 'environment',
                      key + (' matches the captured generation.' if observed == expected else ' differs from the captured generation; it may be an intentional override.'))

    def bat(self):
        if 'BAT_THEME' not in self.env or 'BAT_CACHE_PATH' not in self.env:
            return result(basis='environment', reason='BAT_THEME and BAT_CACHE_PATH are not both exported.')
        if self.env['BAT_THEME'] != 'Dots':
            return result('different', 'environment', 'BAT_THEME selects another theme.')
        observed = Path(self.env['BAT_CACHE_PATH'])
        if not observed.is_absolute(): return result(basis='environment', reason='BAT_CACHE_PATH is relative.')
        observed = observed.resolve(strict=True)
        expected = self.generation / 'bat-cache'
        if observed == expected:
            return result('matches', 'environment', 'BAT_THEME selects Dots and BAT_CACHE_PATH resolves to this generation.', [expected])
        return result('stale' if self.previous(observed) else 'different', 'environment',
                      'BAT_CACHE_PATH resolves to another location.', [observed])

    def fzf(self):
        if self.env.get('FZF_DEFAULT_OPTS_FILE'):
            return result(basis='environment', reason='FZF_DEFAULT_OPTS_FILE adds options outside this bounded check.')
        text = self.text(self.generation / 'fzf.sh').replace('\\\n', '')
        colors = None
        for line in text.splitlines():
            if not line.strip() or line.lstrip().startswith('#'): continue
            match = re.fullmatch(r'export _FZF_COLORS_="([^"]+)"', line)
            if match and colors is None: colors = match[1]
            elif line != 'export FZF_DEFAULT_OPTS="${FZF_DEFAULT_OPTS} --color=$_FZF_COLORS_"':
                raise ValueError('unsupported FZF template')
        if not colors: raise ValueError('missing FZF colors')
        def parsed(value):
            values = {}
            for part in value.split(','):
                key, sep, val = part.partition(':')
                if not sep or not re.fullmatch(r'[a-z][a-z+-]*', key) or not re.fullmatch(r'[A-Za-z0-9:#;+-]+', val):
                    raise ValueError('unsupported FZF color option')
                values[key] = val.lower()
            return values
        expected = parsed(colors)
        if 'FZF_DEFAULT_OPTS' not in self.env:
            return result(basis='environment', reason='FZF_DEFAULT_OPTS is not exported.')
        words = shlex.split(self.env['FZF_DEFAULT_OPTS'])
        observed, i = {}, 0
        while i < len(words):
            word = words[i]
            if word == '--color':
                i += 1
                if i >= len(words): raise ValueError('missing color option')
                word = '--color=' + words[i]
            if word.startswith('--color='):
                value = word.partition('=')[2]
                if value in ('bw', 'dark', 'light', '16'): observed = {}
                else: observed.update(parsed(value))
            i += 1
        matches = all(observed.get(k) == v for k, v in expected.items())
        return result('matches' if matches else 'different', 'environment',
                      'Effective literal FZF color options ' + ('match.' if matches else 'differ from the published colors.'))

    def gum(self):
        expected = {}
        for line in self.text(self.generation / 'gum_env.sh').splitlines():
            if not line.strip() or line.lstrip().startswith('#'): continue
            match = re.fullmatch(r"export ((?:GUM_[A-Z_]+|FOREGROUND|BACKGROUND|BORDER_FOREGROUND|BORDER_BACKGROUND))='(#[a-fA-F0-9]{6})'", line)
            if not match: raise ValueError('unsupported Gum assignment')
            expected[match[1]] = match[2]
        if not expected: raise ValueError('empty Gum data')
        exported = {k: self.env[k] for k in expected if k in self.env}
        if any(exported[k] != expected[k] for k in exported):
            return result('different', 'environment', 'Exported Gum color assignments differ from the generation.')
        if len(exported) != len(expected):
            return result(basis='environment', reason='Not all published Gum color assignments are exported.')
        return result('matches', 'environment', 'All published Gum color assignments match inherited values.')

    def connection(self, app):
        return next((c for c in self.inspection.connections if c['app'] == app and c['origin'] == 'fixed'), None)

    def reference(self, value, config, target):
        if value.startswith('#{d:current_file}/'):
            value = str(config.parent / value[len('#{d:current_file}/'):])
        if any(c in value for c in ('$','`','*','?','{','}')): return None
        if value.startswith('~/'): value = str(self.inspection.home / value[2:])
        path = Path(value)
        if not path.is_absolute(): path = config.parent / path
        for candidate in (path, target):
            for parent in (candidate, *candidate.parents): check_object(parent)
        return path.resolve(strict=False) == target.resolve(strict=False)

    def config_reference(self, app, artifact):
        c = self.connection(app)
        if not c or not c['target'] or c['reason'] == 'No connector on this platform.':
            return result(basis='configuration', reason='No supported application destination on this platform.')
        target = Path(c['target'])
        base = target.parent.parent if app in ('yazi', 'btop', 'leaf', 'television') else target.parent
        config = base / {'yazi':'theme.toml', 'btop':'btop.conf', 'leaf':'config.toml',
                         'television':'config.toml', 'kitty':'kitty.conf', 'tmux':'tmux.conf'}[app]
        text = self.text(config)
        paths = [config]
        if app in ('yazi', 'leaf', 'television'):
            doc = tomllib.loads(text)
            if app == 'yazi':
                flavor = doc.get('flavor', {})
                values = [flavor.get(k) for k in ('dark', 'light')]
                if None in values: return result(basis='configuration', reason='Both Yazi flavor selections are not explicit.', paths=paths)
                if len(set(values)) > 1: return result(basis='configuration', reason='Yazi flavor selection depends on runtime light/dark mode.', paths=paths)
                matches = values == ['dots', 'dots']
            elif app == 'television':
                value = doc.get('ui', {}).get('theme')
                if value is None: return result(basis='configuration', reason='No explicit Television UI theme selection.', paths=paths)
                matches = value == 'dots'
            else:
                value = self.env.get('LEAF_THEME', doc.get('theme'))
                if value is None: return result(basis='configuration', reason='No explicit Leaf theme selection.', paths=paths)
                matches = self.reference(value, config, target)
                if artifact == 'bat.tmTheme' and matches:
                    leaf = tomllib.loads(self.text(self.generation / 'leaf.toml'))
                    matches = leaf.get('syntax') == 'dots.tmTheme'
        elif app == 'btop':
            values = re.findall(r'^\s*color_theme\s*=\s*"([^"\n]+)"\s*(?:#.*)?$', text, re.M)
            if len(values) != 1: return result(basis='configuration', reason='Btop theme selection is missing or ambiguous.', paths=paths)
            matches = values[0] == 'dots'
        else:
            matches, dynamic = False, False
            for line in text.splitlines():
                stripped = line.lstrip()
                if not stripped or stripped.startswith('#'): continue
                candidate = re.match(r'(?:include|globinclude|envinclude)\s' if app == 'kitty' else r'source-file\s', stripped)
                if not candidate:
                    if app == 'tmux' and 'source-file' in line: dynamic = True
                    continue
                words = shlex.split(line, comments=True)
                # shlex treats tmux format syntax inside quotes as literal data.
                if not words: continue
                if app == 'kitty' and words[0] in ('include', 'globinclude', 'envinclude'):
                    if words[0] != 'include' or len(words) != 2: dynamic = True; continue
                    value = words[1]
                elif app == 'tmux' and words[0] == 'source-file':
                    if len(words) < 2 or any(w not in ('-q','-F') for w in words[1:-1]): dynamic = True; continue
                    value = words[-1]
                else:
                    if app == 'tmux' and 'source-file' in line and not line.lstrip().startswith('#'): dynamic = True
                    continue
                match = self.reference(value, config, target)
                if match is None: dynamic = True
                elif match: matches = True
            if dynamic or not matches:
                return result(basis='configuration', reason='Includes are dynamic, indirect, or do not identify a supported direct reference.', paths=paths)
        if matches is None: return result(basis='configuration', reason='Theme reference is dynamic.', paths=paths)
        return result('configured' if matches else 'different', 'configuration',
                      'Known theme selection/reference ' + ('matches; runtime overrides are not evaluated.' if matches else 'selects something else.'), paths)

    def automation(self, app):
        from plugins import PATTERN
        data = self.optional(config_path('theme-plugins.json'))
        if data is None: return 'disabled'
        doc = json.loads(data)
        if doc.get('schema') != 1 or not isinstance(doc.get('enabled'), dict): return 'unknown'
        identity = doc['enabled'].get(app)
        if identity is None: return 'disabled'
        if not isinstance(identity, str): return 'unknown'
        origin, _, filename = identity.partition('/')
        match = PATTERN.fullmatch(filename)
        if not (origin == 'bundled' and match and match[2] == app): return 'unknown'
        if os.name == 'nt' and app != 'starship' and filename.endswith('.sh'): return 'unknown'
        if os.name != 'nt' and filename.endswith('.ps1'): return 'unknown'
        return 'enabled'

    def plugin(self, app):
        automation = self.automation(app)
        if app == 'starship':
            from starship import update_palette, update_symbols
            path = Path(self.env.get('STARSHIP_CONFIG') or self.inspection.home / '.config/starship.toml')
            data = self.bytes(path)
            doc = tomllib.loads(data.decode('utf-8-sig'))
            if 'palette' not in doc: return result(basis='configuration', reason='No explicit Starship palette selected.', paths=[path], automation=automation)
            if doc['palette'] != 'dots': return result('different', 'configuration', 'Starship selects another palette.', [path], automation)
            expected = tomllib.loads(self.text(self.generation / 'blastoff.toml'))
            colors = expected['palettes']['dots']
            if expected.get('palette') != 'dots' or not colors or any(not re.fullmatch(r'#[a-fA-F0-9]{6}|reset', v) for v in colors.values()):
                raise ValueError('invalid generated palette')
            preference_path = self.generation / 'preferences.json'
            preferences = json.loads(self.text(preference_path)) if preference_path.is_file() else {}
            matches = update_symbols(update_palette(data, colors), preferences) == data
            return result('matches' if matches else 'different', 'installed-content',
                          'Selected Starship Dots palette ' + ('matches.' if matches else 'differs from the generation.'), [path], automation)
        from plugin_apps import GTK_BLOCK, qt_registration
        target = self.config / ('gtk-3.0/dots-theme.css' if app == 'gtk' else 'qt6ct/colors/dots.conf')
        registration = self.config / ('gtk-3.0/gtk.css' if app == 'gtk' else 'qt6ct/qt6ct.conf')
        data = self.optional(target)
        original = self.optional(registration)
        receipt_data = self.optional(self.inspection.state / 'theme-plugins' / (app + '.json'))
        if data is None and original is None and receipt_data is None:
            return result('not-configured', 'installed-content', 'No installed plugin configuration.', automation=automation)
        old = json.loads(receipt_data) if receipt_data is not None else None
        if receipt_data is not None and (not isinstance(old, dict) or old.get('schema') != 1 or old.get('plugin') != app or not isinstance(old.get('registration'), dict) or not isinstance(old.get('generated'), str)):
            raise ValueError('malformed plugin receipt')
        expected = self.bytes(self.generation / ('gtk.css' if app == 'gtk' else 'qt6ct.conf'))
        if app == 'gtk':
            text = (original or b'').decode('utf-8-sig')
            if text.count('/* dots theme plugin: begin */') > 1: raise ValueError('ambiguous GTK registration')
            registered = text.count(GTK_BLOCK) == 1
        else:
            _, expected_selection = qt_registration(original, None, target)
            selection = configparser.ConfigParser(interpolation=None)
            selection.read_string((original or b'').decode('utf-8-sig'))
            registered = all(selection.get('Appearance', key, fallback=None) == value
                             for key, value in expected_selection.items())
        receipt_matches = not old or data is not None and hashlib.sha256(data).hexdigest() == old['generated']
        matches = data == expected and registered and receipt_matches
        reason = 'Installed content and registration match' if matches else 'Installed content, registration or receipt differs'
        if not old: reason += '; no ownership receipt is available'
        return result('matches' if matches else 'different', 'installed-content', reason + '.', [target, registration], automation)

    def verify(self, app, artifact, connection=False):
        key = (app, artifact, connection)
        if key in self.results: return self.results[key]
        try:
            if app == 'bat': value = self.bat()
            elif app == 'fzf': value = self.fzf()
            elif app == 'gum': value = self.gum()
            elif app == 'shell' and artifact == 'ls_colors': value = self.environment_value('LS_COLORS', self.text(self.generation / 'ls_colors').rstrip('\r\n'))
            elif app in ('gtk','qt6ct','starship'): value = self.plugin(app)
            elif app in ('kitty','tmux','btop','leaf','television') or app == 'yazi' and connection:
                value = self.config_reference(app, artifact)
            else: value = result()
        except FileNotFoundError:
            value = result(basis='configuration', reason='Required configuration or evidence is absent.')
        except (OSError, ValueError, RuntimeError, TypeError, KeyError, AttributeError, configparser.Error):
            value = result(basis='configuration', reason='Evidence is unreadable, malformed, ambiguous or changed during inspection.')
        self.results[key] = value
        return value


def annotate(inspect, doc, read, include_failures=False, app=None):
    verifier = Verifier(inspect, read)
    findings = []
    seen = set()
    for row in doc['artifacts']:
        for field in ('connections', 'consumers'):
            for consumer in row[field]:
                evidence = verifier.verify(consumer['app'], row['id'], field == 'connections')
                consumer['verification'] = evidence
                if app and consumer['app'] != app: continue
                key = (consumer['app'], row['id'])
                if evidence['status'] in FAILURES and evidence['automation'] != 'disabled' and key not in seen:
                    seen.add(key)
                    findings.append(dict(app=consumer['app'], artifact=row['id'], status=evidence['status'], reason=evidence['reason']))
    doc['consumer_findings'] = findings
    doc['consumer_checks'] = include_failures
    if include_failures: doc['healthy'] = doc['healthy'] and not findings
    return doc

