"""Internal one-shot worker; receives a locked descriptor from the CLI."""

import os
from pathlib import Path
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from termux_status.cache import refresh


if __name__ == "__main__":
    descriptor = int(sys.argv[2])
    try:
        refresh(sys.argv[1])
    finally:
        os.close(descriptor)
