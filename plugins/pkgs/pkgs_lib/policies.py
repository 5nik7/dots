"""Validated, literal package policies. Reading policies never executes them."""
import copy
import re
from .common import Error
from .grammar import MANAGERS

DEFAULTS = {'upgrade': {'managers': 'auto'}, 'output': 'auto', 'policies': {}}
ACTIONS = ('install', 'upgrade')


def identity(name, manager):
    if manager == 'go': return name.partition('@')[0]
    return re.sub(r'[-_.]+', '-', name).lower() if manager in ('pip', 'uv-tool') else name


def literal(value):
    return isinstance(value, str) and bool(value) and not any(ord(c) < 32 or ord(c) == 127 for c in value)


def recipe(value, package=False):
    if not isinstance(value, dict) or set(value) - {'flags', 'before', 'replace', 'after'}:
        raise Error('recipes accept flags, before, replace and after only')
    flags = value.get('flags', [])
    if not isinstance(flags, list) or not all(literal(x) for x in flags):
        raise Error('recipe flags must be literal argument arrays')
    # Flags cannot change the target delimiter or smuggle package placeholders.
    if any(x == '--' or '{package' in x for x in flags):
        raise Error('recipe flags cannot contain -- or package placeholders')
    for field in ('before', 'replace', 'after'):
        commands = value.get(field, [])
        if not isinstance(commands, list) or field == 'replace' and field in value and not commands:
            raise Error(field + ' must be a command sequence (replace cannot be empty)')
        for cmd in commands:
            if not isinstance(cmd, list) or not cmd or not all(literal(x) for x in cmd):
                raise Error('recipe commands must be nonempty literal argv arrays')
            for arg in cmd:
                if '{package' in arg and arg not in ('{package}', '{packages}'):
                    raise Error('package placeholders must occupy a whole argument')
                if arg == '{package}' and not package:
                    raise Error('{package} requires a per-package recipe')
            if '{package' in cmd[0]:
                raise Error('a package cannot select a recipe executable')


def validate(cfg):
    cfg.setdefault('upgrade', copy.deepcopy(DEFAULTS['upgrade']))
    cfg.setdefault('output', 'auto')
    cfg.setdefault('policies', {})
    if cfg['output'] not in ('auto', 'styled', 'raw'):
        raise Error('output must be auto, styled or raw')
    upgrade = cfg['upgrade']
    if not isinstance(upgrade, dict) or set(upgrade) - {'managers'}:
        raise Error('upgrade requires a managers setting')
    upgrade.setdefault('managers', 'auto')
    managers = upgrade['managers']
    if managers != 'auto' and (not isinstance(managers, list) or not managers or
            any(m not in MANAGERS for m in managers) or len(set(managers)) != len(managers)):
        raise Error('upgrade.managers must be auto or a nonempty unique manager list')
    if not isinstance(cfg['policies'], dict):
        raise Error('policies must be a manager object')
    for manager, policy in cfg['policies'].items():
        if manager not in MANAGERS or not isinstance(policy, dict) or set(policy) - {'skip', 'packages', *ACTIONS}:
            raise Error('invalid manager policy: ' + str(manager))
        skips = policy.get('skip', [])
        if not isinstance(skips, list) or not all(literal(x) and not x.startswith('-') for x in skips):
            raise Error('skip must be a list of exact package identities')
        for action in ACTIONS:
            if action in policy: recipe(policy[action])
        packages = policy.get('packages', {})
        if not isinstance(packages, dict): raise Error('packages must be an object')
        normalized = set()
        for name, rules in packages.items():
            if not literal(name) or name.startswith('-') or identity(name, manager) in normalized:
                raise Error('invalid or duplicate policy package identity')
            normalized.add(identity(name, manager))
            if not isinstance(rules, dict) or set(rules) - set(ACTIONS):
                raise Error('package recipes support install and upgrade only')
            for action, entry in rules.items():
                recipe(entry, True)
                if 'replace' in entry and 'replace' in policy.get(action, {}):
                    raise Error('manager and package replacement recipes overlap')
    return cfg


