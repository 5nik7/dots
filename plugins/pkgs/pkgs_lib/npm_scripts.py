"""Explicit one-run approval of native global npm blocked install scripts."""
import json
import os
import re
import sys

from .common import Error, budget, query

SPEC = r'((?:@[a-zA-Z0-9_.~-]+/)?[a-zA-Z0-9][a-zA-Z0-9_.~-]*@\d+\.\d+\.\d+(?:-[a-zA-Z0-9.-]+)?(?:\+[a-zA-Z0-9.-]+)?)'


def terminal():
    if not sys.stdout.isatty(): return False
    if os.name == 'nt': return sys.stdin.isatty() and sys.stderr.isatty()
    try:
        with open('/dev/tty', 'r'), open('/dev/tty', 'w'): return True
    except OSError: return False


def approve(spec):
    # Native approval must be explicit even when the package command used --yes.
    from . import reports  # shared interaction import path
    try:
        from interaction import gum_confirm
        answer = gum_confirm('Run install scripts for '+spec+' once?', 'Run scripts', 'Skip')
        if answer is not None: return answer
    except ImportError: pass
    prompt = 'Run install scripts for '+spec+' once? [y/N] '
    if os.name == 'nt':
        try: return input(prompt).strip().lower() in ('y', 'yes')
        except EOFError: return False
    with open('/dev/tty', 'r') as source, open('/dev/tty', 'w') as target:
        target.write(prompt); target.flush()
        return source.readline().strip().lower() in ('y', 'yes')


def evidence(specs, env=None):
    """Recheck native installed identities/scripts; warning text is not authority."""
    with budget(15):
        result = query(['npm', 'ls', '--global', '--all', '--long', '--json', '--', *specs], env=env)
    if result.returncode not in (0, 1): raise Error('npm script inventory failed')
    if len(result.stdout) > 8 * 1024 * 1024: raise Error('npm script inventory is too large')
    tree = json.loads(result.stdout)
    found = {spec: [] for spec in specs}
    pending = [tree]
    visited = 0
    while pending:
        row = pending.pop(); visited += 1
        if visited > 20000 or not isinstance(row, dict): raise Error('invalid npm script inventory')
        spec = str(row.get('name', ''))+'@'+str(row.get('version', ''))
        if spec in found:
            if row.get('link') or row.get('missing') or row.get('invalid'):
                raise Error('npm script target is linked, missing or invalid')
            # Global npm can omit resolved URLs after loading the installed tree.
            # Known source/link targets are never silently converted to registry approvals.
            if row.get('resolved') and not str(row['resolved']).startswith(('http://', 'https://')):
                raise Error('npm script target is a source install')
            if not row.get('path') or not os.path.isabs(row['path']):
                raise Error('npm script target has no installed path')
            scripts = row.get('scripts', {})
            if not isinstance(scripts, dict): raise Error('invalid npm script metadata')
            found[spec].append(json.dumps({k: row.get(k) for k in
                ('name', 'version', 'path', 'resolved', 'integrity', 'scripts', 'hasInstallScript')}, sort_keys=True))
        dependencies = row.get('dependencies', {})
        if not isinstance(dependencies, dict): raise Error('invalid npm dependencies')
        pending.extend(dependencies.values())
    if any(not records for records in found.values()): raise Error('npm script targets could not be verified')
    return {spec: sorted(set(records)) for spec, records in found.items()}


