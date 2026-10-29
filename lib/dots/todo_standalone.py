"""Standalone entry keeps automatic scope distinct from the Dots route."""
import sys
from todo_cli import main

if __name__ == '__main__':
    sys.exit(main(standalone=True))
