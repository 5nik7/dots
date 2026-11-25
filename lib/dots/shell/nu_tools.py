"""Prepare optional native Nushell sources for the current REPL only."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


GENERATORS = {
    'zoxide': ['init', 'nushell'],
    'mise': ['activate', 'nu'],
    'atuin': ['init', 'nu'],
    'tv': ['init', 'nu'],
    'starship': ['init', 'nu'],
}


def prepare(selected, env=None):
    """Produce one-shot hooks in memory. Native source may embed this session's PATH."""
    env = os.environ if env is None else env
    path = env.get('PATH', '')
    home = Path(env.get('HOME') or env.get('USERPROFILE') or Path.home())
    atuin_env = home / '.atuin/bin/env'
    sources = {}
    for tool, args in GENERATORS.items():
        if tool not in selected:
            continue
        if tool == 'atuin' and not (atuin_env.is_file() and os.access(atuin_env, os.R_OK)):
            continue
        exe = shutil.which(tool, path=path)
        if not exe:
            continue
        try:
            run = subprocess.run([exe, *args], env=env, stdin=subprocess.DEVNULL,
                                 stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=3)
            if run.returncode or len(run.stdout) > 1024 * 1024:
                continue
            code = run.stdout.decode('utf-8').strip()
        except (OSError, UnicodeError, subprocess.TimeoutExpired):
            continue
        if not code:
            continue
        if tool == 'mise':
            # Nu imports the generated module's main as the native mise command.
            code = 'module mise {\n' + code + '\n}\nuse mise'
        elif tool in ('tv', 'atuin'):
            code = ('let dots_prior_bindings = $env.config.keybindings\n' + code +
                    '\n_dots-keep-keybindings $dots_prior_bindings')
        sources[tool] = code
    if 'direnv' in selected and shutil.which('direnv', path=path):
        sources['direnv'] = '_dots-direnv-init'
    if not sources:
        return dict(loaded=[], hooks=[])
    # Nu takes a snapshot of the current pre_prompt hooks before executing them.
    # Remove the whole group first so even a broken optional script only runs once.
    marker = '# dots optional integration\n'
    cleanup = ('$env.config.hooks.pre_prompt = ($env.config.hooks.pre_prompt | where {|hook| '
               'if ($hook | describe) == string { not ($hook | str starts-with "# dots optional integration") } '
               'else { true } })')
    return dict(loaded=list(sources), hooks=[marker + source for source in [cleanup, *sources.values()]])


if __name__ == '__main__':
    print(json.dumps(prepare(sys.argv[1:])))
