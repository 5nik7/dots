"""Canonical platform source names; legacy IDs are for persisted data only."""
import argparse

LEGACY_SOURCES = {'androidots': 'termux', 'windots': 'windows'}


def canonical(value):
    if not isinstance(value, str): return value
    owner, separator, name = value.partition(':')
    return LEGACY_SOURCES.get(owner, owner) + separator + name


def current_source(value):
    replacement = canonical(value)
    if replacement != value:
        raise argparse.ArgumentTypeError(f'{value} was renamed; use {replacement}')
    return value


def validate_cli(args, parser):
    values = [getattr(args, 'repo', None)]
    resources = list(getattr(args, 'replaces', None) or [])
    if getattr(args, 'action', None) in ('source','target','show','link','remove','stash','edit','repair'):
        resources.extend(getattr(args, 'values', None) or [])
        resources.append(getattr(args, 'value', None))
    values.extend(value for value in resources if isinstance(value,str) and ':' in value)
    for value in values:
        if value is None: continue
        try: current_source(value)
        except argparse.ArgumentTypeError as error: parser.error(str(error))


def document(data):
    result = dict(data, repository=canonical(data.get('repository')))
    result['resources'] = [dict(row, **({'replaces':[canonical(v) for v in row['replaces']]} if 'replaces' in row else {})) for row in data['resources']]
    return result
