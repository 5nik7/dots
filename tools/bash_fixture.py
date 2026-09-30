#!/usr/bin/env python3
"""Public Bash fixture; native tools run only against owned configuration/state."""
from pathlib import Path
import shutil
from public_fixture import copy_public_tree
from zsh_fixture import REPO, fixture as zsh_fixture


def fixture(source=REPO):
    root, repo, env = zsh_fixture(source, plugins=False)
    copy_public_tree(source / 'shells/bash', repo / 'shells/bash', repo=source, fixture=repo, aliases=(REPO,))
    env['SHELL'] = shutil.which('bash')
    (Path(env['HOME']) / '.fzf.bash').write_text('source <(fzf --bash)\n')
    config = Path(env['XDG_CONFIG_HOME']) / 'atuin'
    config.mkdir(parents=True)
    (config / 'config.toml').write_text('auto_sync = false\nupdate_check = false\n')
    for variable in ('USERPROFILE', 'APPDATA', 'LOCALAPPDATA'):
        env[variable] = str(root / variable.lower())
    return root, repo, env
