#!/usr/bin/env python3
"""Bounded native Windows desktop wallpaper adapter (invoked explicitly)."""
import ctypes
import os
from pathlib import Path
import sys

if __name__ == '__main__':
    if os.name != 'nt' or len(sys.argv) != 2 or not Path(sys.argv[1]).is_file():
        sys.exit(2)
    function = ctypes.WinDLL('user32', use_last_error=True).SystemParametersInfoW
    function.argtypes = [ctypes.c_uint, ctypes.c_uint, ctypes.c_wchar_p, ctypes.c_uint]
    function.restype = ctypes.c_int
    # SPI_SETDESKWALLPAPER; persist and broadcast the setting change.
    if not function(0x0014, 0, str(Path(sys.argv[1]).resolve()), 0x01 | 0x02):
        sys.exit(1)
