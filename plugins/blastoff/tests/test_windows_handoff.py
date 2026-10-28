"""Platform-branch unit tests, NOT evidence of a native Windows execution."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('blastoff_install_test', ROOT/'scripts/install.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)

class WindowsPayloadSelection(unittest.TestCase):
    def test_windows_does_not_discover_or_generate_posix_launcher(self):
        # Isolate this module's os reference; do not mutate global os.name or
        # pretend PosixPath can exercise Windows filesystem semantics.
        temporary = tempfile.TemporaryDirectory(prefix='blastoff-platform-branch-')
        self.addCleanup(temporary.cleanup)
        prefix = Path(temporary.name)/'not-created'
        with patch.object(installer, 'os', SimpleNamespace(name='nt')), \
             patch.object(installer.shutil, 'which', return_value=r'C:\Program Files\Git\bin\bash.exe') as which:
            pending, version_root = installer.payload(prefix)
        which.assert_not_called()
        self.assertNotIn(prefix/'bin/blastoff', pending)
        self.assertIn(version_root/'powershell/blastoff.psm1', pending)
        self.assertIn(prefix/'share/man/man1/blastoff.1', pending)
        self.assertFalse(prefix.exists())
