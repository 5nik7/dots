#!/usr/bin/env python3
"""Bounded Git XDG migration; preview by default, explicit apply with a journal."""
import argparse
import os
from pathlib import Path
import re
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'lib/dots/files'))
from mappings import MappingPlan, arguments, render
from catalog import platform
from progress import Progress, configure

ENTRY = '[include]\n  path = gitconfig\n  path = ~/.config/git-termux/config\n'


def settings(*options):
    """Read config as data only; never print values or invoke credential helpers."""
    env = {key: value for key, value in os.environ.items() if not key.startswith('GIT_CONFIG')}
    env['GIT_CONFIG_NOSYSTEM'] = '1'
    result = subprocess.run(['git', 'config', *options, '--null', '--list'], env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode:
        raise ValueError('Git could not validate configuration; no configuration values were printed')
    return [row for row in result.stdout.split(b'\0') if row and row.partition(b'\n')[0] != b'include.path']


def without_common_include(text):
    """Remove only the inspected old common include, preserving all other bytes."""
    pattern = r'(?m)^\[include\]\r?\n[ \t]*path[ \t]*=[ \t]*~/repos/dots/config/git/gitconfig[ \t]*\r?\n'
    updated, count = re.subn(pattern, '', text)
    if count > 1:
        raise ValueError('multiple old common includes; review manually')
    if '[include]' in updated or '[includeIf' in updated:
        raise ValueError('unexpected additional Android include; review manually')
    return updated


def migration_plan():
    if platform() != 'termux':
        raise ValueError('this bounded migration is for the existing Termux Git setup')
    home = Path(os.environ['HOME'])
    if Path(os.environ.get('XDG_CONFIG_HOME') or home / '.config') != home / '.config':
        raise ValueError('this Git migration requires the standard ~/.config XDG root; review the overlay include for a custom root')
    plan = MappingPlan(backup=True)
    common, android = plan.record('dots:git'), plan.record('androidots:git')
    expected_common = plan.root / 'config/git'
    expected_android = plan.root / 'androidots/config/git/gitconfig'
    if Path(common['source']) != expected_common or Path(android['source']) != expected_android:
        raise ValueError('Git sources changed; review the migration')
    if not common['enabled'] or not android['enabled']:
        raise ValueError('Git resource is stashed; review before migrating')
    if common['target_spec'] != '${CONFIG}/git' or common['strategy'] != 'directory-link':
        raise ValueError('common Git mapping changed; review the migration')
    if android['target_spec'] not in ('${HOME}/.gitconfig', '${CONFIG}/git-termux/config'):
        raise ValueError('Android Git destination changed; review the migration')
    entry = expected_common / 'config'
    plan.install.guard(entry)
    if entry.is_symlink() or (entry.exists() and entry.read_text() != ENTRY):
        raise ValueError('Git XDG entry point is occupied; review manually')
    if not entry.exists():
        plan.operation(entry, text=ENTRY)
    plan.install.guard(expected_android)
    text = expected_android.read_text()
    updated = without_common_include(text)
    if text != updated:
        plan.operation(expected_android, text=updated)
    for args in (
        ['edit', 'dots:git', '--apply', '--yes'],
        ['edit', 'androidots:git', '--target', '${CONFIG}/git-termux/config', '--apply', '--yes'],
    ):
        _, parsed = arguments(args)
        plan.edit(parsed)
    # Recovery payloads are retained; no source configuration values enter views.
    plan.rows.insert(0, dict(id='git:entry-points', status='prepare', source=str(entry),
                            target=str(expected_android),
                            reason='Add standard Git entry point; retain Android settings without the obsolete common include'))
    plan.finish()
    return plan


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--yes', action='store_true')
    args = parser.parse_args()
    if args.apply and not args.yes:
        parser.error('--apply requires --yes after reviewing the preview')
    configure(args.apply)
    with Progress('Planning Git configuration migration'):
        plan = migration_plan()
    doc = dict(action='Git configuration migration', status='preview', items=plan.rows)
    render(doc)
    if args.apply:
        expected = settings('--file', str(plan.root/'config/git/gitconfig'), '--includes')
        expected += settings('--file', str(plan.root/'androidots/config/git/gitconfig'), '--no-includes')
        with Progress('Migrating Git configuration'):
            result = plan.apply('git-config-migration')
        try:
            if settings('--global', '--includes') != expected:
                raise ValueError('Git global settings did not match the reviewed common and Android settings')
        except (OSError, ValueError):
            if result.get('id'):
                operations, guards, catalogs = plan.install.store.inverse(result['id'])
                plan.install.store.apply('undo-git-config-migration', operations, guards, retain=True, catalogs=catalogs)
            raise ValueError('Git verification failed; migration was undone without printing configuration values') from None
        doc.update(status=result['status'], transaction=result.get('id'))
        render(doc, True)
        print('  Verified standard Git global settings and retained Android overrides.')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError, TypeError) as error:
        from catalog import Presentation
        ui = Presentation(sys.stderr)
        ui.emit(ui.paint('Git migration: ' + str(error), '91'))
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(130)
