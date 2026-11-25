"""Plan checkout-independent shell startup files inside the install transaction."""
import os
from pathlib import Path

from managed_destination import points_to
from transactions import exists


def bootstrap_entry(installation, row, source, target):
    templates = installation.root / 'shells/bootstrap'
    if row['strategy'] != 'copy':
        return False
    if source == installation.root/'shells/bash/.bash_profile':
        installation.add(row['id'], target, source=source, managed=points_to(target, source))
        return True
    if source.parent != templates:
        return False
    shells = {'rc.sh', 'config.fish', 'config.nu', 'profile.ps1', 'rc.xsh'}
    if source.name not in shells:
        return False

    helpers = installation.root / 'lib/dots/shell/bootstrap'
    home = Path(os.environ.get('HOME') or Path.home())
    data = home / '.local/share/dots/bootstrap'
    helper = 'locate.ps1' if installation.platform == 'windows' else 'locate.sh'
    if source.name == 'profile.ps1':
        helper = 'locate.ps1'
    for name in (helper, 'checkout'):
        if name not in installation.bootstrap_outputs:
            installation.bootstrap_outputs.add(name)
            if name == 'checkout':
                installation.add('dots:shell-bootstrap:checkout', data/name, text=str(installation.root) + '\n')
            else:
                installation.add('dots:shell-bootstrap:' + name, data/name, source=helpers/name)

    if source.name in ('config.fish', 'config.nu'):
        family = 'fish' if source.name == 'config.fish' else 'nushell'
        legacy = installation.root / 'shells' / family
        # A legacy complete-directory link cannot hold a standalone rc.
        # Repoint just that verified link to a durable directory and retain its
        # other members, including untracked entries, at their original sources.
        # The Store never follows a user configuration directory while writing.
        if target.parent.is_symlink():
            bridge = data / family
            if points_to(target.parent, legacy):
                if exists(bridge):
                    installation.item(row['id'], 'conflict', bridge, reason='bootstrap directory is already occupied')
                    return True
                installation.guard(legacy)
                for member in sorted(legacy.iterdir()):
                    if member.name != source.name:
                        installation.add(row['id'], bridge/member.name, link=member, directory=member.is_dir())
                installation.add(row['id'], target.parent, link=bridge, directory=True, managed=True)
            elif not (points_to(target.parent, bridge) and
                      installation.entries.get(str(target.parent), {}).get('id') == row['id']):
                installation.item(row['id'], 'conflict', target.parent, reason='unrecognized shell configuration directory link')
                return True
            target = bridge/source.name
        elif family == 'fish':
            # Fish itself reads universal variables and Fisher reads fish_plugins
            # before the rc. Seed native assets only when the user lacks them.
            for member in ('fish_variables', 'fish_plugins'):
                original, destination = legacy/member, target.parent/member
                if original.is_file() and not exists(destination):
                    installation.add(row['id'], destination, source=original)
            themes = target.parent/'themes'
            if not themes.is_symlink() and (not exists(themes) or themes.is_dir()):
                for theme in sorted((legacy/'themes').glob('*.theme')):
                    if not exists(themes/theme.name):
                        installation.add(row['id'], themes/theme.name, link=theme)
        if family == 'nushell':
            from bootstrap_snippet import installed_nu_entry
            installation.guard(helpers/'entry.nu')
            installation.add(row['id'], data/'entry.nu', text=installed_nu_entry(installation.root))

    old_entries = {
        'bash': ('shells/bash/.bashrc', 'shells/bash/init.bash'),
        'zsh': ('shells/zsh/zshrc', 'shells/zsh/init.zsh'),
        'fish': ('shells/fish/config.fish',),
        'nushell': ('shells/nushell/config.nu',),
        'xonsh': ('shells/xonsh/.xonshrc',),
        'powershell': ('shells/powershell/profile.ps1', 'shells/powershell/Microsoft.PowerShell_profile.ps1'),
    }
    recognized = any(points_to(target, installation.root/old)
                     for old in old_entries.get(row['app'], ()))
    installation.add(row['id'], target, source=source, managed=recognized)
    if str(target) in installation.entries:
        installation.entries[str(target)]['shell_bootstrap'] = helper
    return True


def bootstrap_retention(installation, selected):
    """Keep the entire entry usable if uninstall must preserve a customization."""
    entries = installation.entries
    retained = set()
    data = Path(os.environ.get('HOME') or Path.home()) / '.local/share/dots/bootstrap'
    for path, rc in entries.items():
        helper = rc.get('shell_bootstrap')
        if not helper:
            continue
        owner = rc['id']
        if selected is not None and owner not in selected:
            retained.update(('dots:shell-bootstrap:' + helper, 'dots:shell-bootstrap:checkout'))
            continue
        installation.guard(path)
        changed = installation.guards[path] != rc['after']
        family = Path(path).parent
        if family.parent == data and family.name in ('fish', 'nushell') and family.is_dir():
            installation.guard(family)
            changed |= any(str(child) not in entries for child in family.iterdir())
            for member, entry in entries.items():
                if entry['id'] == owner:
                    installation.guard(member)
                    changed |= installation.guards[member] != entry['after']
        if changed:
            retained.update((owner, 'dots:shell-bootstrap:' + helper, 'dots:shell-bootstrap:checkout'))
    return retained


def unused_helpers(entries, selected):
    users = [entry for entry in entries.values() if entry.get('shell_bootstrap')]
    if not any(entry['id'] in selected for entry in users):
        return set()
    remaining = {entry['shell_bootstrap'] for entry in users if entry['id'] not in selected}
    names = {entry['shell_bootstrap'] for entry in users} - remaining
    if not remaining:
        names.add('checkout')
    return {'dots:shell-bootstrap:' + name for name in names}
