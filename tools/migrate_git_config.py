#!/usr/bin/env python3
"""Bounded Git XDG migration; preview by default, explicit apply with a journal."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'lib/dots/files'))
from mappings import MappingPlan, render
from catalog import platform
from progress import Progress, configure

OLD_ENTRY = '[include]\n  path = gitconfig\n  path = ~/.config/git-termux/config\n'
ENTRY = '[include]\n  path = gitconfig\n  path = gitplatform\n'


def settings(*options):
    """Read config as data only; never print values or invoke credential helpers."""
    env = {key: value for key, value in os.environ.items() if not key.startswith('GIT_CONFIG')}
    env['GIT_CONFIG_NOSYSTEM'] = '1'
    result = subprocess.run(['git', 'config', *options, '--null', '--list'], env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode:
        raise ValueError('Git could not validate configuration; no configuration values were printed')
    return [row for row in result.stdout.split(b'\0') if row and row.partition(b'\n')[0] != b'include.path']


def migration_plan():
    if platform() != 'termux':
        raise ValueError('this bounded migration is for the existing Termux Git setup')
    home = Path(os.environ['HOME'])
    if Path(os.environ.get('XDG_CONFIG_HOME') or home / '.config') != home / '.config':
        raise ValueError('this legacy Git migration requires the standard ~/.config root')
    plan = MappingPlan(backup=True)
    common = plan.record('dots:git')
    source = plan.root / 'config/git'
    if (Path(common['source']) != source or common['target_spec'] != '${CONFIG}/git'
            or common['strategy'] != 'directory-link' or not common['enabled']):
        raise ValueError('common Git mapping changed or is stashed; review the migration')
    entry = source / 'config'
    plan.install.guard(entry)
    if entry.is_symlink() or not entry.is_file() or entry.read_text() not in (ENTRY, OLD_ENTRY):
        raise ValueError('Git entry point changed; review manually')
    if entry.read_text() != ENTRY:
        plan.operation(entry, text=ENTRY)
    overlay = source / 'termux'
    plan.install.guard(overlay)
    if overlay.is_symlink() or not overlay.is_file():
        raise ValueError('move the Termux settings into config/git/termux before migrating')
    # Catalog retirement is part of the same transaction as historical links.
    android = plan.documents.get('androidots')
    if android:
        rows = [r for r in android['resources'] if r['id'] == 'git']
        if rows and (rows[0]['source'] not in ('config/git/gitconfig', 'config/git/termux')
                     or rows[0]['target'] not in ('${HOME}/.gitconfig', '${CONFIG}/git-termux/config')):
            raise ValueError('Android Git mapping changed; review manually')
        android['resources'] = [r for r in android['resources'] if r['id'] != 'git']
        if rows:
            plan.rows.append(dict(id='androidots:git', status='retire', target=str(plan.paths['androidots']),
                                  reason='Remove the obsolete Androidots Git resource mapping'))
    locations = plan.root / 'androidots/.dots/file-locations.json'
    plan.install.guard(locations)
    location_changed = False
    if locations.exists():
        if locations.is_symlink() or not locations.is_file():
            raise ValueError('Android import mappings must be a regular file')
        doc = json.loads(locations.read_text())
        obsolete = [r for r in doc['locations'] if r['id'] == 'git']
        if obsolete and any(r['kind'] != 'file' or r['target'] != '${HOME}/.gitconfig'
                            or r['source'] not in ('config/git/gitconfig', 'config/git/termux') for r in obsolete):
            raise ValueError('Android Git import mapping changed; review manually')
        if obsolete:
            doc['locations'] = [r for r in doc['locations'] if r['id'] != 'git']
            plan.operation(locations, data=doc)
            location_changed = True
            plan.rows.append(dict(id='androidots:git', status='retire', target=str(locations),
                                  reason='Remove the obsolete Git import mapping'))
    legacy = (home / '.gitconfig', home / '.config/git-termux/config')
    known_sources = (plan.root / 'androidots/config/git/gitconfig', plan.root / 'androidots/config/git/termux')
    for target in legacy:
        plan.install.guard(target)
        owned = plan.install.entries.get(str(target))
        if owned and (owned['id'] != 'androidots:git' or plan.install.guards[str(target)] != owned['after']):
            raise ValueError('historical Git target changed; preserve and review it')
        if target.exists() or target.is_symlink():
            if not target.is_symlink() or target.resolve() not in [p.resolve() for p in known_sources]:
                raise ValueError('unrelated old target is protected: ' + str(target))
            plan.operation(target, delete=True)
            plan.live = True
            if owned:
                owned['after'] = None  # Retain its original recovery baseline.
            plan.rows.append(dict(id='androidots:git', status='unlink', target=str(target),
                                  reason='Retire the verified legacy Git link'))
    if any(e['id'] == 'androidots:git' and Path(p) not in legacy for p,e in plan.install.entries.items()):
        raise ValueError('unknown historical Android Git destination; review manually')
    plan.link(common)
    if entry.read_text() != ENTRY:
        from git_platform import plan as platform_plan
        start = len(plan.install.items)
        platform_plan(plan.install, common, entry_text=ENTRY)
        plan.rows.extend(plan.install.items[start:])
    plan.live = plan.live or bool(plan.install.operations)
    plan.rows.append(dict(id='dots:git', status='prepare', source=str(source), target=common['target'],
                          reason='Use common Git settings and the consolidated Termux overlay'))
    plan.finish()
    if location_changed:
        plan.catalogs.append(str(locations))
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
        expected += settings('--file', str(plan.root/'config/git/termux'), '--no-includes')
        with Progress('Migrating Git configuration'):
            result = plan.apply('git-config-migration')
        try:
            if settings('--global', '--includes') != expected:
                raise ValueError('Git global settings did not match the reviewed common and Termux settings')
        except (OSError, ValueError):
            if result.get('id'):
                operations, guards, catalogs = plan.install.store.inverse(result['id'])
                plan.install.store.apply('undo-git-config-migration', operations, guards, retain=True, catalogs=catalogs)
            raise ValueError('Git verification failed; migration was undone without printing configuration values') from None
        doc.update(status=result['status'], transaction=result.get('id'))
        render(doc, True)
        print('  Verified standard Git global settings and retained Termux overrides.')


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
