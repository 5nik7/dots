#!/usr/bin/env python3
import os
import sys
sys.dont_write_bytecode = True
if sys.version_info < (3, 9):
    sys.exit('pkgs: Python 3.9+ is required')

def main():
    from pkgs_lib.cli import main as run
    return run()

if __name__ == '__main__':
    sys.exit(main())
