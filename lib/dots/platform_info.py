"""Read-only execution-context detection, shared by Dots controllers."""
import os
from pathlib import Path
import platform as host
import re


def os_release(path):
    result = {}
    try:
        for line in Path(path).read_text(encoding='utf-8').splitlines():
            key, sep, value = line.partition('=')
            if sep and key in ('ID', 'ID_LIKE', 'NAME', 'VERSION_ID'):
                result[key] = value.strip().strip('\"\'')
    except (OSError, UnicodeError):
        pass
    return result


def detect(*, env=None, system=None, release=None, machine=None, release_file=None):
    env = os.environ if env is None else env
    system = host.system() if system is None else system
    release = host.release() if release is None else release
    runtime = system.lower()
    evidence = []
    prefix = env.get('TERMUX__PREFIX') or env.get('PREFIX', '')
    if system == 'Windows' or system.startswith(('MSYS', 'CYGWIN', 'MINGW')):
        selected = 'windows'
        runtime = 'native' if system == 'Windows' else system.split('_')[0].lower()
        evidence.append('operating-system')
    elif prefix.endswith('/com.termux/files/usr') or (env.get('TERMUX_VERSION') and prefix.endswith('/usr')):
        selected, runtime = 'termux', 'android'
        evidence.append('termux-prefix')
    elif system in ('Linux', 'Android') and ('microsoft' in release.lower() or env.get('WSL_INTEROP') or env.get('WSL_DISTRO_NAME')):
        selected, runtime = 'wsl', 'linux'
        evidence.append('wsl-kernel' if 'microsoft' in release.lower() else 'wsl-environment')
    else:
        selected = 'linux'
        evidence.append('operating-system')
    data = os_release(release_file or (Path(prefix) / 'etc/os-release' if selected == 'termux' else '/etc/os-release')) if selected != 'windows' else {}
    identity = data.get('ID', 'unknown').lower()
    if not re.fullmatch(r'[a-z0-9][a-z0-9_.-]*', identity): identity = 'unknown'
    if selected in ('termux', 'windows'): identity = selected
    return dict(platform=selected, distro=identity,
                family=[v for v in data.get('ID_LIKE', '').lower().split() if re.fullmatch(r'[a-z0-9][a-z0-9_.-]*', v)],
                version=data.get('VERSION_ID', ''), name=data.get('NAME', identity),
                architecture=machine or host.machine(), runtime=runtime,
                wsl_distribution=env.get('WSL_DISTRO_NAME', '') if selected == 'wsl' else '', evidence=evidence)
