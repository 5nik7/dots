#!/usr/bin/env python3
import os
import sys
sys.dont_write_bytecode = True
if sys.version_info < (3, 9):
    sys.exit('pkgs: Python 3.9+ is required')

def main():
    if os.name == 'nt':
        from pkgs_lib.grammar import parser
        grammar = parser()
        args = grammar.parse_intermixed_args()
        if args.command in (None, 'help'):
            grammar.print_help()
            return 0
        print('pkgs: package operations require Termux, Linux or WSL; native Windows backends are not implemented. Run pkgs in a separate WSL installation.', file=sys.stderr)
        return 3
    from pkgs_lib.cli import main as run
    return run()

if __name__ == '__main__':
    sys.exit(main())
