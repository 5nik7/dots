#!/usr/bin/env python3
"""Run absorbed application behavior tests, separate from retired release tooling."""
import argparse
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
# These modules test standalone source archives and prefix/module installation.
# Combined checkout lifecycle is covered by test_bundled_apps/test_installation.
BLASTOFF_RELEASE_TESTS = {
    'test_installed_package', 'test_installer_public', 'test_lifecycle_planning',
    'test_packaging', 'test_platform_detection', 'test_powershell_install',
    'test_windows_handoff',
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('application', choices=('blastoff', 'pkgs', 'all'), nargs='?', default='all')
    args = parser.parse_args()
    for app in ('blastoff', 'pkgs') if args.application == 'all' else (args.application,):
        if app == 'pkgs' and os.name == 'nt':
            print('pkgs backend tests require POSIX; native help/refusal is covered by test_bundled_apps.', flush=True)
            continue
        tests = ROOT/'plugins'/app/'tests'
        modules = sorted(p.stem for p in tests.glob('test_*.py')
                         if app != 'blastoff' or p.stem not in BLASTOFF_RELEASE_TESTS)
        # test_blastoff also contains the old prefix-install Lifecycle class.
        # Keep its application Contract class; Dots owns the new lifecycle.
        if app == 'blastoff':
            modules = ['test_blastoff.Contract' if name == 'test_blastoff' else name for name in modules]
        print('Running '+app+' application behavior tests', flush=True)
        result = subprocess.call([sys.executable, '-B', '-m', 'unittest', '-v', *modules], cwd=tests,
                                 env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
        if result: return result
    return 0


if __name__ == '__main__':
    sys.exit(main())
