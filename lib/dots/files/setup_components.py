"""Stable checkout component identities; selection never implies removal."""

COMPONENTS = ('core', 'files', 'themes', 'anodize', 'blastoff', 'pkgs',
              'packages', 'fonts', 'leaf')
DEFAULTS = COMPONENTS[:6]


def component(identity):
    if identity.startswith('theme:'):
        return 'themes'
    if identity.startswith('setup:leaf'):
        return 'leaf'
    if identity.startswith('setup:font:'):
        return 'fonts'
    if identity in ('dots:command', 'dots:todo:command', 'dots:fonts:command', 'dots:manual'):
        return 'core'
    for name in ('anodize', 'blastoff', 'pkgs'):
        if identity.startswith('dots:' + name + ':'):
            return name
    return 'files'


def validate(values):
    values = list(dict.fromkeys(values))
    unknown = set(values) - set(COMPONENTS)
    if unknown:
        raise ValueError('unknown setup component: ' + ', '.join(sorted(unknown)))
    return values
