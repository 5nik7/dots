#!/usr/bin/env python3
"""Bounded native Windows wallpaper adapters; explicit setters only."""
import ctypes
import json
import os
from pathlib import Path
import subprocess
import sys


def windows_powershell():
    """Use the OS-owned 64-bit WinRT-capable engine, never PATH or a profile."""
    if os.name != 'nt':
        raise ValueError('native Windows is required')
    buffer = ctypes.create_unicode_buffer(32768)
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.GetWindowsDirectoryW.argtypes = [ctypes.c_wchar_p, ctypes.c_uint]
    size = kernel.GetWindowsDirectoryW(buffer, len(buffer))
    if not size or size >= len(buffer):
        raise ValueError('Windows directory is unavailable')
    system = 'System32' if ctypes.sizeof(ctypes.c_void_p) == 8 else 'Sysnative'
    engine = Path(buffer.value) / system / 'WindowsPowerShell/v1.0/powershell.exe'
    if not engine.is_file():
        raise ValueError('64-bit Windows PowerShell is unavailable')
    return engine


def lock_screen_request(path=None):
    command = [str(windows_powershell()), '-NoLogo', '-NoProfile', '-NonInteractive',
               '-File', str(Path(__file__).with_suffix('.ps1'))]
    if path is None:
        command.append('-Check')
    result = subprocess.run(command, input='' if path is None else json.dumps({'path': str(path)}),
                            capture_output=True, text=True, encoding='utf-8', timeout=15,
                            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if result.returncode:
        raise ValueError('Windows lock-screen adapter failed; no fallback was attempted')
    document = json.loads(result.stdout)
    return document


def lock_screen_supported():
    try:
        return lock_screen_request().get('supported') is True
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return False


def main(arguments=None):
    args = sys.argv[1:] if arguments is None else arguments
    if args == ['--check-lock-screen']:
        print(json.dumps({'supported': lock_screen_supported()}))
        return 0
    locked = len(args) == 2 and args[1] == '--lock-screen'
    if os.name != 'nt' or len(args) not in (1, 2) or (len(args) == 2 and not locked):
        return 2
    path = Path(args[0]).resolve()
    if not path.is_file():
        return 2
    if locked:
        return 0 if lock_screen_request(path).get('applied') is True else 1
    function = ctypes.WinDLL('user32', use_last_error=True).SystemParametersInfoW
    function.argtypes = [ctypes.c_uint, ctypes.c_uint, ctypes.c_wchar_p, ctypes.c_uint]
    function.restype = ctypes.c_int
    # SPI_SETDESKWALLPAPER; persist and broadcast the setting change.
    return 0 if function(0x0014, 0, str(path), 0x01 | 0x02) else 1


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError, subprocess.TimeoutExpired):
        print('Windows wallpaper adapter failed; external effects may require inspection.', file=sys.stderr)
        sys.exit(1)
