"""Read-only lifecycle host classification; no subprocesses or shell profiles."""
import os
import sys


def classify(*, host, platform, android, executable, kernel, env, shell='python', shell_os=''):
    """Classify supplied observations without interpreting environment values as code."""
    evidence = ['Python platform: '+platform, 'Python host: '+host]
    if shell_os:
        evidence.append('Bash OSTYPE: '+shell_os)
    compatibility = shell_os.lower() if shell == 'bash' else platform.lower()
    if compatibility.startswith(('msys', 'mingw')):
        kind, label = 'msys', 'MSYS2 / Git Bash'
        if env.get('MSYSTEM'):
            evidence.append('MSYSTEM: '+env['MSYSTEM'])
    elif compatibility.startswith('cygwin'):
        kind, label = 'cygwin', 'Cygwin'
    elif host == 'nt':
        # Inherited WSL/MSYSTEM variables do not change a native Windows host.
        kind, label = 'windows', 'Windows'
    elif host == 'posix' and (platform == 'android' or android) and (
            env.get('TERMUX_VERSION') or env.get('TERMUX__PREFIX') or '/com.termux/' in executable):
        kind, label = 'termux', 'Termux (Android)'
        evidence.append('Native Android runtime and Termux identity')
    elif platform.startswith('linux'):
        markers = [key for key in ('WSL_DISTRO_NAME', 'WSL_INTEROP') if env.get(key)]
        if 'microsoft' in kernel.lower() or 'wsl' in kernel.lower():
            markers.append('WSL kernel')
        kind, label = ('wsl', 'WSL (Linux)') if markers else ('linux', 'Linux')
        evidence.extend(markers)
    elif platform == 'darwin':
        kind, label = 'posix', 'macOS'
    else:
        kind, label = 'other', platform+' ('+host+')'
    return {'environment': kind, 'label': label, 'host': host,
            'python': executable, 'evidence': evidence, 'shell': shell}


def detect(shell='python', shell_os=''):
    return classify(host=os.name, platform=sys.platform,
                    android=hasattr(sys, 'getandroidapilevel'), executable=sys.executable,
                    kernel=os.uname().release if hasattr(os, 'uname') else '',
                    env=os.environ, shell=shell, shell_os=shell_os)


def validate(info):
    if info['environment'] in ('msys', 'cygwin'):
        raise ValueError(info['label']+' Bash lifecycle is unsupported; open native PowerShell 7+ '
                         'in the source directory and run .\\install.ps1 -WhatIf '
                         '(or .\\uninstall.ps1 -WhatIf). No files changed.')
    if info['shell'] == 'bash' and info['host'] != 'posix':
        raise ValueError('Bash requires a compatible POSIX Python 3.11+ runtime; '
                         'do not mix Windows and WSL tools. Set BLASTOFF_PYTHON '
                         'to the native interpreter. No files changed.')
    return info