def selected(cfg, manager, names, *, override=False, explicit=True):
    skips = {identity(n, manager) for n in cfg.get('policies', {}).get(manager, {}).get('skip', [])}
    blocked = [n for n in names if identity(n, manager) in skips] if not override else []
    if blocked and explicit:
        raise Error('Skipped by policy: ' + ', '.join(blocked) + '; use --ignore-skip to override')
    return [n for n in names if n not in blocked], blocked


def expand(commands, names):
    result = []
    for command in commands:
        args = []
        for arg in command:
            if arg == '{packages}': args.extend(names)
            elif arg == '{package}':
                if len(names) != 1: raise Error('{package} requires one package')
                args.append(names[0])
            else: args.append(arg)
        result.append(args)
    return result


def add_flags(command, flags):
    command = list(command)
    # Adapters put the target marker after their verb and built-in options.
    pos = command.index('--') if '--' in command else len(command)
    return command[:pos] + list(flags) + command[pos:]


def commands(backend, action, names, cfg, yes=False):
    """Wrap one manager operation; isolate packages with specific recipes."""
    policy = cfg.get('policies', {}).get(backend.name, {}) if action in ACTIONS else {}
    outer = policy.get(action, {})
    package_rules = {identity(k, backend.name): v.get(action, {}) for k, v in policy.get('packages', {}).items()}
    result = expand(outer.get('before', []), names)
    if 'replace' in outer:
        result += expand(outer['replace'], names)
    else:
        specific = [n for n in names if package_rules.get(identity(n, backend.name)) or n in getattr(backend,'pins',{})]
        ordinary = [n for n in names if n not in specific]
        groups = ([ordinary] if ordinary or not names else []) + [[n] for n in specific]
        if backend.name == 'uv-tool' and names or backend.name == 'go' and action == 'install':
            groups = [[n] for n in names]
        for group in groups:
            inner = package_rules.get(identity(group[0], backend.name), {}) if len(group) == 1 else {}
            result += expand(inner.get('before', []), group)
            if 'replace' in inner:
                result += expand(inner['replace'], group)
            else:
                flags = outer.get('flags', []) + inner.get('flags', [])
                pin = getattr(backend, 'pins', {}).get(group[0]) if len(group) == 1 else None
                if backend.name == 'go':
                    from .go_tools import transactions
                    targets = [group[0]+'@'+pin] if pin else group
                    result += transactions(action, targets, flags, getattr(backend, 'go_rows', None))
                else:
                    targets = group
                    if pin:
                        separator = {'apt':'=', 'dnf':'-', 'npm':'@', 'pip':'==', 'uv-tool':'=='}.get(backend.name)
                        if backend.name == 'dnf':
                            # rpm inventory identities include .arch; NEVRA places
                            # that suffix after the version-release selector.
                            name, dot, arch = group[0].rpartition('.')
                            targets = [name+'-'+pin+'.'+arch if dot and arch in (
                                'noarch','x86_64','aarch64','i686','armv7hl','ppc64le','s390x','riscv64') else group[0]+'-'+pin]
                        elif separator: targets = [group[0]+separator+pin]
                        elif backend.name == 'gem': flags += ['--version', pin]
                    if (getattr(backend,'bulk_system',False) and backend.name in ('pacman','paru','yay')
                            and group == ordinary and ordinary):
                        excluded = list(dict.fromkeys(getattr(backend,'skipped_targets',[]) + specific))
                        command = backend.transaction(action, [], yes)
                        if excluded: command = add_flags(command, ['--ignore', ','.join(excluded)])
                    else: command = backend.transaction(action, targets, yes)
                    result.append(add_flags(command, flags))
            result += expand(inner.get('after', []), group)
    result += expand(outer.get('after', []), names)
    return result