class Pending:
    def __init__(self):
        self.specs = set()
        self.ran = []
        self.current = []
        self.enabled = self.block = self.invalid = False
        self.expected = self.received = 0
        self.confirmed = set()
        self.rebuilding = False

    def finish(self):
        if self.block and self.expected != self.received: self.invalid = True

    def begin(self, command):
        self.finish()
        self.block = False
        self.expected = self.received = 0
        self.enabled = False
        if not command or len(command) < 3: return
        if os.path.basename(command[0]).lower() not in ('npm', 'npm.cmd', 'npm.exe'): return
        if command[1] not in ('install', 'update'): return
        arguments = command[2:command.index('--')] if '--' in command else command[2:]
        options = [argument for argument in arguments if argument.startswith('-')]
        # Custom prefixes/config files or project recipes keep their native review.
        self.enabled = bool(set(options) & {'--global', '-g'}) and all(
            option in ('--global', '-g', '--force', '--no-audit', '--no-fund') for option in options)

    def observe(self, text):
        if self.rebuilding and re.match(r'^npm warn rebuild \d+ packages? had install scripts blocked because they are not covered by allowScripts[.:]', text, re.I):
            return True  # The final Scripts blocked field reflects remaining choices.
        finished = re.match(r'^npm info run '+SPEC+r' (?:preinstall|install|postinstall|prepare) \{\s*code:\s*0,', text)
        if self.rebuilding and finished and finished[1] in self.specs:
            self.confirmed.add(finished[1])
        if not self.enabled: return False
        prefix = re.match(r'^npm warn install-scripts\s*', text, re.I)
        if not prefix: return False
        value = text[prefix.end():]
        if re.fullmatch(r'\d+ packages? had install scripts blocked because they are not covered by allowScripts:', value):
            self.finish()
            self.block = True
            self.expected, self.received = int(value.split()[0]), 0
            return True
        if not self.block: return False
        match = re.match(SPEC+r' \(', value)
        if match and len(match[1]) <= 256 and len(self.specs) < 128:
            self.received += 1
            self.specs.add(match[1]); return True
        if not value or value.startswith(('Run `', 'all global installs.')): return True
        self.invalid = True
        return False

    def review(self, item, cfg, output, rc):
        self.finish()
        if not self.specs or rc or self.invalid: return rc
        from . import workflows, streams
        from . import script_receipts
        from .upgrade_output import packages
        env = getattr(item.backend, 'operation_env', None)
        interactive=terminal()
        for spec in sorted(self.specs):
            if not interactive and not script_receipts.location(spec).is_file(): continue
            try:
                with workflows.progress('npm · Checking script approval', cfg): before = evidence([spec], env)
                proof=script_receipts.fingerprint(before.get(spec,[]))
                if script_receipts.matches(spec,proof):
                    self.current.append(spec)
                    continue
                if not interactive: continue
                packages(cfg, 'Scripts', [spec])
                if not approve(spec): continue
                with workflows.progress('npm · Rechecking '+spec, cfg): after = evidence([spec], env)
                if before != after: raise Error('installed script metadata changed; review again')
                if proof and script_receipts.fingerprint(after.get(spec,[])) != proof:
                    raise Error('installed script files changed; review again')
                # npm cannot always verify version-pinned allow rules for global
                # installs. Scope permission by name for this invocation, while
                # rebuild selects only the reviewed exact version.
                command = ['npm', 'rebuild', '--global', '--loglevel=info',
                           '--allow-scripts='+spec.rsplit('@', 1)[0], '--', spec]
                self.confirmed.discard(spec)
                with workflows.progress('npm · Running scripts · '+spec, cfg) as meter:
                    output.progress = meter
                    self.rebuilding = True
                    try:
                        code = streams.run(command, dict(cfg, _manager='npm', _upgrade_output=output), env=env)
                    finally:
                        output.close(); output.progress = None; self.rebuilding = False
                if code in (-2, -15, 130, 143): raise KeyboardInterrupt
                if code: return code if code > 0 else 128-code
                if spec not in self.confirmed:
                    raise Error('npm did not confirm script execution for '+spec+'; inspect with --raw')
                self.ran.append(spec)
                if proof:
                    try:
                        # Script-generated outputs are part of the saved evidence.
                        saved=evidence([spec],env)
                        if saved==after: script_receipts.save(spec,script_receipts.fingerprint(saved.get(spec,[])))
                    except (Error,OSError,ValueError,TypeError):
                        output.line('npm warn Script receipt unavailable; review may be needed next time.','\n',sys.stderr)
            except (Error, OSError, ValueError, TypeError) as error:
                output.line('npm error Script approval: '+str(error), '\n', sys.stderr)
                return 1
        return rc

    def result(self, cfg):
        from .upgrade_output import packages
        if self.ran: packages(cfg, 'Scripts ran', self.ran)
        if self.current: packages(cfg, 'Scripts current', self.current)
        blocked = sorted(self.specs - set(self.ran) - set(self.current))
        if blocked: packages(cfg, 'Scripts blocked', blocked)
        if self.invalid: packages(cfg, 'Script review', ['incomplete; use --raw to inspect npm instructions'])
